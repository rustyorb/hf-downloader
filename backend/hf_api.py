"""HuggingFace Hub search and repository info helpers."""
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
