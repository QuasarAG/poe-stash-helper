from __future__ import annotations

from models import ItemRarity
"""
Constants and small static lookup tables for the item property filter panel.

This file exists so the public panel and the content builder do not need to
start with a long wall of static data. For a beginner, that makes the code
much easier to scan:

- constants.py answers "what are the fixed values?"
- widgets.py answers "what small reusable controls exist?"
- content.py answers "how is the panel content built for one slot?"
- panel.py answers "what is the public widget the rest of the app uses?"
"""

TWO_COLUMN_THRESHOLD = 560

RARITY_STYLES = {
    ItemRarity.NORMAL: ("#aaaaaa", "#222222"),
    ItemRarity.MAGIC: ("#5588ff", "#0e1830"),
    ItemRarity.RARE: ("#ccaa22", "#261e00"),
    ItemRarity.UNIQUE: ("#bb6622", "#261000"),
}


def sections_for_slot(slot: str) -> set[str]:
    """
    Return the set of section identifiers that should be visible for a slot.

    This is view-related configuration, but it is still pure data logic.
    Keeping it here avoids burying an important rule set inside widget code.
    """
    visible_sections = {"rarity", "requirements"}

    if slot in ("Any", ""):
        return {
            "rarity",
            "requirements",
            "weapon",
            "armour",
            "socket",
            "misc_quality",
            "misc_other",
            "memory_strand",
        }

    if slot == "Main Hand":
        visible_sections |= {"weapon", "socket", "misc_quality", "misc_other"}
    elif slot == "Off-hand":
        visible_sections |= {"armour", "weapon", "socket", "misc_quality", "misc_other"}
    elif slot in {"Helmet", "Body Armour", "Gloves", "Boots"}:
        visible_sections |= {"armour", "socket", "misc_quality", "misc_other"}
    elif slot == "Belt":
        visible_sections |= {"misc_quality", "misc_other"}
    elif slot in {"Ring", "Amulet"}:
        visible_sections |= {"misc_other"}
    elif slot in {"Jewel", "Abyss Jewel", "Cluster Jewel"}:
        visible_sections |= {"misc_other"}
    elif slot in {"Flask", "Tincture"}:
        visible_sections |= {"misc_quality", "misc_other"}

    return visible_sections
