from __future__ import annotations
"""Small service wrapper around the official trade stats client."""

from api import get_api_manager


def load_all_stats(force: bool = False) -> list[dict]:
    return get_api_manager().stats_client.load_all_stats(force=force)


def load_from_disk_if_available() -> bool:
    return get_api_manager().stats_client.load_from_disk_if_available()


def get_cached_stats() -> list[dict]:
    return get_api_manager().stats_client.get_cached()


def cache_size() -> int:
    return get_api_manager().stats_client.cache_size()


def disk_cache_info() -> dict:
    return get_api_manager().stats_client.disk_cache_info()
