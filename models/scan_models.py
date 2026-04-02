from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ScanRequest:
    """Immutable input data for one stash scan.

    Keeping these values together makes worker creation easier to read than
    passing a long list of loosely-related positional arguments.
    """

    access_token: str
    account_name: str
    league: str
    stash_id: str
    filters: list[Any] = field(default_factory=list)
    scan_id: int = 0


@dataclass
class ScanResult:
    """Output produced by a finished stash scan."""

    items: list[Any] = field(default_factory=list)
    scan_id: int = 0
