@echo off
REM ==============================================================
REM  CodeGuard Pro Windows Launcher (uv 版)
REM  - 使用 uv 管理虚拟环境与依赖（速度比 pip 快 10-100 倍）
REM  - 任意步骤失败都会 pause，方便阅读错误
REM ==============================================================
setlocal enabledelayedexpansion
chcp 65001 >nul
title CodeGuard Pro

cd /d "%~dp0"

echo.
echo  ============================================================
echo                CodeGuard Pro - Code Quality Platform
echo  ============================================================
echo.

REM ---------- 1. 检查 uv ----------
where uv >nul 2>nul
if errorlevel 1 (
    echo [!] uv not found, attempting auto-install via pip...
    where python >nul 2>nul
    if errorlevel 1 (
        echo [X] Python not found, please install Python 3.10+ first
        echo     https://www.python.org/downloads/
        echo.
        pause
        exit /b 1
    )
    python -m pip install --user uv
    if errorlevel 1 (
        echo [X] uv installation failed
        echo     Please install manually: https://docs.astral.sh/uv/getting-started/installation/
        echo.
        pause
        exit /b 1
    )
)

echo [1/4] uv detected:
uv --version
echo.

REM ---------- 2. 创建虚拟环境 ----------
if not exist ".venv\Scripts\python.exe" (
    echo [2/4] Creating .venv with uv...
    uv venv --python 3.11
    if errorlevel 1 (
        echo [!] Python 3.11 not available, falling back to default...
        uv venv
        if errorlevel 1 (
            echo [X] uv venv failed
            pause
            exit /b 1
        )
    )
) else (
    echo [2/4] Using existing .venv
)

REM ---------- 3. 安装依赖 ----------
echo [3/4] Installing dependencies (uv pip)...
uv pip install -r requirements.txt
if errorlevel 1 (
    echo [X] Dependency installation failed
    pause
    exit /b 1
)

REM ---------- 4. 初始化数据库 ----------
echo [4/4] Initializing database...
.venv\Scripts\python.exe -m scripts.init_db
if errorlevel 1 (
    echo [X] Database init failed
    pause
    exit /b 1
)

REM ---------- 5. 启动 ----------
echo.
echo  ============================================================
echo   Service starting at http://127.0.0.1:8000
echo   API Docs:           http://127.0.0.1:8000/docs
echo   Press Ctrl+C to stop
echo  ============================================================
echo.

start "" http://127.0.0.1:8000

.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
set "EXITCODE=%ERRORLEVEL%"

echo.
echo Service exited with code %EXITCODE%
pause
endlocal
exit /b %EXITCODE%
