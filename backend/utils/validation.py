from typing import List, Dict

SUPPORTED_LANGUAGES = [
    "Chinese", "English", "Japanese", "Korean", "German",
    "French", "Russian", "Portuguese", "Spanish", "Italian",
    "Auto", "Cantonese"
]

SUPPORTED_SPEAKERS = [
    "Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric",
    "Ryan", "Aiden", "Ono_Anna", "Sohee"
]

SPEAKER_DESCRIPTIONS = {
    "Vivian": "Female, professional and clear",
    "Serena": "Female, gentle and warm",
    "Uncle_Fu": "Male, mature and authoritative",
    "Dylan": "Male, young and energetic",
    "Eric": "Male, calm and steady",
    "Ryan": "Male, friendly and casual",
    "Aiden": "Male, deep and resonant",
    "Ono_Anna": "Female, cute and lively",
    "Sohee": "Female, soft and melodious"
}

# ===== 官方 Qwen3 TTS 音色列表 =====
# 普通话音色
ALIYUN_SPEAKERS_MANDARIN = [
    "Cherry", "Serena", "Ethan", "Chelsie", "Momo",
    "Vivian", "Moon", "Maia", "Kai", "Nofish",
    "Bella", "Jennifer", "Ryan", "Katerina", "Aiden",
    "Eldric Sage", "Mia", "Mochi", "Bellona", "Vincent",
    "Bunny", "Neil", "Elias", "Arthur", "Nini",
    "Ebona", "Seren", "Pip", "Stella", "Andre",
]

# 方言音色
ALIYUN_SPEAKERS_DIALECT = [
    "Jada", "Dylan", "Li", "Marcus", "Roy",
    "Peter", "Sunny", "Eric", "Rocky", "Kiki",
]

# 外语音色
ALIYUN_SPEAKERS_FOREIGN = [
    "Bodega", "Sonrisa", "Alek", "Dolce", "Sohee",
    "Ono Anna", "Lenn", "Emilien", "Radio Gol",
]

ALIYUN_SPEAKERS = ALIYUN_SPEAKERS_MANDARIN + ALIYUN_SPEAKERS_DIALECT + ALIYUN_SPEAKERS_FOREIGN

ALIYUN_SPEAKER_DESCRIPTIONS = {
    # 普通话音色
    "Cherry":      "芊悦 - 阳光积极、亲切自然小姐姐（女）",
    "Serena":      "苏瑶 - 温柔小姐姐（女）",
    "Ethan":       "晨煦 - 阳光、温暖、活力、朝气（男）",
    "Chelsie":     "千雪 - 二次元虚拟女友（女）",
    "Momo":        "茉兔 - 撒娇搞怪，逗你开心（女）",
    "Vivian":      "十三 - 拽拽的、可爱的小暴躁（女）",
    "Moon":        "月白 - 率性帅气的月白（男）",
    "Maia":        "四月 - 知性与温柔的碰撞（女）",
    "Kai":         "凯 - 耳朵的一场SPA（男）",
    "Nofish":      "不吃鱼 - 南方口音男（男）",
    "Bella":       "萌宝 - 喝酒不打醉拳的小萝莉（女）",
    "Jennifer":    "詹妮弗 - 美剧大女主（女）",
    "Ryan":        "甜茶 - 节奏拉满，戏感炸裂（男）",
    "Katerina":    "卡捷琳娜 - 御姐深情女（女）",
    "Aiden":       "艾登 - 精通厨艺的美语大男孩（男）",
    "Eldric Sage": "沧明子 - 沉稳睿智的老者（男）",
    "Mia":         "乖小妹 - 温顺如春水，乖巧如初雪（女）",
    "Mochi":       "沙小弥 - 聪明伶俐的小大人（男）",
    "Bellona":     "燕铮莺 - 金戈铁马，千面人声（女）",
    "Vincent":     "田叔 - 沙哑烟嗓，江湖豪情（男）",
    "Bunny":       "萌小姬 - 萌属性爆棚的小萝莉（女）",
    "Neil":        "阿闻 - 专业新闻主持人（男）",
    "Elias":       "墨讲师 - 学术讲师女（女）",
    "Arthur":      "徐大爷 - 质朴嗓音，满村奇闻（男）",
    "Nini":        "邻家妹妹 - 又软又黏的嗓音（女）",
    "Ebona":       "诡婆婆 - 神秘低语（女）",
    "Seren":       "小婉 - 温和舒缓助眠（女）",
    "Pip":         "顽屁小孩 - 调皮捣蛋却充满童真（男）",
    "Stella":      "少女阿月 - 甜到发腻的迷糊少女（女）",
    "Andre":       "安德雷 - 声音磁性，沉稳男生（男）",
    # 方言音色
    "Jada":        "上海-阿珍 - 沪上阿姐（女·上海话）",
    "Dylan":       "北京-晓东 - 北京胡同少年（男·北京话）",
    "Li":          "南京-老李 - 南京大叔（男·南京话）",
    "Marcus":      "陕西-秦川 - 陕北汉子（男·陕西话）",
    "Roy":         "闽南-阿杰 - 闽南哥仔（男·闽南语）",
    "Peter":       "天津-李彼得 - 天津捧哏（男·天津话）",
    "Sunny":       "四川-晴儿 - 甜蜜川妹（女·四川话）",
    "Eric":        "四川-程川 - 成都大哥（男·四川话）",
    "Rocky":       "粤语-阿强 - 幽默港仔（男·粤语）",
    "Kiki":        "粤语-阿清 - 甜美港妹（女·粤语）",
    # 外语音色
    "Bodega":      "博德加 - 热情的西班牙大叔（男）",
    "Sonrisa":     "索尼莎 - 热情开朗的拉美大姐（女）",
    "Alek":        "阿列克 - 战斗民族的冷与暖（男）",
    "Dolce":       "多尔切 - 慵懒的意大利大叔（男）",
    "Sohee":       "素熙 - 温柔开朗的韩国欧尼（女）",
    "Ono Anna":    "小野杏 - 鬼灵精怪的青梅竹马（女）",
    "Lenn":        "莱恩 - 穿西装也听后朋克的德国青年（男）",
    "Emilien":     "埃米尔安 - 浪漫的法国大哥哥（男）",
    "Radio Gol":   "拉迪奥·戈尔 - 足球诗人（男）",
}

