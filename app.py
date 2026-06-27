"""HuggingFace Model & Dataset Downloader - Flask entry point."""
import json
import shutil
import time

from flask import Flask, render_template, request, jsonify, Response, stream_with_context

from backend import config, hf_api
from backend.downloader import manager

app = Flask(__name__)


@app.route("/")
def index():
    settings = config.load_settings()
    return render_template("index.html", theme=settings.get("theme", "dark"))


# ---------- Settings ----------
@app.route("/api/settings", methods=["GET"])
def get_settings():
    s = config.load_settings()
    s = dict(s)
    s["token_set"] = bool(s.get("token"))
    s["token"] = ""  # never expose token to client
    return jsonify(s)


@app.route("/api/settings", methods=["POST"])
def update_settings():
    data = request.get_json(force=True) or {}
    payload = {}
    if "download_dir" in data and data["download_dir"]:
        payload["download_dir"] = data["download_dir"]
    if "max_workers" in data:
        try:
            payload["max_workers"] = max(1, min(8, int(data["max_workers"])))
        except (ValueError, TypeError):
            pass
    if "theme" in data:
        payload["theme"] = data["theme"]
    if "token" in data:
        # only overwrite if non-empty, unless explicitly clearing
        if data["token"] or data.get("clear_token"):
            payload["token"] = data["token"]
    s = config.save_settings(payload)
    s = dict(s)
    s["token_set"] = bool(s.get("token"))
    s["token"] = ""
    return jsonify(s)


# ---------- Search ----------
@app.route("/api/search")
def api_search():
    query = request.args.get("q", "").strip()
    repo_type = request.args.get("type", "model")
    sort = request.args.get("sort", "downloads")
    try:
        limit = min(100, max(1, int(request.args.get("limit", 30))))
    except (ValueError, TypeError):
        limit = 30
    token = config.load_settings().get("token")
    try:
        results = hf_api.search(query, repo_type, sort, limit, token)
        return jsonify({"results": results})
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": str(e)}), 400


# ---------- Discover (trending + collections) ----------
@app.route("/api/discover")
def api_discover():
    repo_type = request.args.get("type", "dataset")
    sort = request.args.get("sort", "trending")
    try:
        limit = min(48, max(1, int(request.args.get("limit", 24))))
    except (ValueError, TypeError):
        limit = 24
    token = config.load_settings().get("token")
    try:
        if sort == "trending":
            results = hf_api.trending(repo_type, limit, token)
        else:
            results = hf_api.search("", repo_type, sort, limit, token)
        return jsonify({"results": results})
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": str(e)}), 400


@app.route("/api/collections")
def api_collections():
    sort = request.args.get("sort", "trending")
    try:
        limit = min(24, max(1, int(request.args.get("limit", 12))))
    except (ValueError, TypeError):
        limit = 12
    token = config.load_settings().get("token")
    try:
        return jsonify({"collections": hf_api.collections_list(sort, limit, token)})
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": str(e)}), 400


@app.route("/api/collection")
def api_collection():
    slug = request.args.get("slug", "").strip()
    if not slug:
        return jsonify({"error": "Missing collection slug"}), 400
    token = config.load_settings().get("token")
    try:
        return jsonify(hf_api.collection_items(slug, token))
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": str(e)}), 400


# ---------- Repo info ----------
@app.route("/api/repo")
def api_repo():
    repo_id = request.args.get("id", "").strip()
    repo_type = request.args.get("type", "model")
    revision = request.args.get("revision", "").strip()
    if not repo_id:
        return jsonify({"error": "Missing repo id"}), 400
    token = config.load_settings().get("token")
    try:
        info = hf_api.repo_info(repo_id, repo_type, revision, token)
        return jsonify(info)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": str(e)}), 500


# ---------- Downloads ----------
@app.route("/api/download", methods=["POST"])
def api_download():
    data = request.get_json(force=True) or {}
    repo_id = (data.get("repo_id") or "").strip()
    repo_type = data.get("repo_type", "model")
    revision = data.get("revision", "main")
    files = data.get("files") or []
    if not repo_id or not files:
        return jsonify({"error": "repo_id and files are required"}), 400
    task = manager.enqueue(repo_id, repo_type, revision, files)
    return jsonify({"task": task.to_dict()})


@app.route("/api/download/<task_id>/cancel", methods=["POST"])
def api_cancel(task_id):
    ok = manager.cancel(task_id)
    return jsonify({"ok": ok})


@app.route("/api/download/<task_id>", methods=["DELETE"])
def api_remove(task_id):
    ok = manager.remove(task_id)
    return jsonify({"ok": ok})


@app.route("/api/queue")
def api_queue():
    return jsonify({"tasks": manager.snapshot()})


@app.route("/api/stream")
def api_stream():
    @stream_with_context
    def gen():
        while True:
            payload = json.dumps({"tasks": manager.snapshot()})
            yield f"data: {payload}\n\n"
            time.sleep(1)
    return Response(gen(), mimetype="text/event-stream")


# ---------- History & disk ----------
@app.route("/api/history", methods=["GET"])
def api_history():
    return jsonify({"history": config.load_history()})


@app.route("/api/history", methods=["DELETE"])
def api_clear_history():
    config.clear_history()
    return jsonify({"ok": True})


@app.route("/api/disk")
def api_disk():
    s = config.load_settings()
    try:
        usage = shutil.disk_usage(s.get("download_dir"))
        return jsonify({"total": usage.total, "used": usage.used, "free": usage.free})
    except OSError as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    config.load_settings()  # ensure data dir + defaults
    app.run(host="127.0.0.1", port=5000, threaded=True, debug=False)
