from __future__ import annotations
"""Disk cache for stash responses.

The stash endpoint supports ETag / If-None-Match. We keep the last successful
response on disk so a 304 Not Modified response can reuse already downloaded
content without reparsing or redownloading everything.
"""

import json
import time
from pathlib import Path
from typing import Optional

CACHE_DIR = Path(__file__).resolve().parents[2] / ".cache" / "stash"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL_SECONDS = 300


def _path(cache_key: str) -> Path:
    safe = cache_key.replace("/", "_")
    return CACHE_DIR / f"{safe}.json"


def load(cache_key: str) -> Optional[dict]:
    path = _path(cache_key)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
        if time.time() - payload.get("_ts", 0) > CACHE_TTL_SECONDS:
            return None
        payload.pop("_etag", None)
        payload.pop("_ts", None)
        return payload
    except Exception:
        return None


def get_etag(cache_key: str) -> Optional[str]:
    path = _path(cache_key)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle).get("_etag")
    except Exception:
        return None


def save(cache_key: str, payload: dict, etag: Optional[str]) -> None:
    record = dict(payload)
    record["_ts"] = time.time()
    record["_etag"] = etag
    try:
        with open(_path(cache_key), "w", encoding="utf-8") as handle:
            json.dump(record, handle)
    except Exception:
        pass


def invalidate(cache_key: str) -> None:
    try:
        _path(cache_key).unlink(missing_ok=True)
    except Exception:
        pass
