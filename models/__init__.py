"""Small data models used to make the project easier to read.

These dataclasses are intentionally simple. They are not meant to introduce
a heavy framework or complicated object graph. Their job is only to give a
few important pieces of app data a stable, self-documenting shape.
"""

from models.enums import (
    ActiveModBehaviour,
    ItemRarity,
    ModSearchCategory,
    OutlineColorRole,
    StashTabType,
    UpdateMode,
)
from models.scan_models import ScanRequest, ScanResult
from models.stash_models import StashTabSummary, coerce_stash_tab_summary
from models.trade_stat_models import TradeStatSummary

__all__ = [
    "ActiveModBehaviour",
    "ItemRarity",
    "ModSearchCategory",
    "OutlineColorRole",
    "StashTabType",
    "UpdateMode",
    "ScanRequest",
    "ScanResult",
    "StashTabSummary",
    "TradeStatSummary",
    "coerce_stash_tab_summary",
]
