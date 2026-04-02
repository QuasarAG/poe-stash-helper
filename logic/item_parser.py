from __future__ import annotations
"""
logic/item_parser.py — Parse GGG API item objects into a clean representation.

GGG item JSON reference:
https://www.pathofexile.com/developer/docs/reference#type-Item
"""

from dataclasses import dataclass, field
from typing import Optional

from repositories.base_repository import get_default_base_repository


@dataclass
class ParsedMod:
    text: str                    # raw display text
    stat_ids: list[str]          # e.g. ["explicit.stat_1754445556"]
    values: list[float]          # rolled values
    is_crafted: bool = False
    affix_type: str = ""         # "prefix" | "suffix" | "implicit" | "" (unknown)


# Influence types present in PoE
INFLUENCES = ["shaper", "elder", "crusader", "hunter", "redeemer", "warlord",
              "exarch", "eater"]

# Item categories (from GGG extended.category)
ITEM_CATEGORIES = [
    "weapon", "armour", "accessory", "gem", "jewel",
    "flask", "map", "card", "leaguestone", "monster",
]

# Frame types
FRAME_NORMAL  = 0
FRAME_MAGIC   = 1
FRAME_RARE    = 2
FRAME_UNIQUE  = 3
FRAME_GEM     = 4
FRAME_CURRENCY= 5
FRAME_DIVCARD = 6


@dataclass
class ParsedItem:
    # Identity
    id:         str
    name:       str
    base_type:  str
    frame_type: int      # 0=Normal 1=Magic 2=Rare 3=Unique 4=Gem 5=Currency 6=DivCard
    ilvl:       int
    # Grid position in stash
    x: int
    y: int
    w: int
    h: int
    # Mods
    explicit_mods: list[ParsedMod] = field(default_factory=list)
    implicit_mods: list[ParsedMod] = field(default_factory=list)
    crafted_mods:  list[ParsedMod] = field(default_factory=list)
    enchant_mods:  list[ParsedMod] = field(default_factory=list)
    fractured_mods:list[ParsedMod] = field(default_factory=list)
    # Sockets
    links:         int = 0
    sockets:       int = 0
    socket_colors: str = ""   # e.g. "RRGB"
    # Boolean item states
    corrupted:     bool = False
    identified:    bool = True
    mirrored:      bool = False
    split:         bool = False
    fractured:     bool = False
    synthesised:   bool = False
    veiled:        bool = False
    foulborn:      bool = False   # PoE2: item is foulborn (foil variation)
    # Influences (dict: {"shaper": True, "elder": False, ...})
    influences:    dict = field(default_factory=dict)
    # Numeric properties
    quality:       int = 0
    memory_strands: int = 0   # PoE2: Memory Strand count on item
    # Requirements (parsed from item["requirements"])
    req_level:     int = 0
    req_str:       int = 0
    req_dex:       int = 0
    req_int:       int = 0
    # Defence values (local to item, parsed from properties)
    armour:        int = 0
    evasion:       int = 0
    energy_shield: int = 0
    ward:          int = 0
    block:         int = 0
    # Weapon values
    phys_dps:      float = 0.0
    elem_dps:      float = 0.0
    attacks_ps:    float = 0.0

    # Item category (from extended data)
    category:      str = ""   # "weapon", "armour", "accessory", etc.
    sub_category:  str = ""   # "sword", "helmet", "ring", etc.
    # Flavour text (uniques)
    flavour_text:  str = ""
    # Cached scoring results
    score:         Optional[float] = None
    matched_mods:  list[str] = field(default_factory=list)
    total_filters: int = 0   # how many mod filters were active for this item's slot
    # Cached price
    price_chaos:   Optional[float] = None

    @property
    def is_rare(self)     -> bool: return self.frame_type == FRAME_RARE
    @property
    def is_unique(self)   -> bool: return self.frame_type == FRAME_UNIQUE
    @property
    def is_magic(self)    -> bool: return self.frame_type == FRAME_MAGIC
    @property
    def is_normal(self)   -> bool: return self.frame_type == FRAME_NORMAL
    @property
    def is_gem(self)      -> bool: return self.frame_type == FRAME_GEM
    @property
    def is_currency(self) -> bool: return self.frame_type == FRAME_CURRENCY
    @property
    def is_divcard(self)  -> bool: return self.frame_type == FRAME_DIVCARD
    @property
    def is_influenced(self) -> bool: return any(self.influences.values())

    @property
    def equipment_slot(self) -> str:
        """
        Best-effort equipment slot detection.
        Uses sub_category (extended data) when available,
        falls back to base_type keyword matching.
        """
        # 1. Extended data from OAuth API (most reliable)
        if self.sub_category:
            return _subcategory_to_slot(self.sub_category)
        # 2. Exact base_type match against our database (catches most items)
        base_slot = get_default_base_repository().get_slot_for_base_type(self.base_type)
        if base_slot:
            return base_slot
        # 3. Keyword suffix fallback (catches anything not in database)
        # Fallback: keyword match on base_type
        return _detect_slot_from_base(self.base_type)
    @property
    def influence_list(self) -> list[str]:
        return [k for k, v in self.influences.items() if v]
    @property
    def display_name(self) -> str:
        return self.name if self.name else self.base_type


