"""Shared colour state and helper functions used by every file in the overlay package."""

from __future__ import annotations

from typing import Optional
from PyQt5.QtGui import QColor

from config import SCORE_COLORS, SCORE_ALPHA
from logic.mod_scorer import score_tier
from models import OutlineColorRole


_OUTLINE_COLORS: dict[OutlineColorRole, str] = {
    OutlineColorRole.SLOT_ONLY: "#ffffff",
    OutlineColorRole.ALL_GOLD: "#ffd700",
    OutlineColorRole.ALL: "#00ff44",
    OutlineColorRole.MINUS1: "#ff8800",
    OutlineColorRole.MINUS2: "#ff2222",
}

_OUTLINE_THICKNESS: int = 3
_OUTLINE_MIN_MATCHING: int = 1
_BADGE_FLAGS: dict[str, bool] = {"mod_count": True}


def set_outline_color(role: OutlineColorRole, hex_colour: str) -> None:
    _OUTLINE_COLORS[role] = hex_colour


def set_outline_palette(
    all_hex: str,
    minus1_hex: str,
    minus2_hex: str,
    slot_only_hex: str = "#ffffff",
    all_gold_hex: str = "#ffd700",
) -> None:
    set_outline_color(OutlineColorRole.ALL, all_hex)
    set_outline_color(OutlineColorRole.MINUS1, minus1_hex)
    set_outline_color(OutlineColorRole.MINUS2, minus2_hex)
    set_outline_color(OutlineColorRole.SLOT_ONLY, slot_only_hex)
    set_outline_color(OutlineColorRole.ALL_GOLD, all_gold_hex)


def set_outline_thickness(pixels: int) -> None:
    global _OUTLINE_THICKNESS
    _OUTLINE_THICKNESS = max(1, pixels)


def set_min_matching(count: int) -> None:
    global _OUTLINE_MIN_MATCHING
    _OUTLINE_MIN_MATCHING = max(0, count)


def set_badge_flag(badge_key: str, enabled: bool) -> None:
    _BADGE_FLAGS[badge_key] = enabled


def get_mod_count_color(matched: int, total_filters: int) -> Optional[QColor]:
    if total_filters == 0:
        return None
    if matched < _OUTLINE_MIN_MATCHING:
        return None

    missing = total_filters - matched
    if missing == 0:
        return QColor(_OUTLINE_COLORS[OutlineColorRole.ALL_GOLD])
    if missing == 1:
        return QColor(_OUTLINE_COLORS[OutlineColorRole.MINUS1])
    return QColor(_OUTLINE_COLORS[OutlineColorRole.MINUS2])


def get_score_color(score: float) -> Optional[QColor]:
    tier = score_tier(score)
    hex_col = SCORE_COLORS.get(tier)
    if not hex_col:
        return None
    color = QColor(hex_col)
    color.setAlpha(SCORE_ALPHA)
    return color
