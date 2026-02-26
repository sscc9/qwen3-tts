import time
import logging
from abc import ABC, abstractmethod
from typing import Tuple, Optional
import json
import base64

logger = logging.getLogger(__name__)


class TTSBackend(ABC):
    @abstractmethod
    async def generate_custom_voice(self, params: dict) -> Tuple[bytes, int]:
        pass

    @abstractmethod
    async def generate_voice_design(self, params: dict) -> Tuple[bytes, int]:
        pass

    @abstractmethod
    async def generate_voice_clone(self, params: dict, ref_audio_bytes: bytes) -> Tuple[bytes, int, str]:
        pass

    @abstractmethod
    async def health_check(self) -> dict:
        pass


class AliyunTTSBackend(TTSBackend):
    def __init__(self, api_key: str, region: str):
        self.api_key = api_key
        self.region = region
        self.tts_url = self._get_tts_url(region)
        self.customization_url = self._get_customization_url(region)

    def _get_tts_url(self, region: str) -> str:
        """非流式 TTS 合成接口"""
        if region == "beijing":
            return "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        else:
            return "https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"

    def _get_customization_url(self, region: str) -> str:
        """声音复刻 / 声音设计管理接口"""
        if region == "beijing":
            return "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization"
        else:
            return "https://dashscope-intl.aliyuncs.com/api/v1/services/audio/tts/customization"

    # 方言音色列表 - 这些只能用 Flash 模型
    DIALECT_SPEAKERS = {
        "Jada", "Dylan", "Li", "Marcus", "Roy",
        "Peter", "Sunny", "Eric", "Rocky", "Kiki",
    }

    async def generate_custom_voice(self, params: dict) -> Tuple[bytes, int]:
        from core.config import settings

        voice = self._map_speaker(params['speaker'])
        instruct = params.get('instruct', '')

        # Route to correct model based on voice type
        if "clone" in voice or "-vc-" in voice:
            model = settings.ALIYUN_MODEL_VC
        elif "design" in voice or "-vd-" in voice:
            model = settings.ALIYUN_MODEL_VD
        elif voice in self.DIALECT_SPEAKERS:
            # 方言音色不支持 Instruct-Flash，使用 Flash
            model = settings.ALIYUN_MODEL_FLASH
        else:
            # 普通话/外语音色使用 Instruct-Flash（支持指令控制）
            model = settings.ALIYUN_MODEL_INSTRUCT

        return await self._generate_via_http(
            model=model,
            text=params['text'],
            voice=voice,
            language=params['language'],
            instruct=instruct if model == settings.ALIYUN_MODEL_INSTRUCT else None,
        )

    async def generate_voice_design(self, params: dict, saved_voice_id: Optional[str] = None) -> Tuple[bytes, int]:
        from core.config import settings

        if saved_voice_id:
            voice_id = saved_voice_id
            logger.info(f"Using saved Aliyun voice_id: {voice_id}")
            if "clone" in voice_id or "-vc-" in voice_id:
                model = settings.ALIYUN_MODEL_VC
            else:
                model = settings.ALIYUN_MODEL_VD
        else:
            voice_id = await self._create_voice_design(
                instruct=params['instruct'],
                preview_text=params['text']
            )
            model = settings.ALIYUN_MODEL_VD

        return await self._generate_via_http(
            model=model,
            text=params['text'],
            voice=voice_id,
            language=params['language'],
        )

    async def generate_voice_clone(self, params: dict, ref_audio_bytes: bytes) -> Tuple[bytes, int, str]:
        from core.config import settings

        voice_id = await self._create_voice_clone(ref_audio_bytes)

        model = settings.ALIYUN_MODEL_VC

        audio_bytes, sample_rate = await self._generate_via_http(
            model=model,
            text=params['text'],
            voice=voice_id,
            language=params['language'],
        )
        return audio_bytes, sample_rate, voice_id

    async def _generate_via_http(
        self,
        model: str,
        text: str,
        voice: str,
        language: str,
        instruct: Optional[str] = None,
    ) -> Tuple[bytes, int]:
        """通过 HTTP 非流式接口生成语音"""
        import httpx

        payload = {
            "model": model,
            "input": {
                "text": text,
                "voice": voice,
                "language_type": language,
            }
        }

        # Instruct-Flash 模型支持指令控制
        if instruct and "instruct" in model:
            payload["input"]["instructions"] = instruct
            payload["input"]["optimize_instructions"] = True

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        logger.info(f"TTS HTTP request: model={model}, voice={voice}, lang={language}, instruct={'yes' if instruct else 'no'}")

        async with httpx.AsyncClient() as client:
            resp = await client.post(self.tts_url, json=payload, headers=headers, timeout=120)

            if resp.status_code != 200:
                logger.error(f"TTS HTTP failed with status {resp.status_code}")
                logger.error(f"Response body: {resp.text}")
                raise RuntimeError(f"Aliyun TTS API error: {resp.status_code} - {resp.text}")

            result = resp.json()

            # 获取音频 URL 并下载
            audio_url = result.get("output", {}).get("audio", {}).get("url")
            if not audio_url:
                raise RuntimeError(f"No audio URL in response: {result}")

            logger.info(f"TTS audio URL received, downloading...")

            audio_resp = await client.get(audio_url, timeout=60)
            audio_resp.raise_for_status()

            wav_bytes = audio_resp.content
            logger.info(f"TTS audio downloaded: {len(wav_bytes)} bytes")

            return wav_bytes, 24000

    async def _create_voice_clone(self, ref_audio_bytes: bytes) -> str:
        from core.config import settings
        import httpx

        audio_b64 = base64.b64encode(ref_audio_bytes).decode()
        data_uri = f"data:audio/wav;base64,{audio_b64}"

        payload = {
            "model": "qwen-voice-enrollment",
            "input": {
                "action": "create",
                "target_model": settings.ALIYUN_MODEL_VC,
                "preferred_name": f"clone{int(time.time())}",
                "audio": {"data": data_uri}
            }
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        logger.info(f"Voice clone request payload (audio truncated): {{'model': '{payload['model']}', 'input': {{'action': '{payload['input']['action']}', 'target_model': '{payload['input']['target_model']}', 'preferred_name': '{payload['input']['preferred_name']}', 'audio': '<truncated>'}}}}")

        async with httpx.AsyncClient() as client:
            resp = await client.post(self.customization_url, json=payload, headers=headers, timeout=60)

            if resp.status_code != 200:
                logger.error(f"Voice clone failed with status {resp.status_code}")
                logger.error(f"Response body: {resp.text}")

            resp.raise_for_status()
            result = resp.json()
            return result['output']['voice']

    async def _create_voice_design(self, instruct: str, preview_text: str) -> str:
        from core.config import settings
        import httpx

        payload = {
            "model": "qwen-voice-design",
            "input": {
                "action": "create",
                "target_model": settings.ALIYUN_MODEL_VD,
                "voice_prompt": instruct,
                "preview_text": preview_text,
                "preferred_name": f"design{int(time.time())}",
                "language": "zh"
            },
            "parameters": {
                "sample_rate": 24000,
                "response_format": "wav"
            }
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        logger.info(f"Voice design request payload: {payload}")

        async with httpx.AsyncClient() as client:
            resp = await client.post(self.customization_url, json=payload, headers=headers, timeout=60)

            if resp.status_code != 200:
                logger.error(f"Voice design failed with status {resp.status_code}")
                logger.error(f"Response body: {resp.text}")

            resp.raise_for_status()
            result = resp.json()
            return result['output']['voice']

    async def delete_voice(self, voice_id: str) -> bool:
        import httpx
        
        # Determine the correct model based on voice ID contents
        if "clone" in voice_id or "-vc-" in voice_id:
            model_name = "qwen-voice-enrollment"
        else:
            model_name = "qwen-voice-design"
            
        payload = {
            "model": model_name,
            "input": {
                "action": "delete",
                "voice_name": voice_id
            }
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        logger.info(f"Deleting voice from Aliyun: {voice_id}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.customization_url,
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    logger.warning(f"Failed to delete Aliyun voice {voice_id}: {response.text}")
                    return False
                    
                return True
            except Exception as e:
                logger.error(f"Error during Aliyun voice deletion for {voice_id}: {e}")
                return False

    async def health_check(self) -> dict:
        """轻量级 API Key 验证 - 不生成完整音频，仅检测 key 格式和连通性"""
        # 检查 key 格式
        if not self.api_key or not self.api_key.startswith("sk-"):
            return {"available": False, "error": "invalid_key_format"}

        import httpx
        try:
            # 使用极短文本触发最小开销请求，通过 HTTP 状态码确认 key 有效性
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "qwen3-tts-flash",
                "input": {
                    "text": "测",
                    "voice": "Cherry",
                    "language_type": "zh",
                }
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self.tts_url, json=payload, headers=headers, timeout=20
                )
                # 401 = key invalid, 200 = ok, 400 = param error but key ok
                if resp.status_code == 401:
                    return {"available": False, "error": "unauthorized"}
                return {"available": resp.status_code in (200, 400)}
        except Exception as e:
            logger.warning(f"Aliyun health check failed: {e}")
            return {"available": False}

    @staticmethod
    def _map_speaker(local_speaker: str) -> str:
        """Map legacy speaker names to official Qwen3 TTS voice IDs."""
        mapping = {
            "Ono_Anna": "Ono Anna",
            "Female": "Cherry",
            "Male": "Ethan"
        }

        mapped = mapping.get(local_speaker)
        if mapped:
            return mapped

        return local_speaker


class TTSServiceFactory:
    _aliyun_backend: Optional[AliyunTTSBackend] = None
    _user_aliyun_backends: dict[str, AliyunTTSBackend] = {}

    @classmethod
    async def get_backend(cls, backend_type: str = "aliyun", user_api_key: Optional[str] = None) -> TTSBackend:
        from core.config import settings
        
        # Force aliyun backend
        if not user_api_key:
            raise ValueError("Aliyun backend requires user API key. Please set your API key first.")

        if user_api_key not in cls._user_aliyun_backends:
            cls._user_aliyun_backends[user_api_key] = AliyunTTSBackend(
                api_key=user_api_key,
                region=settings.ALIYUN_REGION
            )
        return cls._user_aliyun_backends[user_api_key]
