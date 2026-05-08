#!/usr/bin/env bash
# ==============================================================
#  CodeGuard Pro Linux/Mac Launcher
# ==============================================================
set -e

echo
echo "  ============================================================"
echo "                CodeGuard Pro - Code Quality Platform"
echo "  ============================================================"
echo

if ! command -v python3 &> /dev/null; then
    echo "[X] python3 not found, please install Python 3.10+"
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "[1/4] Creating venv..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "[2/4] Installing dependencies..."
pip install -q --disable-pip-version-check -r requirements.txt

echo "[3/4] Initializing database..."
python -m scripts.init_db

echo "[4/4] Starting service..."
URL="http://127.0.0.1:8000"
( sleep 1.5 && {
    if command -v xdg-open &>/dev/null; then xdg-open "$URL"
    elif command -v open &>/dev/null; then open "$URL"
    fi
} ) &

echo
echo "  Access: $URL"
echo "  API Doc: $URL/docs"
echo "  Press Ctrl+C to stop"
echo
exec python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
