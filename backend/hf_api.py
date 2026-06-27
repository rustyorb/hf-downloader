"""HuggingFace Hub search and repository info helpers."""
import json

import requests

from huggingface_hub import HfApi, hf_hub_url
from huggingface_hub.utils import (
    GatedRepoError,
    RepositoryNotFoundError,
    HfHubHTTPError,
)


def _api(token: str | None) -> HfApi:
    return HfApi(token=token or None)


def search(query: str, repo_type: str, sort: str, limit: int, token: str | None) -> list:
    """Search models or datasets. repo_type in {'model','dataset'}."""
    api = _api(token)
    sort = sort or "downloads"
    results = []
    if repo_type == "dataset":
        items = api.list_datasets(search=query or None, sort=sort, direction=-1, limit=limit)
        for it in items:
            results.append({
                "id": it.id,
                "type": "dataset",
                "downloads": getattr(it, "downloads", 0) or 0,
                "likes": getattr(it, "likes", 0) or 0,
                "tags": (getattr(it, "tags", None) or [])[:8],
                "updated": str(getattr(it, "last_modified", "") or ""),
            })
    else:
        items = api.list_models(search=query or None, sort=sort, direction=-1, limit=limit)
        for it in items:
            results.append({
                "id": it.id,
                "type": "model",
                "downloads": getattr(it, "downloads", 0) or 0,
                "likes": getattr(it, "likes", 0) or 0,
                "tags": (getattr(it, "tags", None) or [])[:8],
                "pipeline_tag": getattr(it, "pipeline_tag", "") or "",
                "updated": str(getattr(it, "last_modified", "") or ""),
            })
    return results


def repo_info(repo_id: str, repo_type: str, revision: str, token: str | None) -> dict:
    """Return metadata + file list with sizes for a repo."""
    api = _api(token)
    try:
        info = api.repo_info(
            repo_id=repo_id,
            repo_type=repo_type,
            revision=revision or None,
            files_metadata=True,
        )
    except GatedRepoError:
        raise ValueError("This repo is gated. Provide an access token with accepted license.")
    except RepositoryNotFoundError:
        raise ValueError("Repository not found (or private without a valid token).")
    except HfHubHTTPError as e:
        raise ValueError(f"HuggingFace API error: {e}")

    files = []
    for s in (info.siblings or []):
        size = getattr(s, "size", None)
        if size is None:
            lfs = getattr(s, "lfs", None)
            if lfs and isinstance(lfs, dict):
                size = lfs.get("size")
        files.append({
            "path": s.rfilename,
            "size": size or 0,
            "url": hf_hub_url(repo_id, s.rfilename, repo_type=repo_type, revision=revision or None),
        })
    files.sort(key=lambda f: f["path"])

    try:
        refs = api.list_repo_refs(repo_id=repo_id, repo_type=repo_type)
        branches = [b.name for b in refs.branches]
    except Exception:
        branches = ["main"]

    card = ""
    try:
        from huggingface_hub import hf_hub_download
        readme_path = hf_hub_download(
            repo_id=repo_id, filename="README.md", repo_type=repo_type,
            revision=revision or None, token=token or None,
        )
        with open(readme_path, "r", encoding="utf-8", errors="ignore") as f:
            card = f.read()[:20000]
    except Exception:
        card = ""

    return {
        "id": repo_id,
        "type": repo_type,
        "sha": getattr(info, "sha", ""),
        "downloads": getattr(info, "downloads", 0) or 0,
        "likes": getattr(info, "likes", 0) or 0,
        "tags": getattr(info, "tags", []) or [],
        "pipeline_tag": getattr(info, "pipeline_tag", "") or "",
        "branches": branches or ["main"],
        "files": files,
        "total_size": sum(f["size"] for f in files),
        "readme": card,
    }


TRENDING_URL = "https://huggingface.co/api/trending"


def trending(repo_type: str, limit: int, token: str | None) -> list:
    """Top trending models or datasets via the Hub trending feed."""
    headers = {"authorization": f"Bearer {token}"} if token else {}
    r = requests.get(
        TRENDING_URL,
        # The trending endpoint rejects limit > 20 with a 400.
        params={"type": repo_type, "limit": min(limit, 20)},
        headers=headers,
        timeout=20,
    )
    r.raise_for_status()
    data = r.json() or {}
    results = []
    for entry in data.get("recentlyTrending", []):
        if entry.get("repoType") != repo_type:
            continue
        repo = entry.get("repoData") or {}
        results.append({
            "id": repo.get("id", ""),
            "type": repo_type,
            "downloads": repo.get("downloads", 0) or 0,
            "likes": repo.get("likes", 0) or 0,
            "tags": (repo.get("tags") or [])[:8],
            "pipeline_tag": repo.get("pipeline_tag", "") or "",
            "updated": str(repo.get("lastModified", "") or ""),
        })
    return results[:limit]


