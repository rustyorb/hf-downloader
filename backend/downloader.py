"""Threaded download manager with per-file progress, speed/ETA, cancel & resume."""
import os
import time
import uuid
import threading
import queue
from pathlib import Path

import requests

from . import config


class DownloadTask:
    def __init__(self, repo_id, repo_type, revision, files, dest_root):
        self.id = uuid.uuid4().hex[:12]
        self.repo_id = repo_id
        self.repo_type = repo_type
        self.revision = revision or "main"
        self.files = files  # list of {path, size, url}
        self.dest_root = dest_root
        self.status = "queued"  # queued|downloading|completed|error|cancelled
        self.total_bytes = sum(f.get("size", 0) for f in files)
        self.done_bytes = 0
        self.speed = 0.0
        self.eta = 0
        self.current_file = ""
        self.error = ""
        self.created = time.time()
        self._cancel = threading.Event()

    def cancel(self):
        self._cancel.set()

    @property
    def cancelled(self):
        return self._cancel.is_set()

    @property
    def percent(self):
        if self.total_bytes <= 0:
            return 0.0
        return min(100.0, self.done_bytes / self.total_bytes * 100.0)

    def to_dict(self):
        return {
            "id": self.id,
            "repo_id": self.repo_id,
            "repo_type": self.repo_type,
            "revision": self.revision,
            "status": self.status,
            "total_bytes": self.total_bytes,
            "done_bytes": self.done_bytes,
            "percent": round(self.percent, 2),
            "speed": round(self.speed, 1),
            "eta": int(self.eta),
            "current_file": self.current_file,
            "file_count": len(self.files),
            "error": self.error,
            "created": self.created,
        }


class DownloadManager:
    def __init__(self):
        self.tasks: dict[str, DownloadTask] = {}
        self._q: "queue.Queue[str]" = queue.Queue()
        self._lock = threading.Lock()
        self._workers: list[threading.Thread] = []
        self._started = False

    def start(self):
        if self._started:
            return
        self._started = True
        max_workers = max(1, int(config.load_settings().get("max_workers", 3)))
        for _ in range(max_workers):
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()
            self._workers.append(t)

    def enqueue(self, repo_id, repo_type, revision, files, dest_root=None):
        self.start()
        settings = config.load_settings()
        dest_root = dest_root or settings.get("download_dir")
        task = DownloadTask(repo_id, repo_type, revision, files, dest_root)
        with self._lock:
            self.tasks[task.id] = task
        self._q.put(task.id)
        return task

    def cancel(self, task_id):
        with self._lock:
            task = self.tasks.get(task_id)
        if task and task.status in ("queued", "downloading"):
            task.cancel()
            if task.status == "queued":
                task.status = "cancelled"
            return True
        return False

    def remove(self, task_id):
        with self._lock:
            task = self.tasks.get(task_id)
            if task and task.status in ("completed", "error", "cancelled"):
                del self.tasks[task_id]
                return True
        return False

    def snapshot(self):
        with self._lock:
            return [t.to_dict() for t in sorted(self.tasks.values(), key=lambda x: x.created, reverse=True)]

    # --- worker internals ---
    def _worker(self):
        while True:
            task_id = self._q.get()
            with self._lock:
                task = self.tasks.get(task_id)
            if task is None or task.cancelled:
                if task:
                    task.status = "cancelled"
                self._q.task_done()
                continue
            try:
                self._run_task(task)
            except Exception as e:  # noqa: BLE001
                task.status = "error"
                task.error = str(e)
            finally:
                self._q.task_done()

    def _run_task(self, task: DownloadTask):
        task.status = "downloading"
        token = config.load_settings().get("token") or None
        subdir = "datasets" if task.repo_type == "dataset" else "models"
        base = Path(task.dest_root) / subdir / task.repo_id.replace("/", "__")
        base.mkdir(parents=True, exist_ok=True)

        window_start = time.time()
        window_bytes = 0

        for f in task.files:
            if task.cancelled:
                task.status = "cancelled"
                return
            task.current_file = f["path"]
            dest = base / f["path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_suffix(dest.suffix + ".part")

            resume_from = tmp.stat().st_size if tmp.exists() else 0
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            if resume_from > 0:
                headers["Range"] = f"bytes={resume_from}-"

            if dest.exists() and f.get("size") and dest.stat().st_size == f["size"]:
                task.done_bytes += f["size"]
                continue

            with requests.get(f["url"], headers=headers, stream=True, timeout=60) as r:
                if r.status_code == 416:  # already complete
                    if tmp.exists():
                        tmp.replace(dest)
                    task.done_bytes += f.get("size", 0)
                    continue
                r.raise_for_status()
                mode = "ab" if resume_from and r.status_code == 206 else "wb"
                if mode == "wb":
                    resume_from = 0
                else:
                    task.done_bytes += resume_from
                with open(tmp, mode) as out:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if task.cancelled:
                            task.status = "cancelled"
                            return
                        if not chunk:
                            continue
                        out.write(chunk)
                        n = len(chunk)
                        task.done_bytes += n
                        window_bytes += n
                        elapsed = time.time() - window_start
                        if elapsed >= 0.5:
                            task.speed = window_bytes / elapsed
                            remaining = max(0, task.total_bytes - task.done_bytes)
                            task.eta = remaining / task.speed if task.speed > 0 else 0
                            window_start = time.time()
                            window_bytes = 0
            tmp.replace(dest)

        task.speed = 0
        task.eta = 0
        task.current_file = ""
        task.status = "completed"
        config.add_history({
            "repo_id": task.repo_id,
            "repo_type": task.repo_type,
            "revision": task.revision,
            "files": len(task.files),
            "bytes": task.total_bytes,
            "dest": str(base),
            "time": time.time(),
        })


manager = DownloadManager()
