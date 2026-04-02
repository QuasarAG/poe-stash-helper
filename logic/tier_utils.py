from __future__ import annotations
"""logic/tier_utils.py — Tier helpers. Now fully slot-aware via slot_tiers."""
from typing import Optional


def _tiers(stat_id: str, slot: str = ""):
    from data.mod_data import MOD_DB
    entry = MOD_DB.get(stat_id)
    if not entry: return []
    if slot:
        st = entry.get("slot_tiers", {})
        if slot in st: return st[slot]
    return entry.get("tiers", [])


def get_tier(stat_id: str, value: float, slot: str = "") -> Optional[int]:
    for rank, (lo, hi) in enumerate(_tiers(stat_id, slot), start=1):
        if lo <= value <= hi: return rank
    return None

def get_tier_count(stat_id: str, slot: str = "") -> int:
    return len(_tiers(stat_id, slot))

def get_tier_range(stat_id: str, tier: int, slot: str = "") -> Optional[tuple]:
    t = _tiers(stat_id, slot)
    return tuple(t[tier - 1]) if 1 <= tier <= len(t) else None

def get_t1_min(stat_id: str, slot: str = "") -> Optional[float]:
    r = get_tier_range(stat_id, 1, slot)
    return r[0] if r else None

def tier_label(tier: Optional[int]) -> str:
    return f"T{tier}" if tier is not None else "T?"
