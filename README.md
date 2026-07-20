# 🤗 HF Downloader

A full-featured **web GUI** for discovering, previewing, and downloading HuggingFace **models**, **datasets**, and **collections**. Built with Flask + vanilla HTML/CSS/JS — no build step, no heavy frameworks.

![stack](https://img.shields.io/badge/python-3.10+-blue) ![flask](https://img.shields.io/badge/flask-3.x-black) ![license](https://img.shields.io/badge/license-MIT-green)

> Runs **entirely on your machine** — the server binds to `127.0.0.1:5000` and your HuggingFace token is stored locally in `data/settings.json` (git-ignored) and never sent to the browser.

## Features

- 🔥 **Discover** tab — trending models/datasets and trending/most-upvoted collections
- 🔎 **Browse/Search** models, datasets, and collections with sort (downloads / likes / recently updated) and full-text collection search
- 📋 **Repo detail view** — file list with sizes, tags, downloads, likes, README preview
- 🧮 **Dataset preview** — columns and first rows via the HF Datasets Viewer, with config/split switching
- 📚 **Collection browsing** — view all model/dataset items in a collection
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

## Tech stack

| Layer    | Tech                                                   |
| -------- | ------------------------------------------------------- |
| Backend  | Python 3.10+, Flask 3.x, `huggingface_hub`, `requests` |
| Frontend | Vanilla HTML/CSS/JS (no framework, no build step)      |
| Data     | Flat JSON files (`data/settings.json`, `data/history.json`) |
| Storage  | Local filesystem (`downloads/` by default)             |

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

1. **Discover** tab — see what's trending in models/datasets, plus trending/most-upvoted collections.
2. **Browse** tab — search models, datasets, or collections, or paste a repo id (`owner/name`) into the quick-open box.
3. Click a result to open the detail modal; pick a revision, preview a dataset's columns/rows, and select files.
4. Click **Download Selected** — items appear in the **Queue** tab with live progress.
5. Set your **token** and **download directory** in **Settings**.

> **Gated/private repos:** add a HuggingFace access token in Settings. Get one at
> <https://huggingface.co/settings/tokens>. The token is stored in `data/settings.json` on your machine only.

## Configuration

Settings are persisted in `data/settings.json` (created on first run) and editable from the **Settings** tab or via the API.

| Key            | Default          | Description                                    |
| -------------- | ---------------- | ----------------------------------------------- |
| `token`        | `""`              | HuggingFace access token for gated/private repos |
| `download_dir` | `<repo>/downloads` | Root directory for downloaded files            |
| `max_workers`  | `3`               | Concurrent download workers (1–8, takes effect on restart) |
| `theme`        | `"dark"`          | UI theme (`dark` / `light`)                     |

## API

| Route                              | Method | Purpose                                      |
| ----------------------------------- | ------ | --------------------------------------------- |
| `/api/settings`                    | GET/POST | Read/update settings                        |
| `/api/search`                      | GET    | Search models/datasets                       |
| `/api/discover`                    | GET    | Trending models/datasets                     |
| `/api/collections`                 | GET    | List or search collections                   |
| `/api/collection`                  | GET    | Items within a collection                    |
| `/api/dataset-preview`             | GET    | Dataset columns/rows via the Datasets Viewer |
| `/api/repo`                        | GET    | Repo metadata + file list                    |
| `/api/download`                    | POST   | Enqueue a download                           |
| `/api/download/<task_id>/cancel`   | POST   | Cancel a queued/running download             |
| `/api/download/<task_id>`          | DELETE | Remove a finished/cancelled task              |
| `/api/queue`                       | GET    | Snapshot of all download tasks               |
| `/api/stream`                      | GET    | Live queue updates (Server-Sent Events)      |
| `/api/history`                     | GET/DELETE | View/clear download history              |
| `/api/disk`                        | GET    | Disk usage for the download directory        |

## Project structure

```
hf-downloader/
├── app.py                 Flask routes + SSE stream
├── backend/
│   ├── config.py          settings + history persistence (JSON)
│   ├── hf_api.py          HF Hub search, discover, collections, dataset preview, repo info
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
