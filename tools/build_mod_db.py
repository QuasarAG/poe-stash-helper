#!/usr/bin/env python3
"""
tools/build_mod_db.py  —  Rebuild data/mod_data.py from PoB data export.

DATA SOURCE
-----------
repoe-fork.github.io/pob-data/poe1/Mod*.min.json

PoB pre-separates mods into distinct files by domain — no monster mods,
no map mods, no manual domain filtering required:
  ModItem.min.json         equippable items  (slots from weightKey/weightVal)
  ModJewel.min.json        regular jewels
  ModJewelAbyss.min.json   abyss jewels
  ModJewelCluster.min.json cluster jewels
  ModFlask.min.json        flasks
  ModTincture.min.json     tinctures

POB ENTRY FORMAT
----------------
Each key is a unique mod ID. Every entry has:
  "type"      "Prefix" | "Suffix" | "Exarch" | "Eater" | "Corrupted" | ...
  "group"     mod family name (same for all tiers of the same mod)
  "affix"     display name suffix/prefix ("Icy", "of the Shaper", ...)
  "level"     item-level requirement
  "weightKey" list of tags     ["ring","amulet","gloves","default"]
  "weightVal" parallel weights [500, 500, 500, 0]
  "1"         first mod line   "Adds (5-7) to (10-12) Cold Damage to Attacks"
  "2"         optional second line

DESIGN
------
Group key = (group, affix_type, influence)
  → ONE DB entry per logical mod family. No search-panel duplication.

slot_tiers = { slot_name: [(lo, hi), ...] }  T1-first
  → Built by iterating each mod in the family and contributing its (lo,hi)
    only to the slots that mod can actually spawn on (weightVal > 0).
  → Each slot gets only the tiers that genuinely exist for that slot.
    Gloves may have 4 tiers of ColdDamage while Ring has 9 — both correct.

Essence-only / zero-weight mods are silently skipped (no slots derived → excluded).
"""

from __future__ import annotations
import json, re, argparse, pathlib, sys, time
from collections import defaultdict
from typing import Optional

ROOT = pathlib.Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.common.http_cache import clear_cache_files, fetch_json_cached

OUT_PATH   = ROOT / "data" / "mod_data.py"
CACHE_DIR  = ROOT / ".cache" / "pob"
POB_BASE   = "https://repoe-fork.github.io/pob-data/poe1"
CACHE_TTL_H = 24

# Files to load and their fixed slot (None = derive from weightKey)
_FILES: list[tuple[str, Optional[list[str]]]] = [
    ("ModItem",          None),
    ("ModJewel",         ["Jewel"]),
    ("ModJewelAbyss",    ["Abyss Jewel"]),
    ("ModJewelCluster",  ["Cluster Jewel"]),
    ("ModFlask",         ["Flask"]),
    ("ModTincture",      ["Tincture"]),
]

# Only these PoB types are shown in the filter tool
_TYPE_MAP: dict[str, str] = {
    "Prefix": "prefix",
    "Suffix": "suffix",
    "Exarch": "implicit",   # Searing Exarch implicit
    "Eater":  "implicit",   # Eater of Worlds implicit
}

# Influence suffix on weightKey tags (confirmed from real RePoE inspect)
_INFLUENCE: dict[str, str] = {
    "_shaper":      "Shaper",
    "_elder":       "Elder",
    "_crusader":    "Crusader",
    "_eyrie":       "Redeemer",
    "_adjudicator": "Warlord",
    "_basilisk":    "Hunter",
}
_INF_SUFFIXES = list(_INFLUENCE)

_ALL_ARMOUR = ["Helmet", "Body Armour", "Gloves", "Boots"]

