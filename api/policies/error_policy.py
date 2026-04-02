from __future__ import annotations
"""Small API error helpers used by multiple clients."""

import json
import time
import requests


class PoeApiError(RuntimeError):
    """User-facing API error with a readable message."""


def parse_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
        error_obj = payload.get("error")
        if isinstance(error_obj, dict):
            message = error_obj.get("message") or "Unknown API error"
            code = error_obj.get("code")
            if code is not None:
                return f"{message} (code {code})"
            return message
    except (ValueError, json.JSONDecodeError, AttributeError):
        pass
    return f"HTTP {response.status_code}"


def raise_for_error_response(response: requests.Response) -> None:
    if response.status_code < 400:
        return
    raise PoeApiError(parse_error_message(response))


def wait_from_retry_after(response: requests.Response, default_seconds: float = 60.0) -> None:
    retry_after = response.headers.get("Retry-After")
    try:
        delay = float(retry_after) if retry_after is not None else default_seconds
    except ValueError:
        delay = default_seconds
    time.sleep(max(0.0, delay))
