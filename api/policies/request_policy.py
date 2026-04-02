from __future__ import annotations
"""Small shared helpers for API request policies and headers."""

from config import API


def build_json_headers(access_token: str | None = None, extra_headers: dict | None = None) -> dict:
    headers = {
        "User-Agent": API["user_agent"],
        "Accept": "application/json",
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if extra_headers:
        headers.update(extra_headers)
    return headers
