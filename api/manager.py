from __future__ import annotations
"""Central access point for API clients.

WHY THIS FILE EXISTS
    Earlier parts of the project imported separate flat API modules directly.
    That worked, but it scattered request setup, user-agent refresh behaviour,
    and rate-limit configuration across multiple files.

    ApiManager keeps the external HTTP clients in one place so the rest of the
    app can say "give me the stash client" or "give me the stats client"
    without knowing how those clients are configured internally.
"""

from config import API
from api.clients.oauth_client import OAuthClient
from api.clients.stash_client import StashClient
from api.clients.stats_client import StatsClient
from api.policies.rate_limiter import RateLimiter


class ApiManager:
    def __init__(self):
        self.oauth_client = OAuthClient()
        self.stash_client = StashClient(RateLimiter(**API["stash_rate_limit"]))
        self.stats_client = StatsClient(RateLimiter(**API["trade_rate_limit"]))
        self.refresh_runtime_settings()

    def refresh_runtime_settings(self) -> None:
        self.stash_client.update_user_agent()
        self.stats_client.update_user_agent()


_api_manager = ApiManager()


def get_api_manager() -> ApiManager:
    return _api_manager
