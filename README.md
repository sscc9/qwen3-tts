# Qwen3-TTS-WebUI

一个基于阿里云 DashScope API 的 Qwen3 TTS 语音合成 Web 应用，支持内置發音人、声音设计和声音克隆功能。

本项目的 WebUI 和在线功能基于 [bdim404/Qwen3-TTS-WebUI](https://github.com/bdim404/Qwen3-TTS-WebUI)。

---

## 功能特性

- 🎙️ **49 个官方内置发音人**：包含普通话、9种方言（上海话/粤语/四川话等）和外语音色
- 🧠 **指令控制合成**：普通话音色支持通过自然语言描述控制语气、语速、情感（采用 `qwen3-tts-instruct-flash` 模型）
- 🎨 **声音设计**：通过文字描述创建专属音色
- 🔁 **声音克隆**：上传音频样本，快速复刻专属声线
- 📥 **音频下载**：生成的音频可直接下载保存
- 🖥️ **本地运行**：无需服务器，在本地启动即用

## 模型说明

| 场景 | 使用模型 |
|---|---|
| 普通话 / 外语内置音色 | `qwen3-tts-instruct-flash`（支持指令控制） |
| 方言内置音色 | `qwen3-tts-flash` |
| 声音克隆 | `qwen3-tts-vc-2026-01-22` |
| 声音设计 | `qwen3-tts-vd-2026-01-26` |

## 环境要求

- macOS / Linux
- Python 3.9+
- Node.js 18+
- [阿里云百炼 API Key](https://bailian.console.aliyun.com/)（需开通 Qwen3 TTS 服务）

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-username/qwen3-tts-webui.git
cd qwen3-tts-webui
```

### 2. 安装后端依赖

```bash
cd backend
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 安装前端依赖

```bash
cd ../frontend
npm install
```

### 4. 启动应用

**macOS 一键启动（双击即可）：**

```
双击 一键启动.command
```

**或手动启动：**

```bash
# 终端 1：启动后端
cd backend
source venv/bin/activate
python main.py

# 终端 2：启动前端
cd frontend
npm run dev
```

**访问地址：** http://localhost:5173

### 5. 配置 API Key

进入**设置页面**，填入你的阿里云百炼 API Key（以 `sk-` 开头）并保存。

## 项目结构

```
.
├── backend/          # Python FastAPI 后端
│   ├── api/          # API 路由
│   ├── core/         # 核心服务（TTS、配置）
│   ├── db/           # 数据库模型与操作
│   └── main.py       # 入口
├── frontend/         # React 前端
│   └── src/
│       ├── components/
│       ├── pages/
│       └── contexts/
└── 一键启动.command  # macOS 快捷启动脚本
```

## 致谢

- [bdim404/Qwen3-TTS-WebUI](https://github.com/bdim404/Qwen3-TTS-WebUI) — 提供原始 WebUI 和在线功能实现
- [阿里云百炼 DashScope](https://dashscope.aliyuncs.com) — Qwen3 TTS API 服务

## License

本项目遵循原项目 [bdim404/Qwen3-TTS-WebUI](https://github.com/bdim404/Qwen3-TTS-WebUI) 的开源协议。
