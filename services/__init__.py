"""Application services.

The service layer owns higher-level workflows.
It sits above repositories and API clients, and below controllers / views.
"""

from services.stash_service import get_stash, list_stashes
from services.stats_service import load_all_stats, load_from_disk_if_available
from services.oauth_login_service import perform_oauth_login

__all__ = [
    "get_stash",
    "list_stashes",
    "load_all_stats",
    "load_from_disk_if_available",
    "perform_oauth_login",
]