# weightKey tag → UI slot name(s).  Confirmed from real inspect_cache output.
# Tags NOT in this dict are non-slot (no_attack_mods, grants_2h_support, etc.)
_TAG_SLOTS: dict[str, list[str]] = {
    "helmet":               ["Helmet"],
    "chest":                ["Body Armour"],
    "body_armour":          ["Body Armour"],
    "gloves":               ["Gloves"],
    "boots":                ["Boots"],
    "armour":               _ALL_ARMOUR,    # confirmed: FireResistance, StunRecovery
    "str_armour":           _ALL_ARMOUR,
    "dex_armour":           _ALL_ARMOUR,
    "int_armour":           _ALL_ARMOUR,
    "str_dex_armour":       _ALL_ARMOUR,
    "str_int_armour":       _ALL_ARMOUR,
    "dex_int_armour":       _ALL_ARMOUR,
    "str_dex_int_armour":   _ALL_ARMOUR,
    "ward_armour":          _ALL_ARMOUR,
    "necropolis_helmet":       ["Helmet"],
    "necropolis_body_armour":  ["Body Armour"],
    "necropolis_gloves":       ["Gloves"],
    "necropolis_boots":        ["Boots"],
    "ring":                 ["Ring"],
    "amulet":               ["Amulet"],
    "belt":                 ["Belt"],
    "sword":                ["Main Hand"],
    "axe":                  ["Main Hand"],
    "mace":                 ["Main Hand"],
    "claw":                 ["Main Hand"],
    "dagger":               ["Main Hand"],
    "wand":                 ["Main Hand"],
    "sceptre":              ["Main Hand"],
    "bow":                  ["Main Hand"],
    "staff":                ["Main Hand"],
    "2h_sword":             ["Main Hand"],
    "2h_axe":               ["Main Hand"],
    "2h_mace":              ["Main Hand"],
    "warstaff":             ["Main Hand"],
    "rune_dagger":          ["Main Hand"],
    "rapier":               ["Main Hand"],
    "one_hand_weapon":      ["Main Hand"],
    "two_hand_weapon":      ["Main Hand"],
    "weapon":               ["Main Hand"],
    "attack_dagger":        ["Main Hand"],
    "attack_staff":         ["Main Hand"],
    "ranged":               ["Main Hand", "Quiver"],
    "shield":               ["Off-hand"],
    "focus":                ["Off-hand"],
    "str_shield":           ["Off-hand"],
    "dex_shield":           ["Off-hand"],
    "int_shield":           ["Off-hand"],
    "str_dex_shield":       ["Off-hand"],
    "str_int_shield":       ["Off-hand"],
    "dex_int_shield":       ["Off-hand"],
    "quiver":               ["Quiver"],
    "weapon_can_roll_minion_modifiers": ["Main Hand"],
    "focus_can_roll_minion_modifiers":  ["Off-hand"],
    "ring_can_roll_minion_modifiers":   ["Ring"],
}


def _tag_base(tag: str) -> str:
    """Strip influence suffix from a raw weightKey tag."""
    for suf in _INF_SUFFIXES:
        if tag.endswith(suf):
            return tag[:-len(suf)]
    return tag


# Broad item slots: what "default:positive, no specific positive tags" expands to.
# Confirmed from real RePoE data: Life/Resist mods have weapon:0, fishing_rod:0,
# default:1000 — they spawn on all armour, jewellery, and off-hand, but NOT weapons.
_ITEM_BROAD_SLOTS = [
    "Helmet", "Body Armour", "Gloves", "Boots",
    "Ring", "Amulet", "Belt",
    "Off-hand", "Quiver",
]
# Fixed-slot files (jewel/flask/tincture) never need broad expansion; they have
# their slots set directly in _FILES.

def _slots_from_weights(wk: list[str], wv: list[int]) -> list[str]:
    """
    Derive slot list from PoB weightKey/weightVal arrays.

    Three cases:
      A) Positive non-default tags exist -> use those slots only
      B) No positive non-default tags AND default > 0 -> BROAD mod:
         expand to _ITEM_BROAD_SLOTS minus any explicitly blocked slots
         (e.g. weapon:0, fishing_rod:0 with default:1000)
      C) No positive non-default tags AND default = 0 -> essence-only: return []
    """
    pos: set[str] = set()
    blocked: set[str] = set()
    default_w = 0

    for tag, val in zip(wk, wv):
        if tag == "default":
            default_w = val
            continue
        base = _tag_base(tag)
        tag_slots = _TAG_SLOTS.get(base, [])
        if val > 0:
            pos.update(tag_slots)
        elif val == 0 and tag_slots:
            blocked.update(tag_slots)

    if pos:
        # Case A: explicit positive slots
        return sorted(pos)
    if default_w > 0:
        # Case B: broad mod — expand to all item slots, subtract explicit blocks
        broad = set(_ITEM_BROAD_SLOTS) - blocked
        return sorted(broad)
    # Case C: essence-only or zero weight — skip
    return []


