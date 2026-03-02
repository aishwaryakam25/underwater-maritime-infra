@echo off
cd /d "c:\Users\Asus\Documents\nauticai-underwater-anomaly"

echo Starting Backend in new window (port 8000)...
start "NautiCAI Backend" cmd /k "cd /d c:\Users\Asus\Documents\nauticai-underwater-anomaly && venv\Scripts\activate.bat && uvicorn backend.main:app --host 0.0.0.0 --port 8000"

timeout /t 5 /nobreak >nul

echo Starting Frontend in new window (port 3000)...
start "NautiCAI Frontend" cmd /k "cd /d c:\Users\Asus\Documents\nauticai-underwater-anomaly\frontend && npm start"

echo.
echo Two windows opened: Backend (8000) and Frontend (3000).
echo Wait until frontend shows "Compiled successfully" then open: http://localhost:3000
echo.
pause
