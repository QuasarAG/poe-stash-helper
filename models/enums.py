from __future__ import annotations

from enum import Enum


class OutlineColorRole(str, Enum):
    """Meaning of each overlay outline colour."""

    ALL = "all"
    MINUS1 = "minus1"
    MINUS2 = "minus2"
    SLOT_ONLY = "slot_only"
    ALL_GOLD = "all_gold"


class ActiveModBehaviour(str, Enum):
    """How one active-mod group should evaluate its rows."""

    AND = "AND"
    NOT = "NOT"
    IF = "IF"
    COUNT = "COUNT"


class ItemRarity(str, Enum):
    """User-facing item rarity labels used by filters."""

    NORMAL = "Normal"
    MAGIC = "Magic"
    RARE = "Rare"
    UNIQUE = "Unique"


class ModSearchCategory(str, Enum):
    """Categories shown above the mod search results table."""

    ALL = "all"
    PREFIX = "prefix"
    SUFFIX = "suffix"
    INFLUENCE = "influence"
    ELDRITCH = "eldritch"
    PSEUDO = "pseudo"
    META = "meta"


class UpdateMode(str, Enum):
    """Supported generated-data rebuild modes."""

    BASES = "bases"
    MODS = "mods"
    ALL = "all"


class StashTabType(str, Enum):
    """Known stash-tab type names returned by the official API."""

    NORMAL = "NormalStash"
    PREMIUM = "PremiumStash"
    QUAD = "QuadStash"
    CURRENCY = "CurrencyStash"
    FRAGMENT = "FragmentStash"
    MAP = "MapStash"
    GEM = "GemStash"
    DIVINATION_CARD = "DivinationCardStash"
    UNIQUE = "UniqueStash"
    ESSENCE = "EssenceStash"
    DELIRIUM = "DeliriumStash"
    BLIGHT = "BlightStash"
    METAMORPH = "MetamorphStash"
    EXPEDITION = "ExpeditionStash"
    HARVEST = "HarvestStash"
    FLASK = "FlaskStash"
    DELVE = "DelveStash"
    FOLIO = "FolioStash"
