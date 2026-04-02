"""Shared fixed values for the overlay settings tab."""

from __future__ import annotations

from models import OutlineColorRole

OUTLINE_COLOR_ROWS = [
    ("Colour - Item matches Base/Properties only:", OutlineColorRole.SLOT_ONLY, "#ffffff"),
    ("Colour - Item matches EVERYTHING:", OutlineColorRole.ALL_GOLD, "#ffd700"),
    ("Colour - All mods matched:", OutlineColorRole.ALL, "#00ff44"),
    ("Colour - Missing 1 mod:", OutlineColorRole.MINUS1, "#ff8800"),
    ("Colour - Missing 2+ mods:", OutlineColorRole.MINUS2, "#ff2222"),
]

FONT_SLIDER_ROWS = [
    ("General text (base for all):", "general", 0, -5, 10),
    ("Headers / Tab titles / Panel headers:", "header", 10, 7, 20),
    ("Buttons (all clickable selectors):", "button", 10, 7, 20),
    ("Item Properties labels / checkboxes:", "props", 10, 7, 20),
    ("Mod Stats text (search + filter cols):", "mods", 10, 7, 20),
]