def _parse_mod_list(raw_mods: list[str], extended: dict, is_crafted=False) -> list[ParsedMod]:
    """
    Convert a list of mod strings + extended data into ParsedMod objects.
    extended["mods"]["explicit"] contains stat_id + values per mod.
    """
    parsed = []
    for text in (raw_mods or []):
        parsed.append(ParsedMod(
            text=text,
            stat_ids=[],    # populated below when extended data available
            values=[],
            is_crafted=is_crafted,
        ))

    # Enrich with stat ids if available
    if extended and "mods" in extended:
        categories = (
            ("explicit", parsed) if not is_crafted
            else ("crafted", parsed)
        )
        cat_key = categories[0]
        mods_ext = extended["mods"].get(cat_key, [])
        for i, ext in enumerate(mods_ext):
            if i < len(parsed):
                parsed[i].stat_ids   = [m.get("id", "") for m in ext.get("magnitudes", [])]
                parsed[i].values     = [m.get("min", 0) for m in ext.get("magnitudes", [])]
                # GGG extended data carries "type": "prefix" | "suffix" on each mod entry
                parsed[i].affix_type = ext.get("type", "").lower()

    # Fallback: infer affix_type from MOD_DB when extended data absent
    if not (extended and "mods" in extended):
        try:
            from data.mod_data import MOD_DB as _MDB
            for pm in parsed:
                if pm.affix_type or not pm.stat_ids:
                    continue
                for sid in pm.stat_ids:
                    entry = _MDB.get(sid)
                    if entry and entry.get("affix_type"):
                        pm.affix_type = entry["affix_type"]
                        break
        except Exception:
            pass

    return parsed


def _count_links(item: dict) -> int:
    """Return the largest socket group size."""
    sockets = item.get("sockets", [])
    if not sockets:
        return 0
    groups: dict[int, int] = {}
    for s in sockets:
        g = s.get("group", 0)
        groups[g] = groups.get(g, 0) + 1
    return max(groups.values(), default=0)


def _count_sockets(item: dict) -> int:
    return len(item.get("sockets", []))

def _socket_colors(item: dict) -> str:
    return "".join(s.get("sColour", "?") for s in item.get("sockets", []))

def _parse_influences(raw: dict) -> dict:
    inf = raw.get("influences", {})
    return {k: bool(v) for k, v in inf.items()}

def _parse_defence_value(raw_value: str) -> int:
    """Parse a value like '(347-399)' or '399' → midpoint int."""
    import re as _re
    nums = [int(x) for x in _re.findall(r'\d+', raw_value)]
    if len(nums) == 2:
        return (nums[0] + nums[1]) // 2
    return nums[0] if nums else 0