def _detect_influence(wk: list[str], wv: list[int]) -> Optional[str]:
    """
    Return influence name if ALL positive non-default tags belong to exactly one
    influence. Mods with mixed plain+influence tags return None.
    """
    found: set[str] = set()
    has_plain = False
    for tag, val in zip(wk, wv):
        if tag == "default" or val == 0:
            continue
        inf = next((name for suf, name in _INFLUENCE.items()
                    if tag.endswith(suf)), None)
        if inf:
            found.add(inf)
        else:
            has_plain = True
    return next(iter(found)) if (not has_plain and len(found) == 1) else None


def _normalize_label(text: str) -> str:
    """Replace (min-max) ranges with # for a clean display label."""
    return re.sub(r'\([^)]+\)', '#', text).strip()


def _extract_lo_hi(text: str) -> tuple[float, float]:
    """
    Extract (lo, hi) from PoB mod text — numbers read left-to-right.
    Handles: (5-7), (10-12), (-35--25), "1 to 2", "Adds 1 to (2-3)".
    lo = first value encountered, hi = last value encountered.
    """
    all_nums: list[float] = []
    for m in re.finditer(r'\(([^)]+)\)|\b(\d+(?:\.\d+)?)\b', text):
        if m.group(1) is not None:  # parenthesised group
            rng = re.match(
                r'\s*(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)\s*$',
                m.group(1)
            )
            if rng:
                all_nums.append(float(rng.group(1)))
                all_nums.append(float(rng.group(2)))
            else:
                try:
                    all_nums.append(float(m.group(1).strip()))
                except ValueError:
                    pass
        else:  # standalone number outside parens
            all_nums.append(float(m.group(2)))
    if not all_nums:
        return (0.0, 0.0)
    return (all_nums[0], all_nums[-1])


def _value_type(label: str) -> str:
    return "percent" if "%" in label else "flat"


def _fetch(url: str, name: str) -> dict:
    return fetch_json_cached(
        url=url,
        cache_dir=CACHE_DIR,
        cache_name=name,
        cache_ttl_hours=CACHE_TTL_H,
        user_agent="poe-stash-helper/mod-db",
    )


# ── Core build ──────────────────────────────────────────────────────────────

