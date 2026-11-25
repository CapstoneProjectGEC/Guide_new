@echo off
title Karnataka Tourism AI Guide Launcher
echo ======================================================================
echo  Starting Karnataka Tourism Smart AI Guide Platform
echo ======================================================================

:: 1. Check MySQL Service
echo [1/3] Checking MySQL database service...
sc query MySQL80 | find "RUNNING" >nul
if %ERRORLEVEL% neq 0 (
    echo [WARNING] MySQL80 service is not running. Starting MySQL80...
    net start MySQL80
) else (
    echo [OK] MySQL80 is running.
)

:: 2. Check Ollama
echo [2/3] Checking Ollama LLM service...
tasklist /fi "imagename eq ollama.exe" | find "ollama.exe" >nul
if %ERRORLEVEL% neq 0 (
    echo [INFO] Starting Ollama in the background...
    start "" ollama serve
) else (
    echo [OK] Ollama is running.
)

:: 3. Launch Backend & Frontend
echo [3/3] Launching Backend and Frontend servers...

start "Karnataka Tourism - Backend Server" cmd /k "cd /d %~dp0 && title Backend Server && backend\.venv\Scripts\python.exe -m uvicorn backend.src.main:app --host 127.0.0.1 --port 8000"

start "Karnataka Tourism - Frontend UI" cmd /k "cd /d %~dp0frontend && title Frontend UI && npm run dev"

echo.
echo ======================================================================
echo Both servers have been launched!
echo.
echo   * Frontend Web UI:  http://127.0.0.1:3000
echo   * Backend REST API: http://127.0.0.1:8000
echo   * API Docs:         http://127.0.0.1:8000/docs
echo.
echo   * Admin Username:   admin
echo   * Admin Password:   AdminPassword123!
echo ======================================================================
echo.
echo Opening browser in 4 seconds...
timeout /t 4 /nobreak >nul
start http://127.0.0.1:3000