def _parse_defences(raw: dict) -> dict:
    """Parse armour/evasion/ES/ward/block and weapon stats from item properties."""
    result = {"armour": 0, "evasion": 0, "energy_shield": 0, "ward": 0, "block": 0,
              "phys_dps": 0.0, "elem_dps": 0.0, "attacks_ps": 0.0}
    for prop in raw.get("properties", []):
        name = prop.get("name", "")
        vals = prop.get("values", [])
        if not vals:
            continue
        raw_val = vals[0][0] if vals[0] else "0"
        try:
            if name == "Armour":
                result["armour"] = _parse_defence_value(raw_val)
            elif name == "Evasion Rating":
                result["evasion"] = _parse_defence_value(raw_val)
            elif name == "Energy Shield":
                result["energy_shield"] = _parse_defence_value(raw_val)
            elif name == "Ward":
                result["ward"] = _parse_defence_value(raw_val)
            elif name == "Chance to Block":
                result["block"] = _parse_defence_value(raw_val.replace("%", ""))
            elif name == "Attacks per Second":
                result["attacks_ps"] = float(raw_val)
            elif name == "Physical Damage":
                lo_hi = [float(x) for x in raw_val.split("-") if x.strip()]
                if len(lo_hi) == 2:
                    avg = (lo_hi[0] + lo_hi[1]) / 2
                    result["phys_dps"] = round(avg * result["attacks_ps"], 1)
        except (ValueError, AttributeError):
            pass
    return result


def _parse_quality(raw: dict) -> int:
    """Extract quality from item properties list."""
    for prop in raw.get("properties", []):
        if prop.get("name") == "Quality":
            vals = prop.get("values", [])
            if vals:
                try:
                    return int(str(vals[0][0]).strip("+%"))
                except (ValueError, IndexError):
                    pass
    return 0

def _parse_requirements(raw: dict) -> dict:
    """Parse Level/Str/Dex/Int requirements from item requirements list."""
    result = {"req_level": 0, "req_str": 0, "req_dex": 0, "req_int": 0}
    name_map = {"Level": "req_level", "Str": "req_str", "Dex": "req_dex", "Int": "req_int"}
    for req in raw.get("requirements", []):
        key = name_map.get(req.get("name", ""))
        if key:
            vals = req.get("values", [])
            if vals:
                try:
                    result[key] = int(str(vals[0][0]).strip("+%"))
                except (ValueError, IndexError):
                    pass
    return result


def _parse_category(extended: dict) -> tuple:
    cat = extended.get("category", "")
    sub_cats = extended.get("subcategories", [])
    sub = sub_cats[0] if sub_cats else ""
    return cat, sub

def _parse_memory_strands(raw: dict) -> int:
    """Return Memory Strand count from item properties (PoE2)."""
    for prop in raw.get("properties", []):
        name = prop.get("name", "")
        if "Memory" in name and "Strand" in name:
            vals = prop.get("values", [])
            if vals:
                try:
                    return int(str(vals[0][0]).replace(",", ""))
                except (ValueError, IndexError):
                    pass
    return 0


def parse_item(raw: dict) -> ParsedItem:
    extended = raw.get("extended", {})
    cat, sub = _parse_category(extended)
    return ParsedItem(
        id             = raw.get("id", ""),
        name           = raw.get("name", ""),
        base_type      = raw.get("baseType", raw.get("typeLine", "")),
        frame_type     = raw.get("frameType", 0),
        ilvl           = raw.get("ilvl", 0),
        x              = raw.get("x", 0),
        y              = raw.get("y", 0),
        w              = raw.get("w", 1),
        h              = raw.get("h", 1),
        corrupted      = raw.get("corrupted", False),
        identified     = raw.get("identified", True),
        mirrored       = raw.get("mirrored", False),
        split          = raw.get("split", False),
        fractured      = raw.get("fractured", False),
        synthesised    = raw.get("synthesised", False),
        veiled         = bool(raw.get("veiledMods")),
        foulborn       = bool(raw.get("foilVariation") or raw.get("foulborn", False)),
        influences     = _parse_influences(raw),
        quality        = _parse_quality(raw),
        memory_strands = _parse_memory_strands(raw),
        **_parse_requirements(raw),
        **_parse_defences(raw),
        links          = _count_links(raw),
        sockets        = _count_sockets(raw),
        socket_colors  = _socket_colors(raw),
        category       = cat,
        sub_category   = sub,
        flavour_text   = " ".join(raw.get("flavourText", [])),
        explicit_mods  = _parse_mod_list(raw.get("explicitMods",  []), extended),
        implicit_mods  = _parse_mod_list(raw.get("implicitMods",  []), extended),
        crafted_mods   = _parse_mod_list(raw.get("craftedMods",   []), extended, is_crafted=True),
        enchant_mods   = _parse_mod_list(raw.get("enchantMods",   []), extended),
        fractured_mods = _parse_mod_list(raw.get("fracturedMods", []), extended),
    )