def build_mod_db() -> dict[str, dict]:
    # Step 1: load all PoB files, convert each mod to a flat record
    raw: list[dict] = []
    for file_name, fixed_slots in _FILES:
        url  = f"{POB_BASE}/{file_name}.min.json"
        data = _fetch(url, file_name)
        print(f"  {file_name}: {len(data)} entries")
        for mod_id, e in data.items():
            pob_type = e.get("type", "")
            if pob_type not in _TYPE_MAP:
                continue
            affix = _TYPE_MAP[pob_type]
            group = e.get("group", "")
            wk    = e.get("weightKey", [])
            wv    = e.get("weightVal", [])

            if fixed_slots is not None:
                slots     = list(fixed_slots)
                influence = None
            else:
                slots = _slots_from_weights(wk, wv)
                if not slots:
                    continue   # essence-only / zero-weight: skip
                influence = (
                    pob_type          # "Exarch" or "Eater" — from type directly
                    if pob_type in ("Exarch", "Eater")
                    else _detect_influence(wk, wv)
                )

            # Collect text lines "1", "2", ...
            lines = []
            for i in range(1, 10):
                t = e.get(str(i))
                if t is None: break
                lines.append(t)
            if not lines:
                continue

            lo, hi = _extract_lo_hi(lines[0])
            raw.append({
                "group": group, "affix": affix, "influence": influence,
                "level": e.get("level", 0),
                "slots": slots, "lo": lo, "hi": hi,
                "lines": lines,
            })

    print(f"\n  Raw mod records: {len(raw)}")

    # Step 2: group by (group, affix_type, influence) — ONE DB entry per family
    family: dict[tuple, list] = defaultdict(list)
    for rec in raw:
        family[(rec["group"], rec["affix"], rec["influence"])].append(rec)
    print(f"  Families: {len(family)}")

    # Step 3: build slot_tiers — per-slot sorted tier list
    stat_count: dict[str, int] = defaultdict(int)
    entries: list[tuple[str, dict]] = []

    for (group, affix, influence), recs in family.items():
        # Sort recs T1-first (highest hi = best)
        recs.sort(key=lambda r: r["hi"], reverse=True)

        # slot_tiers: only add (lo,hi) to the slots this specific mod can spawn on
        slot_tiers: dict[str, list] = defaultdict(list)
        for r in recs:
            t = (r["lo"], r["hi"])
            for slot in r["slots"]:
                if t not in slot_tiers[slot]:
                    slot_tiers[slot].append(t)
        # Each slot's list is already in T1-first order (recs sorted by hi)

        if not slot_tiers:
            continue

        # Primary = slot with most tiers
        primary = max(slot_tiers, key=lambda s: len(slot_tiers[s]))
        tiers   = slot_tiers[primary]
        slots   = sorted(slot_tiers.keys())

        # Label from best-tier (T1) mod text, influence prefix stripped from label
        label_parts = [_normalize_label(l) for l in recs[0]["lines"]]
        label = " / ".join(dict.fromkeys(label_parts))  # deduplicate identical parts
        vtype = _value_type(label)

        base_key = f"mod.{group}.{affix}"
        if influence:
            base_key += f".{influence}"
        stat_count[base_key] += 1
        n = stat_count[base_key]
        entry_key = base_key if n == 1 else f"{base_key}#{n}"

        entries.append((entry_key, {
            "label":      label,
            "affix_type": affix,
            "slots":      slots,
            "slot_tiers": dict(slot_tiers),
            "type":       vtype,
            "tiers":      tiers,
            "group":      group,
            "stat_ids":   [],
            "influence":  influence,
            "source":     "pob",
        }))

    return dict(entries)


# ── Validation ──────────────────────────────────────────────────────────────

def _validate(db: dict[str, dict]):
    print("\n  === VALIDATION (expected counts) ===")
    checks = [
        ("ColdDamage",   "prefix", None,    "Ring",        "9"),
        ("ColdDamage",   "prefix", None,    "Gloves",      "4 (drops at T5+)"),
        ("ColdDamage",   "prefix", None,    "Helmet",      "0 (not in slots)"),
        ("FireResistance","suffix",None,    "Helmet",      "~8"),
        ("IncreasedLife","prefix", None,    "Body Armour", "many"),
        ("IncreasedLife","prefix", None,    "Main Hand",   "0"),
        ("IncreasedMana","prefix", None,    "Ring",        "~12"),
        ("IncreasedMana","prefix", None,    "Main Hand",   "12 (staff/caster)"),
        ("DefencesPercent","prefix",None,   "Boots",       "~6"),
    ]
    for grp, atype, infl, slot, note in checks:
        match = next(
            ((k,v) for k,v in db.items()
             if v["group"] == grp and v["affix_type"] == atype
             and v["influence"] == infl and slot in v["slots"]),
            None
        )
        if match:
            n = len(match[1]["slot_tiers"].get(slot, []))
            print(f"  {grp:22} {atype:6} on {slot:12}: {n:3} tiers  ({note})")
        else:
            n_any = sum(1 for v in db.values()
                       if v["group"]==grp and slot in v.get("slots",[]))
            print(f"  {grp:22} {atype:6} on {slot:12}:   0  ✓  ({note})"
                  if n_any == 0 else
                  f"  {grp:22} {atype:6} on {slot:12}:  ?  (found {n_any} entries but key mismatch)")


