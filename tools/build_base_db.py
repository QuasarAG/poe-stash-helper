#!/usr/bin/env python3
"""
tools/build_base_db.py  --  Rebuild data/base_types.json from RePoE.

USAGE
-----
    python tools/build_base_db.py                   # full rebuild
    python tools/build_base_db.py --force-fetch     # bypass 24-h cache
    python tools/build_base_db.py --dry-run         # parse only, no write

DATA SOURCE
-----------
    https://repoe-fork.github.io/base_items.min.json

ROBUSTNESS NOTES
----------------
RePoE periodically renames item_class strings and changes tag lists.
This script uses NAME-BASED detection for categories that are fragile:

  Shields  -- subtype from base name ("Kite Shield", "Round Shield", etc.)
              NOT from tags (str_armour / dex_armour etc. change without notice)

  Flasks   -- item_class may be "Flask", "Life Flask", "Mana Flask", etc.
              Subtype always derived from base name to cover both old and new schemas.

  Jewels   -- RePoE merged Small/Medium/Large Cluster Jewel and Abyss Jewel
              into item_class "Jewel".  Subtype derived from base name.

  Quivers  -- all DEX, no attribute subtype needed.
              Stored as a flat list (not nested by subtype).

OUTPUT SCHEMA  data/base_types.json
------------------------------------
    {
      "ARMOUR": {
        "Helmet":      [{"name":"Iron Hat","stats":"STR","req_ilvl":1}, ...],
        "Body Armour": [...], "Gloves": [...], "Boots": [...]
      },
      "ACCESSORIES": {
        "Ring":        [{"name":"Coral Ring","req_ilvl":1}, ...],
        "Amulet":      [...], "Belt": [...], "Tincture": [...],
        "Jewel":       [...], "Abyss Jewel": [...], "Cluster Jewel": [...],
        "Flask": {
          "Life Flask":   [...], "Mana Flask":  [...],
          "Hybrid Flask": [...], "Utility Flask": [...]
        }
      },
      "WEAPONS": {
        "1H Melee":        {"Claws":[...], ...},
        "2H Melee":        {"Two Hand Swords":[...], ...},
        "Caster & Ranged": {"Wands":[...], ...}
      },
      "OFF_HAND": {
        "Shields": {
          "Tower Shield (STR)":        [...],
          "Buckler (DEX)":             [...],
          "Spirit Shield (INT)":       [...],
          "Round Shield (STR/DEX)":    [...],
          "Kite Shield (STR/INT)":     [...],
          "Spiked Shield (DEX/INT)":   [...]
        },
        "Quivers": [...]     <- flat list, no subtype nesting
      },
      "META": { ... }
    }
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.common.http_cache import clear_cache_files, fetch_json_cached

OUT_PATH  = ROOT / "data" / "base_types.json"
CACHE_DIR = ROOT / ".cache" / "repoe"

REPOE_URL   = "https://repoe-fork.github.io/base_items.min.json"
CACHE_TTL_H = 24

# ── item_class → (section, slot [, subtype]) ──────────────────────────────
# "_by_name" as subtype = detect from item base name (robust against RePoE renames).
_CLASS_TO_DEST: dict[str, tuple] = {
    # Armour
    "Helmet":                   ("ARMOUR",      "Helmet"),
    "Body Armour":              ("ARMOUR",      "Body Armour"),
    "Gloves":                   ("ARMOUR",      "Gloves"),
    "Boots":                    ("ARMOUR",      "Boots"),
    # Accessories (no stat filter)
    "Ring":                     ("ACCESSORIES", "Ring"),
    "Amulet":                   ("ACCESSORIES", "Amulet"),
    "Belt":                     ("ACCESSORIES", "Belt"),
    # Flasks -- RePoE uses BOTH "Life Flask" (spaced) and "LifeFlask" (camelCase)
    # depending on export version. Map both to be future-proof.
    "Flask":                    ("ACCESSORIES", "Flask", "_by_name"),
    "Life Flask":               ("ACCESSORIES", "Flask", "Life Flask"),
    "Mana Flask":               ("ACCESSORIES", "Flask", "Mana Flask"),
    "Hybrid Flask":             ("ACCESSORIES", "Flask", "Hybrid Flask"),
    "Utility Flask":            ("ACCESSORIES", "Flask", "Utility Flask"),
    "Critical Utility Flask":   ("ACCESSORIES", "Flask", "Utility Flask"),
    # CamelCase variants (current RePoE schema as of 2025)
    "LifeFlask":                ("ACCESSORIES", "Flask", "Life Flask"),
    "ManaFlask":                ("ACCESSORIES", "Flask", "Mana Flask"),
    "HybridFlask":              ("ACCESSORIES", "Flask", "Hybrid Flask"),
    "UtilityFlask":             ("ACCESSORIES", "Flask", "Utility Flask"),
    # Other accessories
    "Tincture":                 ("ACCESSORIES", "Tincture"),
    # Jewels -- "Jewel" catches merged class; specific names for legacy RePoE
    # Subtype always resolved by name (_jewel_subtype) to handle both schemas.
    "Jewel":                    ("ACCESSORIES", "Jewel", "_by_name"),
    "Abyss Jewel":              ("ACCESSORIES", "Jewel", "_by_name"),
    "AbyssJewel":               ("ACCESSORIES", "Jewel", "_by_name"),   # CamelCase variant
    "Small Cluster Jewel":      ("ACCESSORIES", "Jewel", "_by_name"),
    "Medium Cluster Jewel":     ("ACCESSORIES", "Jewel", "_by_name"),
    "Large Cluster Jewel":      ("ACCESSORIES", "Jewel", "_by_name"),
    # Weapons (1H melee)
    "One Hand Sword":           ("WEAPONS", "1H Melee",        "One Hand Swords"),
    "Thrusting One Hand Sword": ("WEAPONS", "1H Melee",        "Thrusting One Hand Swords"),
    "One Hand Axe":             ("WEAPONS", "1H Melee",        "One Hand Axes"),
    "One Hand Mace":            ("WEAPONS", "1H Melee",        "One Hand Maces"),
    "Claw":                     ("WEAPONS", "1H Melee",        "Claws"),
    "Dagger":                   ("WEAPONS", "1H Melee",        "Daggers"),
    # Weapons (2H melee)
    "Two Hand Sword":           ("WEAPONS", "2H Melee",        "Two Hand Swords"),
    "Two Hand Axe":             ("WEAPONS", "2H Melee",        "Two Hand Axes"),
    "Two Hand Mace":            ("WEAPONS", "2H Melee",        "Two Hand Maces"),
    "Warstaff":                 ("WEAPONS", "2H Melee",        "Warstaves"),
    # Weapons (caster / ranged)
    "Wand":                     ("WEAPONS", "Caster & Ranged", "Wands"),
    "Sceptre":                  ("WEAPONS", "Caster & Ranged", "Sceptres"),
    "Rune Dagger":              ("WEAPONS", "Caster & Ranged", "Rune Daggers"),
    "Staff":                    ("WEAPONS", "Caster & Ranged", "Staves"),
    "Bow":                      ("WEAPONS", "Caster & Ranged", "Bows"),
    # Off-hand -- shield subtype always resolved by name (_shield_subtype)
    "Shield":                   ("OFF_HAND", "Shields"),
    # Quivers -- stored as flat list, no subtype nesting
    "Quiver":                   ("OFF_HAND", "Quivers"),
}

_STAT_ATTRIBUTES = {
    "STR":         "Strength",
    "DEX":         "Dexterity",
    "INT":         "Intelligence",
    "STR/DEX":     "Strength/Dexterity",
    "STR/INT":     "Strength/Intelligence",
    "DEX/INT":     "Dexterity/Intelligence",
    "STR/DEX/INT": "All Attributes",
    "WARD":        "Ward",
    "NONE":        "No Requirements",
}


# ── Name-based subtype detectors ───────────────────────────────────────────

def _shield_subtype(name: str) -> str:
    """Determine shield category from base name.
    Name-based detection is robust against RePoE tag renames.
    Check longer / more-specific strings first to avoid false matches.
    """
    n = name.lower()
    if "kite shield"   in n:                          return "Kite Shield (STR/INT)"
    if "round shield"  in n:                          return "Round Shield (STR/DEX)"
    if "spiked shield" in n or "spiked bundle" in n:  return "Spiked Shield (DEX/INT)"
    if "tower shield"  in n:                          return "Tower Shield (STR)"
    if "buckler"       in n:                          return "Buckler (DEX)"
    if "spirit shield" in n:                          return "Spirit Shield (INT)"
    return "Spirit Shield (INT)"   # safe fallback


def _flask_subtype(name: str) -> str:
    """Determine flask category from base name."""
    n = name.lower()
    if "life flask"   in n: return "Life Flask"
    if "mana flask"   in n: return "Mana Flask"
    if "hybrid flask" in n: return "Hybrid Flask"
    return "Utility Flask"   # Silver, Quicksilver, Diamond, Jade, Basalt, etc.


def _jewel_subtype(name: str, item_class: str) -> str:
    """Determine Jewel / Abyss Jewel / Cluster Jewel from base name + item_class.

    In newer RePoE all jewel types share item_class "Jewel".
    Specific item_class strings (legacy and CamelCase) are checked first,
    then name-based detection for the merged schema.

    Abyss Jewel base names: "Searching Eye Jewel", "Hypnotic Eye Jewel",
    "Ghastly Eye Jewel", "Murderous Eye Jewel", "Violent Eye Jewel",
    "Stalwart Eye Jewel", "Resolute Eye Jewel", "Timeless Eye Jewel".
    They all end in "Eye Jewel".
    """
    # Item_class takes priority (both spaced and CamelCase)
    if item_class in ("Abyss Jewel", "AbyssJewel"):     return "Abyss Jewel"
    if "Cluster Jewel" in item_class:                   return "Cluster Jewel"
    # Name-based (merged "Jewel" schema in current RePoE)
    if "Cluster Jewel" in name:                         return "Cluster Jewel"
    if name.endswith("Eye Jewel"):                      return "Abyss Jewel"
    return "Jewel"


# ── HTTP fetch with disk cache ─────────────────────────────────────────────

def _fetch(url: str, cache_name: str) -> dict:
    return fetch_json_cached(
        url=url,
        cache_dir=CACHE_DIR,
        cache_name=cache_name,
        cache_ttl_hours=CACHE_TTL_H,
        user_agent="poe-stash-helper/base-db",
    )


# The raw RePoE entry stores requirement numbers separately (strength / dexterity / intelligence).
# The rest of the application does not want to care about those three separate fields every time it
# needs to group or filter a base item. We therefore convert them here into one small label:
#
#     STR
#     DEX
#     INT
#     STR/DEX
#     STR/INT
#     DEX/INT
#     STR/DEX/INT
#     WARD
#     NONE
#
# This helper existed in the original project, but it was accidentally lost during the refactor when
# I was moving repeated fetch / cache code around. The build loop still called it, so the rebuild
# crashed with: NameError: _req_to_stats is not defined.
#
# Keeping this as a dedicated helper is good practice because:
# - the build loop stays readable
# - the conversion rule has a single home
# - future schema changes can be handled in one place
def _req_to_stats(reqs: dict, tags: list) -> str:
    strength = reqs.get("strength", 0) or 0
    dexterity = reqs.get("dexterity", 0) or 0
    intelligence = reqs.get("intelligence", 0) or 0

    parts = []
    if strength:
        parts.append("STR")
    if dexterity:
        parts.append("DEX")
    if intelligence:
        parts.append("INT")

    if parts:
        return "/".join(parts)

    # Ward bases often do not use the normal attribute requirements, so we preserve that information
    # through the existing tag-based fallback used by the project before the refactor.
    if tags and any("ward" in tag for tag in tags):
        return "WARD"

    return "NONE"


def _sort(lst: list) -> list:
    return sorted(lst, key=lambda b: (b.get("req_ilvl", 0), b["name"]))


def _dedup(lst: list) -> list:
    seen: set[str] = set()
    out  = []
    for b in lst:
        if b["name"] not in seen:
            seen.add(b["name"])
            out.append(b)
    return out


# ── Core builder ───────────────────────────────────────────────────────────

def build(raw: dict) -> dict:
    # Armour
    armour: dict[str, list] = {s: [] for s in ("Helmet", "Body Armour", "Gloves", "Boots")}
    # Accessories (flat lists)
    accessories: dict[str, list] = {s: [] for s in ("Ring", "Amulet", "Belt", "Tincture")}
    # Jewels (split by subtype, all detected by name)
    jewel_buckets: dict[str, list] = {"Jewel": [], "Abyss Jewel": [], "Cluster Jewel": []}
    # Flasks (split by subtype, detected by name)
    flask_buckets: dict[str, list] = defaultdict(list)
    # Weapons (nested: group -> wtype -> bases)
    weapons: dict[str, dict[str, list]] = {
        "1H Melee":        defaultdict(list),
        "2H Melee":        defaultdict(list),
        "Caster & Ranged": defaultdict(list),
    }
    # Shields (split by subtype, detected by name)
    shields: dict[str, list] = defaultdict(list)
    # Quivers (flat list -- all DEX, no subtype needed)
    quivers: list = []

    placed        = 0
    skipped       = 0
    class_counts:        dict[str, int] = {}
    unrecognized_counts: dict[str, int] = {}   # item_class names not in _CLASS_TO_DEST

    for _internal_id, entry in raw.items():
        # Skip items GGG has not released yet (placeholder / future content).
        # Accept "released", "legacy", "drop_disabled" and any other state —
        # only "unreleased" means the item literally doesn't exist in-game.
        if entry.get("release_state") == "unreleased":
            skipped += 1
            continue

        item_class = entry.get("item_class", "")
        name       = entry.get("name", "")
        if not name or not item_class:
            skipped += 1
            continue

        dest = _CLASS_TO_DEST.get(item_class)
        if dest is None:
            skipped += 1
            unrecognized_counts[item_class] = unrecognized_counts.get(item_class, 0) + 1
            continue

        reqs  = entry.get("requirements", {}) or {}
        tags  = entry.get("tags", [])         or []
        ilvl  = entry.get("drop_level", 0)    or 0
        stats = _req_to_stats(reqs, tags)

        section = dest[0]

        # ── Armour ────────────────────────────────────────────────────────
        if section == "ARMOUR":
            armour[dest[1]].append({"name": name, "stats": stats, "req_ilvl": ilvl})

        # ── Accessories ───────────────────────────────────────────────────
        elif section == "ACCESSORIES":
            slot = dest[1]

            if slot == "Flask":
                flask_type = dest[2] if dest[2] != "_by_name" else _flask_subtype(name)
                flask_buckets[flask_type].append({"name": name, "req_ilvl": ilvl})

            elif slot == "Jewel":
                jewel_type = _jewel_subtype(name, item_class)
                jewel_buckets[jewel_type].append({"name": name, "req_ilvl": ilvl})

            else:  # Ring, Amulet, Belt, Tincture
                accessories[slot].append({"name": name, "req_ilvl": ilvl})

        # ── Weapons ───────────────────────────────────────────────────────
        elif section == "WEAPONS":
            weapons[dest[1]][dest[2]].append({"name": name, "stats": stats, "req_ilvl": ilvl})

        # ── Off-hand ──────────────────────────────────────────────────────
        elif section == "OFF_HAND":
            if dest[1] == "Shields":
                shields[_shield_subtype(name)].append({"name": name, "stats": stats, "req_ilvl": ilvl})
            else:  # Quivers -- flat list
                quivers.append({"name": name, "req_ilvl": ilvl})

        placed += 1
        class_counts[item_class] = class_counts.get(item_class, 0) + 1

    # ── Sort + dedup all collections ──────────────────────────────────────
    for slot in armour:
        armour[slot] = _sort(_dedup(armour[slot]))
    for slot in accessories:
        accessories[slot] = _sort(_dedup(accessories[slot]))
    for jtype in jewel_buckets:
        jewel_buckets[jtype] = _sort(_dedup(jewel_buckets[jtype]))
    flask_out: dict[str, list] = {k: _sort(_dedup(v)) for k, v in flask_buckets.items() if v}
    weapons_out = {grp: {wt: _sort(_dedup(v)) for wt, v in wtypes.items()}
                   for grp, wtypes in weapons.items()}
    shields_out = {sub: _sort(_dedup(v)) for sub, v in shields.items()}
    quivers_out = _sort(_dedup(quivers))

    # ── Derive META ───────────────────────────────────────────────────────
    slot_attributes: dict[str, list[str]] = {}
    for slot in ("Helmet", "Body Armour", "Gloves", "Boots"):
        seen: list[str] = []
        for b in armour[slot]:
            c = b["stats"]
            if c not in seen:
                seen.append(c)
        slot_attributes[slot] = seen

    shield_attributes: list[str] = []
    for bases in shields_out.values():
        for b in bases:
            c = b.get("stats", "NONE")
            if c not in shield_attributes:
                shield_attributes.append(c)
    slot_attributes["Off-hand"] = shield_attributes

    # ── Print diagnostics ─────────────────────────────────────────────────
    print(f"  Placed: {placed:,}  |  Skipped (non-equipment / unreleased): {skipped:,}")
    print("  Per item class:")
    for cls, cnt in sorted(class_counts.items()):
        print(f"    {cls:32}: {cnt:4}")
    print()
    for chk in ("Helmet", "Body Armour", "Gloves", "Boots"):
        n = len(armour[chk])
        mark = "OK" if n else "WARNING -- 0 bases, item_class may have changed in RePoE"
        print(f"  {chk:12}: {n:3}  [{mark}]")
    print()
    print("  Shields:")
    for sub, bases in shields_out.items():
        print(f"    {sub:30}: {len(bases):3}")
    print()
    print("  Jewels:")
    for jtype, bases in jewel_buckets.items():
        mark = "" if jewel_buckets[jtype] else "  <-- WARNING: empty"
        print(f"    {jtype:20}: {len(jewel_buckets[jtype]):3}{mark}")
    print()
    print("  Flasks:")
    if flask_out:
        for ftype, bases in flask_out.items():
            print(f"    {ftype:20}: {len(bases):3}")
    else:
        print("    WARNING: no flasks found -- item_class names may have changed in RePoE")
    print(f"  Quivers (flat):      {len(quivers_out):3}")

    # ── Unrecognized item_class report (helps catch RePoE renames) ─────────
    if unrecognized_counts:
        top = sorted(unrecognized_counts.items(), key=lambda x: -x[1])[:30]
        print(f"\n  UNRECOGNIZED item_class ({len(unrecognized_counts)} distinct, top 30 by count):")
        print("  (Paste this list if flasks / jewels / other slots are missing)")
        for cls, cnt in top:
            print(f"    {cls:40}: {cnt:4}")

    return {
        "ARMOUR": dict(armour),
        "ACCESSORIES": {
            **accessories,
            "Jewel":         jewel_buckets["Jewel"],
            "Abyss Jewel":   jewel_buckets["Abyss Jewel"],
            "Cluster Jewel": jewel_buckets["Cluster Jewel"],
            "Flask":         flask_out,
        },
        "WEAPONS": weapons_out,
        "OFF_HAND": {
            "Shields": shields_out,
            "Quivers": quivers_out,   # flat list
        },
        "META": {
            "STAT_ATTRIBUTES":       _STAT_ATTRIBUTES,
            "SLOT_ATTRIBUTES":       slot_attributes,
            # Quiver is a flat/no-attribute slot (all DEX, no attribute subtype)
            "SLOTS_NO_ATTRIBUTE":    ["Ring", "Amulet", "Belt", "Flask", "Tincture",
                                  "Jewel", "Abyss Jewel", "Cluster Jewel", "Quiver"],
            "SLOTS_WEAPON_TYPE": ["Main Hand", "Off-hand"],
        },
    }


# ── Stats reporter ─────────────────────────────────────────────────────────

def _report(data: dict) -> None:
    def _count(obj) -> int:
        if isinstance(obj, list): return len(obj)
        if isinstance(obj, dict): return sum(_count(v) for v in obj.values())
        return 0

    print("\n  Section totals:")
    total = 0
    for sec in ("ARMOUR", "ACCESSORIES", "WEAPONS", "OFF_HAND"):
        n = _count(data.get(sec, {}))
        total += n
        print(f"    {sec:12}: {n:4}")
    print(f"    {'TOTAL':12}: {total:4}")


# ── Entry point ────────────────────────────────────────────────────────────

def run_build(*, dry_run: bool = False, force_fetch: bool = False) -> dict:
    if force_fetch:
        clear_cache_files(CACHE_DIR, "base_items*.json")
        print("Cache cleared.")

    print("=== build_base_db.py ===")
    print(f"Output : {OUT_PATH}")
    print(f"Source : {REPOE_URL}\n")

    print("Fetching ...")
    raw = _fetch(REPOE_URL, "base_items")
    print(f"  RePoE total entries: {len(raw):,}\n")

    print("Building ...")
    data = build(raw)
    _report(data)

    result = {
        "ok": True,
        "dry_run": dry_run,
        "output_path": str(OUT_PATH),
        "entries": len(raw),
    }

    if dry_run:
        print("\n[DRY RUN] No file written.")
        result["written"] = False
        return result

    print(f"\nWriting {OUT_PATH} ...")
    OUT_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    kb = OUT_PATH.stat().st_size // 1024
    print(f"Done -- base_types.json: {kb} KB")
    result.update({"written": True, "size_kb": kb})
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild data/base_types.json from RePoE")
    parser.add_argument("--dry-run", action="store_true", help="Parse but do not write")
    parser.add_argument("--force-fetch", action="store_true", help="Bypass disk cache")
    args = parser.parse_args()
    run_build(dry_run=args.dry_run, force_fetch=args.force_fetch)


if __name__ == "__main__":
    main()