def parse_stash_items(stash: dict) -> list[ParsedItem]:
    items = stash.get("items", [])
    return [parse_item(i) for i in items]


# ── Equipment slot detection ──────────────────────────────────────────────
#
# Strategy: suffix-first matching (most reliable for PoE base types),
# then whole-word matching for helmet/armour/weapon types.
# Belt MUST be checked before leather/body to avoid "Leather Belt" → Body.
# Ring MUST be checked before coral/gold to avoid "Coral Ring" → Amulet.

_SUBCATEGORY_SLOT = {
    "helmet": "Helmet",
    "body":   "Body Armour",
    "gloves": "Gloves",
    "boots":  "Boots",
    "belt":   "Belt",
    "amulet": "Amulet",
    "ring":   "Ring",
    "sword":  "Main Hand",
    "axe":    "Main Hand",
    "mace":   "Main Hand",
    "bow":    "Main Hand",
    "claw":   "Main Hand",
    "dagger": "Main Hand",
    "wand":   "Main Hand",
    "staff":  "Main Hand",
    "sceptre":"Main Hand",
    "shield": "Off-hand",
    "quiver": "Off-hand",
    "jewel":  "Jewel",
    "abyss":  "Abyss Jewel",
    "cluster":"Cluster Jewel",
    "flask":  "Flask",
}

# Exact suffix → slot (checked first, most reliable)
_SUFFIX_SLOT: list[tuple[str, str]] = [
    # Must check Belt before Body Armour (avoids "Leather Belt" → Body Armour)
    (" belt",      "Belt"),
    ("belt",       "Belt"),
    (" sash",      "Belt"),
    ("sash",       "Belt"),
    # Ring before Amulet (avoids "Coral Ring" → Amulet)
    (" ring",      "Ring"),
    ("ring",       "Ring"),
    (" band",      "Ring"),
    # Amulet
    (" amulet",    "Amulet"),
    ("amulet",     "Amulet"),
    (" talisman",  "Amulet"),
    (" pendant",   "Amulet"),
    # Armour
    (" boots",     "Boots"),
    ("boots",      "Boots"),
    (" greaves",   "Boots"),
    ("greaves",    "Boots"),
    (" slippers",  "Boots"),
    ("slippers",   "Boots"),
    (" shoes",     "Boots"),
    (" leggings",  "Boots"),
    (" sabatons",  "Boots"),
    ("sabatons",   "Boots"),
    (" gloves",    "Gloves"),
    ("gloves",     "Gloves"),
    (" gauntlets", "Gloves"),
    ("gauntlets",  "Gloves"),
    (" mitts",     "Gloves"),
    ("mitts",      "Gloves"),
    (" bracers",   "Gloves"),
    (" helmet",    "Helmet"),
    ("helmet",     "Helmet"),
    (" circlet",   "Helmet"),
    (" crown",     "Helmet"),
    (" cap",       "Helmet"),
    (" hat",       "Helmet"),
    (" mask",      "Helmet"),
    (" cowl",      "Helmet"),
    (" hood",      "Helmet"),
    (" bascinet",  "Helmet"),
    (" casque",    "Helmet"),
    (" sallet",    "Helmet"),
    (" burgonet",  "Helmet"),
    (" greathelm", "Helmet"),
    (" visored",   "Helmet"),
    # Flask / Tincture
    (" flask",     "Flask"),
    ("flask",      "Flask"),
    (" tincture",  "Tincture"),
    ("tincture",   "Tincture"),
    # Jewel
    (" jewel",     "Jewel"),
    ("jewel",      "Jewel"),
    # Off-hand
    (" shield",    "Off-hand"),
    ("shield",     "Off-hand"),
    (" buckler",   "Off-hand"),
    ("buckler",    "Off-hand"),
    (" quiver",    "Off-hand"),
    ("quiver",     "Off-hand"),
    # Weapons by suffix
    (" bow",         "Main Hand"),
    (" axe",         "Main Hand"),
    (" axes",        "Main Hand"),
    (" sword",       "Main Hand"),
    (" swords",      "Main Hand"),
    (" blade",       "Main Hand"),
    (" blades",      "Main Hand"),
    (" dagger",      "Main Hand"),
    (" wand",        "Main Hand"),
    (" staff",       "Main Hand"),
    (" stave",       "Main Hand"),
    (" sceptre",     "Main Hand"),
    (" sceptres",    "Main Hand"),
    (" mace",        "Main Hand"),
    (" maul",        "Main Hand"),
    (" claw",        "Main Hand"),
    (" claws",       "Main Hand"),
    (" fist",        "Main Hand"),
    (" foil",        "Main Hand"),
    (" rapier",      "Main Hand"),
    (" warstaff",    "Main Hand"),
    (" runic dagger","Main Hand"),
]

