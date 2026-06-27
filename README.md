# 🤗 HF Downloader

A full-featured **web GUI** for searching and downloading HuggingFace **models** and **datasets**. Built with Flask + vanilla HTML/CSS/JS — no build step, no heavy frameworks.

![stack](https://img.shields.io/badge/python-3.10+-blue) ![flask](https://img.shields.io/badge/flask-3.x-black) ![license](https://img.shields.io/badge/license-MIT-green)

> Runs **entirely on your machine** — the server binds to `127.0.0.1:5000` and your HuggingFace token is stored locally in `data/settings.json` (git-ignored) and never sent to the browser.

## Features

- 🔎 **Search** models and datasets with sort (downloads / likes / recently updated)
- 📋 **Repo detail view** — file list with sizes, tags, downloads, likes, README preview
- ✅ **Selective download** — pick individual files or all, with a live filter (e.g. `.safetensors`, `.gguf`)
- 🌿 **Revision/branch selection**
- 🔑 **Token auth** for gated/private repos (stored locally, never sent to the browser)
- 🧵 **Download queue** with configurable concurrent workers
- 📈 **Live progress** per item — %, speed, ETA, bytes (via Server-Sent Events)
- ⏹ **Cancel** in-flight downloads
- ↩️ **Resume** interrupted downloads (HTTP Range requests + `.part` files)
- 💾 **Configurable destination** + disk space display
- 🕑 **Download history** log
- 🌓 **Dark / light theme**, persisted

## Quick start

### Windows
```bat
start.bat
```

### Linux / macOS
```bash
chmod +x start.sh stop.sh
./start.sh
```

The script creates a virtual environment, installs dependencies, and opens <http://127.0.0.1:5000>.

To stop:
```bat
stop.bat        REM Windows
./stop.sh       # Linux/macOS
```

## Manual setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Usage

1. **Browse** tab — search, or paste a repo id (`owner/name`) into the quick-open box.
2. Click a result to open the detail modal; pick a revision and select files.
3. Click **Download Selected** — items appear in the **Queue** tab with live progress.
4. Set your **token** and **download directory** in **Settings**.

> **Gated/private repos:** add a HuggingFace access token in Settings. Get one at
> <https://huggingface.co/settings/tokens>. The token is stored in `data/settings.json` on your machine only.

## Project structure

```
HF_Downloaderr/
├── app.py                 Flask routes + SSE stream
├── backend/
│   ├── config.py          settings + history persistence (JSON)
│   ├── hf_api.py          HF Hub search + repo info
│   └── downloader.py      threaded download manager (progress/cancel/resume)
├── templates/index.html
├── static/css/style.css
├── static/js/app.js
├── data/                  settings.json + history.json (created at runtime)
├── downloads/             default download destination
├── requirements.txt
└── start/stop scripts (.bat/.sh)
```

## Notes

- Files download to `<download_dir>/<models|datasets>/<owner__name>/...`.
- Changing the concurrent-worker count takes effect on restart.
- Downloads stream directly via the HuggingFace CDN with resume support.

## License

[MIT](LICENSE) © 2026 rustyorb
