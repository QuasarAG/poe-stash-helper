from __future__ import annotations
"""Official OAuth 2.1 Authorization Code + PKCE client for Path of Exile.

This file handles only the OAuth flow itself:
- generate PKCE verifier and challenge
- open the browser to the official authorisation page
- receive the local callback on 127.0.0.1
- exchange the code for tokens
- cache and refresh tokens

WHY THIS FILE IS BETTER THAN THE OLD FLAT auth.py
    It is now a dedicated client under api/clients, which makes it clearer that
    this layer is about talking to an external HTTP API rather than running the
    higher-level login workflow used by the rest of the desktop application.
"""

import base64
import hashlib
import json
import os
import secrets
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional

import requests

from config import API, OAUTH
from api.policies.request_policy import build_json_headers
from api.policies.error_policy import PoeApiError, parse_error_message

TOKEN_PATH = Path(__file__).resolve().parents[2] / ".token_cache.json"
_CALLBACK_HOST = "127.0.0.1"
_CALLBACK_PORT = 7878
_CALLBACK_TIMEOUT_SECONDS = 180


def _generate_pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(os.urandom(40)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


class _CallbackHandler(BaseHTTPRequestHandler):
    code: Optional[str] = None
    returned_state: Optional[str] = None
    error: Optional[str] = None

    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _CallbackHandler.code = params.get("code", [None])[0]
        _CallbackHandler.returned_state = params.get("state", [None])[0]
        _CallbackHandler.error = params.get("error", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(
            b"<h2>Authentication complete.</h2><p>You can close this tab now.</p>"
        )

    def log_message(self, *_):
        return


def _run_callback_server() -> tuple[Optional[str], Optional[str], Optional[str]]:
    _CallbackHandler.code = None
    _CallbackHandler.returned_state = None
    _CallbackHandler.error = None
    server = HTTPServer((_CALLBACK_HOST, _CALLBACK_PORT), _CallbackHandler)
    server.timeout = _CALLBACK_TIMEOUT_SECONDS
    server.handle_request()
    return (
        _CallbackHandler.code,
        _CallbackHandler.returned_state,
        _CallbackHandler.error,
    )


def load_cached_token() -> Optional[dict]:
    if not TOKEN_PATH.exists():
        return None
    try:
        with open(TOKEN_PATH, encoding="utf-8") as handle:
            token = json.load(handle)
        if token.get("expires_at", 0) > time.time() + 300:
            return token
    except Exception:
        return None
    return None


def _save_token(token: dict) -> None:
    token["expires_at"] = time.time() + token.get("expires_in", 3600)
    with open(TOKEN_PATH, "w", encoding="utf-8") as handle:
        json.dump(token, handle)


class OAuthClient:
    def __init__(self):
        self._session = requests.Session()

    def authenticate(self) -> str:
        cached = load_cached_token()
        if cached:
            return cached["access_token"]

        if TOKEN_PATH.exists():
            try:
                with open(TOKEN_PATH, encoding="utf-8") as handle:
                    stale = json.load(handle)
                refreshed = self.refresh_token(stale)
                if refreshed:
                    return refreshed["access_token"]
            except Exception:
                pass

        verifier, challenge = _generate_pkce_pair()
        expected_state = secrets.token_urlsafe(16)
        auth_url = (
            f"{OAUTH['auth_url']}?"
            + urllib.parse.urlencode(
                {
                    "client_id": OAUTH["client_id"],
                    "response_type": "code",
                    "scope": OAUTH["scope"],
                    "state": expected_state,
                    "redirect_uri": OAUTH["redirect_uri"],
                    "code_challenge": challenge,
                    "code_challenge_method": "S256",
                }
            )
        )

        print("[OAuth] Opening browser for official Path of Exile authorisation...")
        print("[OAuth] Public desktop clients show an authenticity warning by design.")
        webbrowser.open(auth_url)

        code, returned_state, error = _run_callback_server()
        if error:
            raise PoeApiError(f"OAuth authorisation failed: {error}")
        if not code:
            raise PoeApiError(
                f"OAuth timeout: no authorisation code was received within "
                f"{_CALLBACK_TIMEOUT_SECONDS} seconds."
            )
        if returned_state != expected_state:
            raise PoeApiError(
                "OAuth state validation failed. The browser response did not match "
                "the login request created by this application."
            )

        response = self._session.post(
            OAUTH["token_url"],
            data={
                "client_id": OAUTH["client_id"],
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": OAUTH["redirect_uri"],
                "code_verifier": verifier,
            },
            headers=build_json_headers(),
            timeout=15,
        )
        if not response.ok:
            raise PoeApiError(f"OAuth token exchange failed: {parse_error_message(response)}")
        token = response.json()
        _save_token(token)
        return token["access_token"]

    def refresh_token(self, token: dict) -> Optional[dict]:
        refresh_token = token.get("refresh_token")
        if not refresh_token:
            return None
        response = self._session.post(
            OAUTH["token_url"],
            data={
                "client_id": OAUTH["client_id"],
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            headers=build_json_headers(),
            timeout=15,
        )
        if not response.ok:
            return None
        refreshed = response.json()
        _save_token(refreshed)
        return refreshed
