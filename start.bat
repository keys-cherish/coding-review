@echo off
REM ==============================================================
REM  CodeGuard Pro Windows Launcher
REM ==============================================================
setlocal enabledelayedexpansion
chcp 65001 >nul

echo.
echo  ============================================================
echo                CodeGuard Pro - Code Quality Platform
echo  ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [X] Python not found, please install Python 3.10+
    pause
    exit /b 1
)

if not exist "venv\Scripts\python.exe" (
    echo [1/4] Creating venv...
    python -m venv venv
    if errorlevel 1 (
        echo [X] venv creation failed
        pause
        exit /b 1
    )
)

call venv\Scripts\activate.bat

echo [2/4] Installing dependencies...
pip install -q --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo [X] Dependency installation failed
    pause
    exit /b 1
)

echo [3/4] Initializing database...
python -m scripts.init_db

echo [4/4] Starting service...
start "" http://127.0.0.1:8000
echo.
echo  Access: http://127.0.0.1:8000
echo  API Doc: http://127.0.0.1:8000/docs
echo  Press Ctrl+C to stop
echo.
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

endlocal
