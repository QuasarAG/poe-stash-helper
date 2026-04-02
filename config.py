from __future__ import annotations
"""
config.py — central configuration for PoE Stash Helper.

This file keeps the small project-wide defaults that multiple layers need:
- OAuth registration details
- official Path of Exile API base URL
- safe default request pacing
- overlay defaults
- persisted runtime config helpers

IMPORTANT API COMPLIANCE NOTES
    The Path of Exile developer guidelines require an identifiable User-Agent
    header in the format:

        User-Agent: OAuth {$clientId}/{$version} (contact: {$contact})

    Public desktop clients must also use a local redirect URI together with the
    Authorization Code + PKCE flow. We therefore default to 127.0.0.1 here.
"""

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "data" / "config.json"
APP_VERSION = "1.0.0"
DEFAULT_CONTACT = "fabien.ouvre@hotmail.fr"

# ── GGG OAuth2 ────────────────────────────────────────────────────────────
OAUTH = {
    "client_id": "poestashhelper",
    "redirect_uri": "http://localhost:7878/callback",
    "scope": "account:stashes",
    "auth_url": "https://www.pathofexile.com/oauth/authorize",
    "token_url": "https://www.pathofexile.com/oauth/token",
}


def build_user_agent(client_id: str | None = None) -> str:
    """Return a User-Agent string that follows GGG's required prefix format."""
    clean_client_id = (client_id or OAUTH["client_id"] or "poestashhelper").strip()
    if not clean_client_id:
        clean_client_id = "poestashhelper"
    return (
        f"OAuth {clean_client_id}/{APP_VERSION} "
        f"(contact: {DEFAULT_CONTACT}) PoE Stash Helper desktop app"
    )


# ── GGG API ───────────────────────────────────────────────────────────────
API = {
    "base_url": "https://api.pathofexile.com",
    # Public desktop applications share rate limits with other public clients,
    # so we deliberately use conservative pacing.
    "stash_rate_limit": {"requests": 20, "window_sec": 60},
    "trade_rate_limit": {"requests": 8, "window_sec": 10},
    "min_request_delay": 1.5,
    "request_timeout_sec": 30,
}
API["user_agent"] = build_user_agent()

# ── Overlay grid geometry ─────────────────────────────────────────────────
STASH_GRID = {
    "grid_screen_x": 100,
    "grid_screen_y": 140,
    "cell_size": 26.0,
    "cols": 24,
    "rows": 24,
}

# ── Scoring colours ───────────────────────────────────────────────────────
SCORE_COLORS = {
    "tier1": "#00ff88",
    "tier2": "#aaff00",
    "tier3": "#ffdd00",
    "tier4": "#ff8800",
    "tier5": "#ff3333",
    "no_match": None,
}

SCORE_ALPHA = 180

# ── UI ────────────────────────────────────────────────────────────────────
UI = {
    "hotkey_toggle_overlay": "F9",
    "hotkey_refresh": "F10",
    "outline_thickness": 3,
    "score_font_size": 9,
    "opacity": 0.92,
}

# ── Persistence ───────────────────────────────────────────────────────────
_runtime: dict = {}


def load_config() -> dict:
    global _runtime
    defaults = {
        "league": "Standard",
        "account_name": "",
        "selected_stash": "",
        "mod_filters": [],
        "oauth_token": None,
        "stash_grid": STASH_GRID.copy(),
        "ui": UI.copy(),
        "user_agent": build_user_agent(),
    }
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                saved = json.load(f)
            defaults.update(saved)
        except Exception:
            pass
    _runtime = defaults
    API["user_agent"] = _runtime.get("user_agent") or build_user_agent()
    return _runtime


def save_config() -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(_runtime, f, indent=2)


def get(key, default=None):
    return _runtime.get(key, default)


def set_key(key, value) -> None:
    _runtime[key] = value
    save_config()
