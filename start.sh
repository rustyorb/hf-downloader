#!/usr/bin/env bash
# Start the HF Downloader (Linux/macOS)
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate
echo "Installing/checking dependencies..."
pip install -q -r requirements.txt

echo "Starting HF Downloader at http://127.0.0.1:5000"
python app.py
