"""Small service that owns the OAuth login flow.

A beginner-friendly rule of thumb is:
- widgets should ask for a login,
- services should perform the login,
- repositories or config helpers should persist the result.
"""

from __future__ import annotations

import config
from api import get_api_manager


def perform_oauth_login() -> str:
    """Run the official GGG OAuth flow, save the token, and return it."""
    token = get_api_manager().oauth_client.authenticate()
    config.set_key("oauth_token", token)
    return token