def collections_list(sort: str, limit: int, token: str | None) -> list:
    """List collections (trending or most-upvoted)."""
    api = _api(token)
    sort = sort if sort in ("trending", "upvotes", "lastModified") else "trending"
    out = []
    for c in api.list_collections(sort=sort, limit=limit):
        owner = c.owner
        if isinstance(owner, dict):
            owner_name = owner.get("name") or owner.get("fullname") or ""
        else:
            owner_name = getattr(owner, "name", "") or str(owner or "")
        out.append({
            "slug": c.slug,
            "title": c.title,
            "owner": owner_name,
            "upvotes": getattr(c, "upvotes", 0) or 0,
            "url": f"https://huggingface.co/collections/{c.slug}",
        })
    return out


def collection_items(slug: str, token: str | None) -> dict:
    """Return the downloadable (model/dataset) items of a collection."""
    api = _api(token)
    full = api.get_collection(slug)
    all_items = full.items or []
    items = [
        {"id": it.item_id, "type": it.item_type}
        for it in all_items
        if it.item_type in ("model", "dataset")
    ]
    return {"title": full.title, "items": items, "total": len(all_items)}


def _map_raw_collection(c: dict) -> dict:
    owner = c.get("owner") or {}
    if isinstance(owner, dict):
        owner_name = owner.get("name") or owner.get("fullname") or ""
    else:
        owner_name = str(owner)
    slug = c.get("slug", "")
    return {
        "slug": slug,
        "title": c.get("title", ""),
        "owner": owner_name,
        "upvotes": c.get("upvotes", 0) or 0,
        "url": f"https://huggingface.co/collections/{slug}",
    }


def search_collections(query: str, limit: int, token: str | None) -> list:
    """Full-text search collections via the raw Hub endpoint (the library lacks `q`)."""
    headers = {"authorization": f"Bearer {token}"} if token else {}
    r = requests.get(
        "https://huggingface.co/api/collections",
        params={"q": query, "limit": limit},
        headers=headers,
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    return [_map_raw_collection(c) for c in (data or []) if isinstance(c, dict)]


# ---------- Dataset preview (HF Datasets Viewer) ----------
DATASETS_VIEWER = "https://datasets-server.huggingface.co"


def _trunc(val, n: int = 200) -> str:
    s = val if isinstance(val, str) else json.dumps(val, ensure_ascii=False, default=str)
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


def dataset_preview(dataset_id: str, config: str, split: str, token: str | None) -> dict:
    """Preview a dataset via the HF Datasets Viewer: columns + first ~10 rows."""
    headers = {"authorization": f"Bearer {token}"} if token else {}

    def _get(path, **params):
        return requests.get(f"{DATASETS_VIEWER}/{path}", params=params, headers=headers, timeout=25)

    def _err(resp):
        try:
            return resp.json().get("error", "") or f"Viewer error ({resp.status_code})."
        except Exception:
            return f"Viewer error ({resp.status_code})."

    rs = _get("splits", dataset=dataset_id)
    if not rs.ok:
        return {"available": False, "error": _err(rs)}
    splits = rs.json().get("splits", [])
    if not splits:
        return {"available": False, "error": "No viewable splits."}

    configs = []
    for s in splits:
        if s["config"] not in configs:
            configs.append(s["config"])
    config = config if config in configs else configs[0]
    cfg_splits = [s["split"] for s in splits if s["config"] == config]
    split = split if split in cfg_splits else cfg_splits[0]

    num_rows = num_bytes = None
    rz = _get("size", dataset=dataset_id, config=config)
    if rz.ok:
        cfg_size = (rz.json().get("size", {}) or {}).get("config", {}) or {}
        num_rows = cfg_size.get("num_rows")
        num_bytes = cfg_size.get("num_bytes_original_files")

    rf = _get("first-rows", dataset=dataset_id, config=config, split=split)
    if not rf.ok:
        return {"available": False, "error": _err(rf)}
    fr = rf.json()
    columns = [f["name"] for f in fr.get("features", [])]
    rows = [
        {c: _trunc(item.get("row", {}).get(c)) for c in columns}
        for item in fr.get("rows", [])[:10]
    ]

    return {
        "available": True,
        "configs": configs,
        "splits": cfg_splits,
        "config": config,
        "split": split,
        "num_rows": num_rows,
        "num_bytes": num_bytes,
        "columns": columns,
        "rows": rows,
    }
