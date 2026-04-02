"""HTTP client layer for the official Path of Exile APIs.

This package now has a clearer internal structure:
- api.clients   -> thin HTTP clients
- api.policies  -> rate limiting, headers, error helpers
- api.cache     -> small API-specific caches
- api.manager   -> one place that wires clients together
"""

from api.manager import get_api_manager

__all__ = ["get_api_manager"]
