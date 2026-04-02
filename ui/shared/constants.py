"""
Shared user-interface constants.

This file intentionally contains only plain data. There is no widget code here.
That makes it a good place for values that many tabs or widgets need to share,
for example league names, item-slot order, and stash-tab labels.
"""

from __future__ import annotations

from models import StashTabType

LEAGUES = [
    "Mirage",
    "Hardcore Mirage",
    "Solo Self-Found Mirage",
    "Hardcore Solo Self-Found Mirage",
    "Standard",
    "Hardcore",
    "Solo Self-Found",
    "Hardcore Solo Self-Found",
]

ITEM_SLOTS = [
    "Any",
    "Helmet",
    "Body Armour",
    "Gloves",
    "Boots",
    "Belt",
    "Amulet",
    "Ring",
    "Main Hand",
    "Off-hand",
    "Jewel",
    "Abyss Jewel",
    "Cluster Jewel",
    "Flask",
    "Tincture",
]

TAB_TYPE_BADGE: dict[StashTabType | str, str] = {
    StashTabType.NORMAL: "",
    StashTabType.PREMIUM: "",
    StashTabType.QUAD: " [Quad]",
    StashTabType.CURRENCY: " [Currency]",
    StashTabType.FRAGMENT: " [Fragment]",
    StashTabType.MAP: " [Map]",
    StashTabType.GEM: " [Gem]",
    StashTabType.DIVINATION_CARD: " [Div Card]",
    StashTabType.UNIQUE: " [Unique]",
    StashTabType.ESSENCE: " [Essence]",
    StashTabType.DELIRIUM: " [Delirium]",
    StashTabType.BLIGHT: " [Blight]",
    StashTabType.METAMORPH: " [Metamorph]",
    StashTabType.EXPEDITION: " [Expedition]",
    StashTabType.HARVEST: " [Harvest]",
    StashTabType.FLASK: " [Flask]",
    StashTabType.DELVE: " [Delve]",
    StashTabType.FOLIO: " [Folio]",
}

NON_EQUIPMENT_TAB_TYPES: set[StashTabType] = {
    StashTabType.CURRENCY,
    StashTabType.FRAGMENT,
    StashTabType.MAP,
    StashTabType.GEM,
    StashTabType.DIVINATION_CARD,
    StashTabType.ESSENCE,
    StashTabType.DELIRIUM,
    StashTabType.BLIGHT,
    StashTabType.METAMORPH,
    StashTabType.EXPEDITION,
    StashTabType.HARVEST,
    StashTabType.DELVE,
    StashTabType.FOLIO,
}
