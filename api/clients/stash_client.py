from __future__ import annotations
"""Thin client for the official Path of Exile account stashes endpoints."""

import requests

from config import API
from api.cache import stash_response_cache
from api.policies.error_policy import PoeApiError, parse_error_message, wait_from_retry_after
from api.policies.request_policy import build_json_headers
from api.policies.rate_limiter import RateLimiter


class StashClient:
    def __init__(self, rate_limiter: RateLimiter):
        self._session = requests.Session()
        self._rate_limiter = rate_limiter

    def update_user_agent(self) -> None:
        self._session.headers.update({"User-Agent": API["user_agent"]})

    def list_stashes(self, league: str, access_token: str) -> list:
        for _ in range(2):
            self._rate_limiter.wait_for_slot()
            response = self._session.get(
                f"{API['base_url']}/stash/{league}",
                headers=build_json_headers(access_token),
                timeout=API["request_timeout_sec"],
            )
            self._rate_limiter.update_from_headers(response.headers)
            if response.status_code == 429:
                wait_from_retry_after(response)
                continue
            if not response.ok:
                raise PoeApiError(parse_error_message(response))
            return response.json().get("stashes", [])
        raise PoeApiError("Stash list request was rate-limited repeatedly.")

    def get_stash(self, league: str, stash_id: str, access_token: str, force_refresh: bool = False) -> dict:
        cache_key = f"{league}_{stash_id}"
        if not force_refresh:
            cached = stash_response_cache.load(cache_key)
            if cached:
                print("[stash_client] Returning cached stash tab.")
                return cached

        headers = {}
        etag = stash_response_cache.get_etag(cache_key)
        if etag:
            headers["If-None-Match"] = etag

        for _ in range(2):
            self._rate_limiter.wait_for_slot()
            response = self._session.get(
                f"{API['base_url']}/stash/{league}/{stash_id}",
                headers=build_json_headers(access_token, headers),
                timeout=API["request_timeout_sec"],
            )
            self._rate_limiter.update_from_headers(response.headers)
            if response.status_code == 304:
                cached = stash_response_cache.load(cache_key)
                if cached:
                    print("[stash_client] 304 Not Modified — reusing cached stash tab.")
                    return cached
                stash_response_cache.invalidate(cache_key)
                return self.get_stash(league, stash_id, access_token, force_refresh=True)
            if response.status_code == 429:
                wait_from_retry_after(response)
                continue
            if not response.ok:
                raise PoeApiError(parse_error_message(response))
            stash = response.json().get("stash", {})
            new_etag = response.headers.get("ETag") or response.headers.get("etag")
            stash_response_cache.save(cache_key, stash, new_etag)
            return stash
        raise PoeApiError("Stash fetch was rate-limited repeatedly.")
