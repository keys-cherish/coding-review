#!/usr/bin/env bash
# ==============================================================
#  CodeGuard Pro Linux/Mac Launcher (uv 版)
# ==============================================================
set -e

cd "$(dirname "$0")"

echo
echo "  ============================================================"
echo "                CodeGuard Pro - Code Quality Platform"
echo "  ============================================================"
echo

# ---------- 1. 确保 uv ----------
if ! command -v uv &>/dev/null; then
    echo "[!] uv not found, installing..."
    if command -v curl &>/dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
    elif command -v python3 &>/dev/null; then
        python3 -m pip install --user uv
    else
        echo "[X] Need curl or python3 to install uv"
        exit 1
    fi
fi

echo "[1/4] uv: $(uv --version)"

# ---------- 2. 虚拟环境 ----------
if [ ! -d ".venv" ]; then
    echo "[2/4] Creating .venv with uv..."
    uv venv --python 3.11 || uv venv
else
    echo "[2/4] Using existing .venv"
fi

# ---------- 3. 依赖 ----------
echo "[3/4] Installing dependencies..."
uv pip install -r requirements.txt

# ---------- 4. 数据库 ----------
echo "[4/4] Initializing database..."
.venv/bin/python -m scripts.init_db

# ---------- 5. 启动 ----------
URL="http://127.0.0.1:8000"
( sleep 1.5 && {
    if   command -v xdg-open &>/dev/null; then xdg-open "$URL"
    elif command -v open      &>/dev/null; then open "$URL"
    fi
} ) &

echo
echo "  ============================================================"
echo "   Service starting at $URL"
echo "   API Docs:           $URL/docs"
echo "   Press Ctrl+C to stop"
echo "  ============================================================"
echo

exec .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
