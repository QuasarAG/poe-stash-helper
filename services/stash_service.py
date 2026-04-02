from __future__ import annotations
"""Higher-level stash workflow helpers used by workers and controllers.

This service keeps raw API details out of the user-interface layer and
returns small, normalized stash-tab models where that makes the rest of the
code easier to read.
"""

from api import get_api_manager
from models import StashTabSummary


def list_stash_summaries(league: str, access_token: str) -> list[StashTabSummary]:
    raw_tabs = get_api_manager().stash_client.list_stashes(
        league=league,
        access_token=access_token,
    )
    return [StashTabSummary.from_api_dict(tab) for tab in raw_tabs]


def list_stashes(league: str, access_token: str) -> list[StashTabSummary]:
    """Compatibility-friendly public name used by workers and tabs.

    The project still calls this function ``list_stashes`` because that name
    is simple and reads well at call sites, but the returned values are now
    clear dataclass objects instead of loosely-shaped dictionaries.
    """
    return list_stash_summaries(league=league, access_token=access_token)


def get_stash(league: str, stash_id: str, access_token: str, force_refresh: bool = False) -> dict:
    return get_api_manager().stash_client.get_stash(
        league=league,
        stash_id=stash_id,
        access_token=access_token,
        force_refresh=force_refresh,
    )
