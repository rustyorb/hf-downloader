"""Persistent settings and download history stored as JSON on disk."""
import json
import threading
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = APP_DIR / "data"
SETTINGS_FILE = DATA_DIR / "settings.json"
HISTORY_FILE = DATA_DIR / "history.json"

_lock = threading.Lock()

DEFAULT_SETTINGS = {
    "token": "",
    "download_dir": str(APP_DIR / "downloads"),
    "max_workers": 3,
    "theme": "dark",
}


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_settings() -> dict:
    _ensure_data_dir()
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULT_SETTINGS)
        merged.update(data or {})
        return merged
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> dict:
    _ensure_data_dir()
    current = dict(DEFAULT_SETTINGS)
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                current.update(json.load(f) or {})
        except (json.JSONDecodeError, OSError):
            pass
    current.update(settings or {})
    with _lock:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
    try:
        Path(current["download_dir"]).mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return current


def load_history() -> list:
    _ensure_data_dir()
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f) or []
    except (json.JSONDecodeError, OSError):
        return []


def add_history(entry: dict):
    _ensure_data_dir()
    with _lock:
        history = load_history()
        history.insert(0, entry)
        history = history[:200]
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)


def clear_history():
    _ensure_data_dir()
    with _lock:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
