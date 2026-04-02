from __future__ import annotations
"""
logic/item_filter.py — Comprehensive item property filter system.

Mirrors the PoE trade website search capabilities:
  - Ternary states (ANY / YES / NO) for boolean properties
  - Rarity multi-select
  - Per-influence ternary filters
  - Numeric ranges: ilvl, quality, links, sockets, gem level/quality, map tier
  - Item category / sub-category selection
  - Name/base contains search

TriState values:
    0 = ANY  (don't filter on this property)
    1 = YES  (item must have this)
   -1 = NO   (item must NOT have this)
"""

from dataclasses import dataclass, field
from typing import Optional, List

# ── TriState ───────────────────────────────────────────────────────────────
ANY = 0
YES = 1
NO  = -1
TRISTATE_LABELS = {ANY: "Any", YES: "Yes", NO: "No"}


def tristate_match(state: int, value: bool) -> bool:
    if state == ANY: return True
    if state == YES: return value
    return not value


# ── Rarity map ─────────────────────────────────────────────────────────────
RARITIES = {
    "Normal":   0,
    "Magic":    1,
    "Rare":     2,
    "Unique":   3,
    "Gem":      4,
    "Currency": 5,
    "Divcard":  6,
}

# ── Influences ─────────────────────────────────────────────────────────────
INFLUENCE_TYPES = [
    "shaper", "elder", "crusader", "hunter",
    "redeemer", "warlord", "exarch", "eater",
]
INFLUENCE_LABELS = {
    "shaper":   "Shaper",
    "elder":    "Elder",
    "crusader": "Crusader",
    "hunter":   "Hunter",
    "redeemer": "Redeemer",
    "warlord":  "Warlord",
    "exarch":   "Searing Exarch",
    "eater":    "Eater of Worlds",
}

# ── Categories ─────────────────────────────────────────────────────────────
ITEM_CATEGORIES = {
    "weapon":    "Weapon",
    "armour":    "Armour",
    "accessory": "Accessory",
    "jewel":     "Jewel",
    "flask":     "Flask",
    "map":       "Map",
    "gem":       "Gem",
    "card":      "Div. Card",
    "currency":  "Currency",
}
SUB_CATEGORIES = {
    "weapon":    ["sword", "axe", "mace", "bow", "claw", "dagger",
                  "wand", "staff", "sceptre", "shield"],
    "armour":    ["helmet", "body", "gloves", "boots"],
    "accessory": ["ring", "amulet", "belt"],
    "jewel":     ["base", "abyss", "cluster"],
    "flask":     ["life", "mana", "hybrid", "utility"],
    "gem":       ["active", "support"],
}


@dataclass
class NumericRange:
    min: Optional[float] = None
    max: Optional[float] = None

    def matches(self, value: Optional[float]) -> bool:
        if value is None:
            return self.min is None and self.max is None
        if self.min is not None and value < self.min: return False
        if self.max is not None and value > self.max: return False
        return True

    def is_set(self) -> bool:
        return self.min is not None or self.max is not None

    def to_dict(self) -> dict:
        return {"min": self.min, "max": self.max}

    @classmethod
    def from_dict(cls, d: dict) -> "NumericRange":
        return cls(min=d.get("min"), max=d.get("max"))