LOCAL_SPEAKERS = SUPPORTED_SPEAKERS.copy()

LOCAL_SPEAKER_DESCRIPTIONS = SPEAKER_DESCRIPTIONS.copy()


def validate_language(language: str) -> str:
    normalized = language.strip()

    for supported in SUPPORTED_LANGUAGES:
        if normalized.lower() == supported.lower():
            return supported

    raise ValueError(
        f"Unsupported language: {language}. "
        f"Supported languages: {', '.join(SUPPORTED_LANGUAGES)}"
    )


def validate_speaker(speaker: str, backend: str = "local") -> str:
    normalized = speaker.strip()

    if backend == "aliyun":
        speaker_list = ALIYUN_SPEAKERS
    else:
        speaker_list = LOCAL_SPEAKERS

    for supported in speaker_list:
        if normalized.lower() == supported.lower():
            return supported

    raise ValueError(
        f"Unsupported speaker: {speaker} for backend '{backend}'. "
        f"Supported speakers: {', '.join(speaker_list)}"
    )


def validate_text_length(text: str, max_length: int = 1000) -> str:
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    if len(text) > max_length:
        raise ValueError(
            f"Text length ({len(text)}) exceeds maximum ({max_length})"
        )

    return text.strip()


def validate_generation_params(params: dict) -> dict:
    validated = {}

    validated['max_new_tokens'] = params.get('max_new_tokens', 2048)
    if not 128 <= validated['max_new_tokens'] <= 4096:
        raise ValueError("max_new_tokens must be between 128 and 4096")

    validated['temperature'] = params.get('temperature', 0.9)
    if not 0.1 <= validated['temperature'] <= 2.0:
        raise ValueError("temperature must be between 0.1 and 2.0")

    validated['top_k'] = params.get('top_k', 50)
    if not 1 <= validated['top_k'] <= 100:
        raise ValueError("top_k must be between 1 and 100")

    validated['top_p'] = params.get('top_p', 1.0)
    if not 0.0 <= validated['top_p'] <= 1.0:
        raise ValueError("top_p must be between 0.0 and 1.0")

    validated['repetition_penalty'] = params.get('repetition_penalty', 1.05)
    if not 1.0 <= validated['repetition_penalty'] <= 2.0:
        raise ValueError("repetition_penalty must be between 1.0 and 2.0")

    return validated


def get_supported_languages() -> List[str]:
    return SUPPORTED_LANGUAGES.copy()


def get_supported_speakers(backend: str = "local") -> List[dict]:
    if backend == "aliyun":
        speakers = ALIYUN_SPEAKERS
        descriptions = ALIYUN_SPEAKER_DESCRIPTIONS
    else:
        speakers = LOCAL_SPEAKERS
        descriptions = LOCAL_SPEAKER_DESCRIPTIONS

    return [
        {
            "name": speaker,
            "description": descriptions.get(speaker, "")
        }
        for speaker in speakers
    ]
