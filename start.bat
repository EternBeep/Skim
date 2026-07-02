@echo off
echo Starting Skim...

start "Skim Backend" cmd /k "cd /d D:\Project2\Skim && venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000"

timeout /t 3 /nobreak >nul

start "Skim Frontend" cmd /k "cd /d D:\Project2\Skim\frontend && npm run dev"

timeout /t 4 /nobreak >nul

start http://localhost:5173
