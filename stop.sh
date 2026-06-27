#!/usr/bin/env bash
# Stop the HF Downloader (Linux/macOS)
PIDS=$(lsof -ti tcp:5000 2>/dev/null || true)
if [ -n "$PIDS" ]; then
    echo "Stopping PID(s): $PIDS"
    kill $PIDS 2>/dev/null || true
    echo "HF Downloader stopped."
else
    echo "No process found on port 5000."
fi
