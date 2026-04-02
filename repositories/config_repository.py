from __future__ import annotations

"""
repositories/config_repository.py
─────────────────────────────────────────────────────────────────────────────
Small repository-style helpers for persisted configuration values.

WHY THIS FILE EXISTS
    Parts of the project need to read and write user settings such as:
        - selected league
        - selected stash tab
        - OAuth client id
        - custom user agent

    Earlier, some of this logic lived mixed inside UI-related files.
    Pulling it into a repository keeps the data responsibility in one place.
"""

import config
from api import get_api_manager


def get_config_value(key: str, default=None):
    """Read one value from the application's config runtime cache."""
    return config.get(key, default)


def set_config_value(key: str, value) -> None:
    """Write one config value and persist it through the shared config module."""
    config.set_key(key, value)


def save_client_id(client_id: str) -> None:
    """Store the OAuth client id and rebuild the default compliant user-agent."""
    clean_client_id = client_id.strip()
    config.OAUTH["client_id"] = clean_client_id
    config.API["user_agent"] = config.build_user_agent(clean_client_id)
    config.set_key("user_agent", config.API["user_agent"])
    get_api_manager().refresh_runtime_settings()


def save_user_agent(user_agent: str) -> None:
    """
    Save the custom user agent and update already-created API clients.

    A public Path of Exile application must send an identifiable User-Agent.
    We therefore keep this in one place and immediately push the new value into
    the shared ApiManager so future requests use the updated header.
    """
    clean_user_agent = user_agent.strip()
    config.API["user_agent"] = clean_user_agent
    config.set_key("user_agent", clean_user_agent)
    get_api_manager().refresh_runtime_settings()


def get_saved_league() -> str:
    """Return the saved league, or the current project default."""
    return config.get("league") or "Mirage"


def get_saved_stash_id() -> str:
    """Return the saved stash-tab id, or an empty string when none is stored."""
    return config.get("selected_stash") or ""


def save_league(league_name: str) -> None:
    """Persist the currently selected league."""
    config.set_key("league", league_name)


def save_stash_id(stash_tab_id: str) -> None:
    """Persist the currently selected stash tab id."""
    config.set_key("selected_stash", stash_tab_id)
