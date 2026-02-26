#!/bin/bash

# 切换到脚本所在目录
cd "$(dirname "$0")"

echo "========================================"
echo "    🚀 正在启动 Qwen3 TTS 应用程序..."
echo "========================================"

# 捕获退出信号，以便在关闭窗口或按 Ctrl+C 时同步关闭后端进程
trap 'echo "正在关闭服务..."; kill $BACKEND_PID 2>/dev/null; exit' INT TERM EXIT

# 启动后端
echo "-> [1/2] 正在启动后端服务 (Backend)..."
cd backend
if [ -d "venv" ]; then
    source venv/bin/activate
fi
# 将后端放到后台运行
python main.py &
BACKEND_PID=$!

# 回到根目录
cd ..

# 启动前端
echo "-> [2/2] 正在启动前端服务 (Frontend)..."
cd frontend
echo "-> 前端启动后，请在浏览器中打开提供的本地链接 (通常是 http://localhost:5173)"
echo "----------------------------------------"
npm run dev
