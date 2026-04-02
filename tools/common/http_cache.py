from __future__ import annotations

import json
import pathlib
import time
import urllib.request
from typing import Any


def fetch_json_cached(
    *,
    url: str,
    cache_dir: pathlib.Path,
    cache_name: str,
    cache_ttl_hours: int = 24,
    user_agent: str = "poe-stash-helper/1.0",
) -> Any:
    """Fetch JSON from disk cache when fresh, otherwise download it.

    This helper is intentionally tiny so both build scripts can share the same
    fetch/cache behaviour without duplicating urllib + cache-age code.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{cache_name}.json"

    if cache_path.exists():
        age_h = (time.time() - cache_path.stat().st_mtime) / 3600
        if age_h < cache_ttl_hours:
            print(f"  [{cache_name}] cache hit ({age_h:.0f}h old)")
            return json.loads(cache_path.read_text(encoding="utf-8"))

    print(f"  [{cache_name}] fetching {url} ...")
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    cache_path.write_text(json.dumps(data), encoding="utf-8")
    return data


def clear_cache_files(cache_dir: pathlib.Path, *patterns: str) -> list[pathlib.Path]:
    """Delete cache files matching one or more glob patterns."""
    deleted: list[pathlib.Path] = []
    if not cache_dir.exists():
        return deleted
    for pattern in patterns:
        for path in cache_dir.glob(pattern):
            if path.is_file():
                path.unlink()
                deleted.append(path)
    return deleted