@dataclass
class ItemFilter:
    """Complete item property filter — mirrors PoE trade website."""

    # Status (ternary)
    corrupted:   int = ANY
    identified:  int = ANY
    mirrored:    int = ANY
    split:       int = ANY
    fractured:   int = ANY
    synthesised: int = ANY
    veiled:      int = ANY
    crafted:     int = ANY

    # Rarity (list of allowed frame_type ints; empty = any)
    rarities: List[int] = field(default_factory=list)

    # Influences (per-type ternary; any_influence = has at least one)
    influences:    dict = field(default_factory=dict)
    any_influence: int = ANY

    # Numeric ranges
    ilvl:        NumericRange = field(default_factory=NumericRange)
    quality:     NumericRange = field(default_factory=NumericRange)
    links:       NumericRange = field(default_factory=NumericRange)
    sockets:     NumericRange = field(default_factory=NumericRange)
    gem_level:   NumericRange = field(default_factory=NumericRange)
    gem_quality: NumericRange = field(default_factory=NumericRange)
    map_tier:    NumericRange = field(default_factory=NumericRange)
    stack_size:  NumericRange = field(default_factory=NumericRange)

    # Category
    categories:      List[str] = field(default_factory=list)
    sub_categories:  List[str] = field(default_factory=list)

    # Text search
    name_contains: str = ""

    def is_empty(self) -> bool:
        return (
            all(getattr(self, s) == ANY for s in
                ["corrupted","identified","mirrored","split",
                 "fractured","synthesised","veiled","crafted"])
            and not self.rarities
            and all(v == ANY for v in self.influences.values())
            and self.any_influence == ANY
            and not any([self.ilvl, self.quality, self.links, self.sockets,
                         self.gem_level, self.gem_quality, self.map_tier,
                         self.stack_size])
            and not self.categories
            and not self.sub_categories
            and not self.name_contains
        )

    def __bool__(self) -> bool:
        return self.is_set()

    def is_set(self) -> bool:
        if self.ilvl.is_set(): return True
        if self.quality.is_set(): return True
        if self.links.is_set(): return True
        if self.sockets.is_set(): return True
        if self.gem_level.is_set(): return True
        if self.gem_quality.is_set(): return True
        if self.map_tier.is_set(): return True
        if self.stack_size.is_set(): return True
        return not self.is_empty()

    def matches(self, item) -> bool:
        if not tristate_match(self.corrupted,   item.corrupted):   return False
        if not tristate_match(self.identified,  item.identified):  return False
        if not tristate_match(self.mirrored,    item.mirrored):    return False
        if not tristate_match(self.split,       item.split):       return False
        if not tristate_match(self.fractured,   item.fractured):   return False
        if not tristate_match(self.synthesised, item.synthesised): return False
        if not tristate_match(self.veiled,      item.veiled):      return False
        if self.crafted != ANY:
            if not tristate_match(self.crafted, bool(item.crafted_mods)): return False

        if self.rarities and item.frame_type not in self.rarities:
            return False

        if self.any_influence != ANY:
            if not tristate_match(self.any_influence, item.is_influenced): return False
        for inf_type, state in self.influences.items():
            if state == ANY: continue
            if not tristate_match(state, item.influences.get(inf_type, False)):
                return False

        if not self.ilvl.matches(float(item.ilvl)):       return False
        if not self.quality.matches(float(item.quality)): return False
        if not self.links.matches(float(item.links)):     return False
        if not self.sockets.matches(float(item.sockets)): return False

        if self.categories and item.category not in self.categories:
            return False
        if self.sub_categories and item.sub_category not in self.sub_categories:
            return False

        if self.name_contains:
            haystack = (item.display_name + " " + item.base_type).lower()
            if self.name_contains.lower() not in haystack:
                return False

        return True

    def to_dict(self) -> dict:
        return {
            "corrupted": self.corrupted, "identified": self.identified,
            "mirrored": self.mirrored, "split": self.split,
            "fractured": self.fractured, "synthesised": self.synthesised,
            "veiled": self.veiled, "crafted": self.crafted,
            "rarities": self.rarities,
            "influences": self.influences, "any_influence": self.any_influence,
            "ilvl": self.ilvl.to_dict(), "quality": self.quality.to_dict(),
            "links": self.links.to_dict(), "sockets": self.sockets.to_dict(),
            "gem_level": self.gem_level.to_dict(),
            "gem_quality": self.gem_quality.to_dict(),
            "map_tier": self.map_tier.to_dict(),
            "stack_size": self.stack_size.to_dict(),
            "categories": self.categories, "sub_categories": self.sub_categories,
            "name_contains": self.name_contains,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ItemFilter":
        f = cls()
        for s in ["corrupted","identified","mirrored","split",
                  "fractured","synthesised","veiled","crafted"]:
            setattr(f, s, d.get(s, ANY))
        f.rarities      = d.get("rarities", [])
        f.influences    = d.get("influences", {})
        f.any_influence = d.get("any_influence", ANY)
        for r in ["ilvl","quality","links","sockets","gem_level",
                  "gem_quality","map_tier","stack_size"]:
            setattr(f, r, NumericRange.from_dict(d.get(r, {})))
        f.categories    = d.get("categories", [])
        f.sub_categories = d.get("sub_categories", [])
        f.name_contains = d.get("name_contains", "")
        return f


@dataclass
class FilterSet:
    """
    A complete named filter preset combining item property filters
    and mod stat filters. This is what loadouts store.
    """
    name:        str = ""
    item_filter: ItemFilter = field(default_factory=ItemFilter)
    mod_filters: list = field(default_factory=list)   # List[ModFilter]
    mode:        str = "score"   # "score" | "price"

    def to_dict(self) -> dict:
        from logic.mod_scorer import ModFilter
        return {
            "name":        self.name,
            "item_filter": self.item_filter.to_dict(),
            "mod_filters": [
                m.to_dict() if hasattr(m, "to_dict") else m
                for m in self.mod_filters
            ],
            "mode": self.mode,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FilterSet":
        from logic.mod_scorer import ModFilter
        fs = cls()
        fs.name        = d.get("name", "")
        fs.item_filter = ItemFilter.from_dict(d.get("item_filter", {}))
        fs.mod_filters = [
            ModFilter.from_dict(m) if isinstance(m, dict) else m
            for m in d.get("mod_filters", [])
        ]
        fs.mode = d.get("mode", "score")
        return fs


def apply_item_filter(items: list, item_filter: ItemFilter) -> list:
    """Return only items passing the item filter."""
    if item_filter.is_empty():
        return items
    return [i for i in items if item_filter.matches(i)]
