"""Shared constants for the mod search user interface."""

from __future__ import annotations

from models import ModSearchCategory

MAX_SEARCH_RESULTS = 200

CONQUEROR_INFLUENCES = {"Shaper", "Elder", "Crusader", "Redeemer", "Warlord", "Hunter"}
ELDRITCH_INFLUENCES = {"Exarch", "Eater", "Eldritch"}

MOD_SEARCH_CATEGORY_BUTTONS = [
    ("All", ModSearchCategory.ALL, "Show all mods"),
    ("Prefix", ModSearchCategory.PREFIX, "Normal prefix mods"),
    ("Suffix", ModSearchCategory.SUFFIX, "Normal suffix mods"),
    ("Influenced", ModSearchCategory.INFLUENCE, "Shaper / Elder / Conqueror mods"),
    ("Eldritch", ModSearchCategory.ELDRITCH, "Exarch / Eater implicits"),
    ("Pseudo", ModSearchCategory.PSEUDO, "Pseudo mods - sum of multiple stats (e.g. total resistance)"),
    ("[META]", ModSearchCategory.META, "Meta filters - item structure (affix count, influence, enchants...)"),
]

INFLUENCE_TAG_COLOURS = {
    "Shaper":   "#55aaff",
    "Elder":    "#c0c0c0",
    "Crusader": "#aaddff",
    "Redeemer": "#ffaacc",
    "Warlord":  "#ffaa55",
    "Hunter":   "#aaffaa",
    "Exarch":   "#ffdd88",
    "Eater":    "#cc88ff",
}

AFFIX_TYPE_COLOURS = {
    "prefix":   "#6688cc",
    "suffix":   "#668866",
    "implicit": "#aa88cc",
    "pseudo":   "#bb88ff",
    "meta":     "#55cccc",
}

AFFIX_TYPE_BADGE_TEXT = {
    "prefix":   "PRE",
    "suffix":   "SUF",
    "implicit": "IMP",
    "pseudo":   "PSE",
    "meta":     "MTA",
}

INFLUENCE_SORT_ORDER = {
    "Shaper": 0, "Elder": 1, "Crusader": 2, "Redeemer": 3,
    "Warlord": 4, "Hunter": 5, "Exarch": 6, "Eater": 7, "Eldritch": 8,
}

AFFIX_TYPE_SORT_ORDER = {
    "prefix": 0, "suffix": 1, "implicit": 2, "pseudo": -2, "meta": -1,
}