# ── Slot constant helpers ────────────────────────────────────────────────────

_SLOT_CONSTS: dict[frozenset, str] = {
    frozenset(["Helmet"]):                                   "_H",
    frozenset(["Body Armour"]):                              "_BA",
    frozenset(["Gloves"]):                                   "_GL",
    frozenset(["Boots"]):                                    "_BO",
    frozenset(["Belt"]):                                     "_BE",
    frozenset(["Amulet"]):                                   "_AM",
    frozenset(["Ring"]):                                     "_RI",
    frozenset(["Main Hand"]):                                "_MH",
    frozenset(["Off-hand"]):                                 "_OH",
    frozenset(["Quiver"]):                                   "_QU",
    frozenset(["Jewel"]):                                    "_JW",
    frozenset(["Abyss Jewel"]):                              "_AJ",
    frozenset(["Cluster Jewel"]):                            "_CJ",
    frozenset(["Flask"]):                                    "_FL",
    frozenset(["Tincture"]):                                 "_TI",
    frozenset(["Main Hand", "Off-hand"]):                    "_WP",
    frozenset(["Helmet","Body Armour","Gloves","Boots"]):    "_ARMOUR",
    frozenset(["Amulet","Ring"]):                            "_AM_RI",
    frozenset(["Amulet","Ring","Belt"]):                     "_AM_RI_BE",
    frozenset(["Jewel","Abyss Jewel","Cluster Jewel"]):      "_JEWELS",
}

def _slot_expr(slots: list[str]) -> str:
    fs = frozenset(slots)
    if fs in _SLOT_CONSTS: return _SLOT_CONSTS[fs]
    rem = set(slots); parts: list[str] = []
    for fs_c, name in sorted(_SLOT_CONSTS.items(), key=lambda x: -len(x[0])):
        if fs_c <= rem: parts.append(name); rem -= fs_c
    if not rem: return " + ".join(parts)
    return repr(sorted(slots))


# ── Writer ───────────────────────────────────────────────────────────────────