# Whole-word body armour keywords (checked AFTER all suffix rules)
_BODY_ARMOUR_WORDS = {
    "chestplate", "cuirass", "lamellar", "brigandine", "ringmail",
    "chainmail", "scale", "platemail", "plate", "garb", "robe",
    "vestment", "doublet", "regalia", "silken", "jacket", "tunic",
    "coat", "jerkin", "wyrmscale", "dragonscale", "full ringmail",
    "full chainmail", "devout", "vaal", "sacrificial", "sadist",
    "occultist", "carnal", "shagreen", "zodiac",
}

# Exact full-name matches for unique-style bases with no slot suffix
_EXACT_SLOT: dict[str, str] = {
    # Belts
    "stygian vise":           "Belt",
    "micro-distillation band":"Belt",
    "wurm's molt":            "Belt",
    "mechalarm belt":         "Belt",
    # Abyss Jewel
    "searching eye jewel":    "Abyss Jewel",
    "hypnotic eye jewel":     "Abyss Jewel",
    "murderous eye jewel":    "Abyss Jewel",
    "ghastly eye jewel":      "Abyss Jewel",
    "spectral eye jewel":     "Abyss Jewel",
    # Cluster Jewel
    "small cluster jewel":    "Cluster Jewel",
    "medium cluster jewel":   "Cluster Jewel",
    "large cluster jewel":    "Cluster Jewel",
}


def _subcategory_to_slot(sub: str) -> str:
    return _SUBCATEGORY_SLOT.get(sub.lower(), "")


def _detect_slot_from_base(base_type: str) -> str:
    """
    Detect equipment slot from base_type string.
    Uses suffix-first matching to avoid keyword collisions
    (e.g. 'Leather Belt' → Belt, not Body Armour).
    """
    if not base_type:
        return ""
    bt = base_type.lower().strip()

    # 0. Exact name match (for bases with no standard suffix)
    if bt in _EXACT_SLOT:
        return _EXACT_SLOT[bt]

    # 1. Suffix match (most specific, checked first)
    for suffix, slot in _SUFFIX_SLOT:
        if bt.endswith(suffix):
            return slot

    # 2. Body armour whole-word match
    words = set(bt.split())
    if words & _BODY_ARMOUR_WORDS:
        return "Body Armour"

    # 3. Weapon keyword anywhere
    for kw, slot in [("bow", "Main Hand"), ("claw", "Main Hand"),
                     ("foil", "Main Hand"), ("maul", "Main Hand"),
                     ("gavel", "Main Hand"), ("pernach", "Main Hand")]:
        if kw in bt:
            return slot

    return ""
