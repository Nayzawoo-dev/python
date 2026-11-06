#!/bin/bash
set -e

echo "============================================"
echo "  🎮 Python Game Launcher - Setup & Run"
echo "============================================"

if ! command -v python3.9 &>/dev/null; then
    echo "📦 Installing Python 3.9 via Homebrew..."
    brew install python@3.9
else
    echo "✅ Python 3.9: $(python3.9 --version)"
fi

echo "📦 Installing dependencies..."
python3.9 -m pip install --upgrade pip --quiet
python3.9 -m pip install -r requirements.txt

echo ""
echo "🚀 Starting launcher → http://localhost:5000"
python3.9 launcher.py