def write_mod_data(db: dict[str, dict], out_path: pathlib.Path) -> None:
    slot_order = ["Helmet","Body Armour","Gloves","Boots",
                  "Ring","Amulet","Belt","Main Hand","Off-hand","Quiver",
                  "Jewel","Abyss Jewel","Cluster Jewel","Flask","Tincture","MULTI"]
    section_labels = {
        "Helmet":"ARMOUR — Helmet","Body Armour":"ARMOUR — Body Armour",
        "Gloves":"ARMOUR — Gloves","Boots":"ARMOUR — Boots",
        "Ring":"JEWELLERY — Ring","Amulet":"JEWELLERY — Amulet",
        "Belt":"JEWELLERY — Belt","Main Hand":"WEAPONS — Main Hand",
        "Off-hand":"WEAPONS — Off-hand / Shield","Quiver":"WEAPONS — Quiver",
        "Jewel":"JEWELS — Regular Jewel","Abyss Jewel":"JEWELS — Abyss Jewel",
        "Cluster Jewel":"JEWELS — Cluster Jewel",
        "Flask":"FLASK","Tincture":"TINCTURE","MULTI":"MULTI-SLOT",
    }
    def _primary(e):
        for s in slot_order:
            if s in e["slots"]: return s
        return "MULTI"

    sorted_entries = sorted(db.items(), key=lambda x: (
        slot_order.index(_primary(x[1])) if _primary(x[1]) in slot_order else 999,
        x[1]["group"], x[1]["label"],
    ))
    header = f'''\
from __future__ import annotations
"""
data/mod_data.py  —  AUTO-GENERATED. DO NOT EDIT BY HAND.
Source : PoB data export at {POB_BASE}
Generated : {time.strftime("%Y-%m-%d")}
Entries : {len(db):,}

Key: mod.{{group}}.{{prefix|suffix|implicit}}[.{{influence}}][#N]
ONE entry per (group, affix_type, influence) family.
slot_tiers gives the tier list PER SLOT — only tiers that can spawn on that slot.
"""
from typing import Dict, List, Optional
_H:List[str]=["Helmet"];_BA:List[str]=["Body Armour"]
_GL:List[str]=["Gloves"];_BO:List[str]=["Boots"]
_BE:List[str]=["Belt"];_AM:List[str]=["Amulet"]
_RI:List[str]=["Ring"];_MH:List[str]=["Main Hand"]
_OH:List[str]=["Off-hand"];_QU:List[str]=["Quiver"]
_JW:List[str]=["Jewel"];_AJ:List[str]=["Abyss Jewel"]
_CJ:List[str]=["Cluster Jewel"];_FL:List[str]=["Flask"]
_TI:List[str]=["Tincture"]
_WP:List[str]=_MH+_OH;_ARMOUR:List[str]=_H+_BA+_GL+_BO
_AM_RI:List[str]=_AM+_RI;_AM_RI_BE:List[str]=_AM+_RI+_BE
_JEWELS:List[str]=_JW+_AJ+_CJ
MOD_DB:Dict[str,dict]={{
'''
    lines = [header]; cur = None
    for key, e in sorted_entries:
        ps = _primary(e)
        if ps != cur:
            cur = ps
            lbl = section_labels.get(ps, ps)
            pad = "═" * max(0, 74 - len(lbl) - 4)
            lines.append(f"\n    # ╔══ {lbl} {pad}╗\n")
        lines.append(
            f"    {key!r}:{{\n"
            f'        "label":{e["label"]!r},"affix_type":{e["affix_type"]!r},\n'
            f'        "slots":{_slot_expr(e["slots"])},"slot_tiers":{e["slot_tiers"]!r},\n'
            f'        "type":{e["type"]!r},"tiers":{e["tiers"]!r},"group":{e["group"]!r},\n'
            f'        "stat_ids":[],"influence":{e["influence"]!r},"source":"pob",\n'
            f"    }},\n"
        )
    lines.append('}\nAFFIX_LABELS:Dict[str,str]={\n'
                 '    "prefix":"Prefix","suffix":"Suffix","implicit":"Implicit",\n'
                 '    "corrupted":"Corrupted","crafted":"Crafted","enchant":"Enchant",\n'
                 '    "unknown":"","":""}\n')
    out_path.write_text("".join(lines), encoding="utf-8")


# ── Main ─────────────────────────────────────────────────────────────────────

def run_build(*, dry_run: bool = False, force_fetch: bool = False) -> dict:
    if force_fetch:
        clear_cache_files(CACHE_DIR, "*.json")
        print("Cache cleared.")

    print("=== build_mod_db.py (PoB source) ===\n")
    db = build_mod_db()
    _validate(db)

    from collections import Counter
    infl = Counter(v["influence"] or "—" for v in db.values())
    slot = Counter(s for v in db.values() for s in v["slots"])
    print(f"\n  Total families: {len(db):,}")
    print("  By influence:", {k: v for k, v in sorted(infl.items(), key=lambda x: -x[1])})
    print("  By slot:")
    for s in ["Helmet", "Body Armour", "Gloves", "Boots", "Ring", "Amulet", "Belt",
              "Main Hand", "Off-hand", "Quiver", "Jewel", "Abyss Jewel", "Cluster Jewel",
              "Flask", "Tincture"]:
        print(f"    {s:22}: {slot.get(s, 0):4}")

    result = {
        "ok": True,
        "dry_run": dry_run,
        "output_path": str(OUT_PATH),
        "families": len(db),
    }

    if dry_run:
        print("\n[DRY RUN] not writing.")
        result["written"] = False
        return result

    print(f"\nWriting {OUT_PATH} …")
    write_mod_data(db, OUT_PATH)
    kb = OUT_PATH.stat().st_size // 1024
    print(f"Done — {kb} KB, {len(db):,} entries.")
    result.update({"written": True, "size_kb": kb})
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-fetch", action="store_true")
    args = parser.parse_args()
    run_build(dry_run=args.dry_run, force_fetch=args.force_fetch)


if __name__ == "__main__":
    main()
