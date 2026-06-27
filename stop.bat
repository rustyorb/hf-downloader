@echo off
REM Stop the HF Downloader (Windows) - terminates python processes serving app.py on port 5000
setlocal
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000" ^| findstr "LISTENING"') do (
    echo Stopping PID %%a
    taskkill /F /PID %%a >nul 2>&1
)
echo HF Downloader stopped.
endlocal
