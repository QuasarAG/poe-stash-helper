from __future__ import annotations
"""Thin client for the official trade stats endpoint."""

import json
import threading
import time
from pathlib import Path

import requests

from config import API
from models import TradeStatSummary
from api.policies.error_policy import parse_error_message
from api.policies.request_policy import build_json_headers
from api.policies.rate_limiter import RateLimiter

GGG_STATS_URL = "https://www.pathofexile.com/api/trade/data/stats"
CACHE_PATH = Path(__file__).resolve().parents[2] / "cache" / "stats_cache.json"
CACHE_TTL_HOURS = 24


class StatsClient:
    def __init__(self, rate_limiter: RateLimiter):
        self._rate_limiter = rate_limiter
        self._session = requests.Session()
        self._memory_cache: list[dict] = []
        self._lock = threading.Lock()

    def update_user_agent(self) -> None:
        self._session.headers.update({"User-Agent": API["user_agent"]})

    def load_all_stats(self, force: bool = False) -> list[dict]:
        with self._lock:
            if self._memory_cache and not force:
                return list(self._memory_cache)

        fresh = self._fetch_from_api()
        if fresh:
            with self._lock:
                self._memory_cache = fresh
            self._write_disk_cache(fresh)
            return fresh

        disk = self._read_disk_cache()
        if disk:
            age = self._disk_cache_age_hours()
            print(f"[stats_client] Using disk cache ({age:.1f}h old, {len(disk)} mods).")
            with self._lock:
                self._memory_cache = disk
            return disk

        print("[stats_client] No stats available — network failed and disk cache is missing.")
        return []

    def load_from_disk_if_available(self) -> bool:
        disk = self._read_disk_cache()
        if not disk:
            return False
        with self._lock:
            self._memory_cache = disk
        age = self._disk_cache_age_hours()
        print(f"[stats_client] Pre-loaded {len(disk)} mods from disk cache ({age:.1f}h old).")
        return True

    def get_cached(self) -> list[dict]:
        with self._lock:
            return list(self._memory_cache)

    def cache_size(self) -> int:
        with self._lock:
            return len(self._memory_cache)

    def disk_cache_info(self) -> dict:
        age = self._disk_cache_age_hours()
        exists = CACHE_PATH.exists()
        size = len(self._read_disk_cache()) if exists else 0
        return {
            "exists": exists,
            "age_hours": age,
            "mod_count": size,
            "stale": age > CACHE_TTL_HOURS,
        }

    def _fetch_from_api(self) -> list[dict]:
        try:
            self._rate_limiter.wait_for_slot()
            response = self._session.get(
                GGG_STATS_URL,
                headers=build_json_headers(),
                timeout=API["request_timeout_sec"],
            )
            self._rate_limiter.update_from_headers(response.headers)
            response.raise_for_status()
            payload = response.json()
        except Exception as error:
            if isinstance(error, requests.HTTPError) and error.response is not None:
                print(f"[stats_client] Fetch failed: {parse_error_message(error.response)}")
            else:
                print(f"[stats_client] Fetch failed: {error}")
            return []

        flat_models: list[TradeStatSummary] = []
        for group in payload.get("result", []):
            group_label = group.get("label", "")
            for entry in group.get("entries", []):
                flat_models.append(TradeStatSummary(
                    id=entry.get("id", ""),
                    label=entry.get("text", ""),
                    group=group_label,
                ))
        flat = [entry.to_dict() for entry in flat_models]
        print(f"[stats_client] Fetched {len(flat)} mods from the official trade stats endpoint.")
        return flat

    def _write_disk_cache(self, flat: list[dict]) -> None:
        try:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            payload = {"fetched_at": time.time(), "mods": flat}
            with open(CACHE_PATH, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
        except Exception as error:
            print(f"[stats_client] Could not write disk cache: {error}")

    def _read_disk_cache(self) -> list[dict]:
        try:
            if not CACHE_PATH.exists():
                return []
            with open(CACHE_PATH, encoding="utf-8") as handle:
                payload = json.load(handle)
            return [TradeStatSummary.from_dict(item).to_dict() for item in payload.get("mods", [])]
        except Exception as error:
            print(f"[stats_client] Could not read disk cache: {error}")
            return []

    def _disk_cache_age_hours(self) -> float:
        try:
            if not CACHE_PATH.exists():
                return float("inf")
            with open(CACHE_PATH, encoding="utf-8") as handle:
                payload = json.load(handle)
            age_seconds = time.time() - payload.get("fetched_at", 0)
            return age_seconds / 3600
        except Exception:
            return float("inf")
