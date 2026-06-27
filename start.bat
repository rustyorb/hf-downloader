@echo off
REM Start the HF Downloader (Windows)
setlocal
cd /d "%~dp0"

if not exist ".venv\" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat
echo Installing/checking dependencies...
pip install -q -r requirements.txt

echo Starting HF Downloader at http://127.0.0.1:5000
start "" http://127.0.0.1:5000
python app.py

endlocal
