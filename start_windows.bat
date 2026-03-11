@echo off
echo Starting Qwen3-TTS Services...

:: Start Backend
start "Qwen3-TTS Backend" cmd /k "cd backend && venv\Scripts\python main.py"

:: Start Frontend
start "Qwen3-TTS Frontend" cmd /k "cd frontend && npm run dev"

echo Services are starting in separate windows.
echo Please visit http://localhost:5173 when the frontend is ready.
pause
