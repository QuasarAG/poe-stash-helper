from __future__ import annotations
"""
logic/unified_filter.py — Unified AND-logic filter combining:
  - Slot mod filters   ({slot: [ModFilter]})
  - Base type selections ({slot: [base_name]})
  - Item property filters ({slot: filter_dict})

An item PASSES when ALL active filter groups agree.
If a group has no active rules it contributes True (passes everything).
"""

from typing import Optional
from logic.item_parser import ParsedItem
from logic.mod_scorer   import ModFilter, score_item
from models import ActiveModBehaviour, ItemRarity


FRAME_NORMAL  = 0
FRAME_MAGIC   = 1
FRAME_RARE    = 2
FRAME_UNIQUE  = 3


def _in_range(val: float, lo: float, hi: Optional[float]) -> bool:
    """Return True if lo <= val <= hi (hi=None means no upper bound)."""
    if val < lo:
        return False
    if hi is not None and val > hi:
        return False
    return True


def _yesno(val: bool, choice: str) -> bool:
    if choice == "Any":
        return True
    return val if choice == "Yes" else (not val)


# ── Active-mod-group-aware mod evaluation ─────────────────────────────────────────────

def _eval_group(item: ParsedItem, behaviour: str,
                filters: list[ModFilter],
                count_min: int = 1, count_max: int = 0) -> tuple[bool, list, float]:
    """Evaluate one active mod group of filters against an item.

    Returns (passes: bool, matched_labels: list[str], score_contribution: float).

    Behaviours:
      AND   — every enabled filter must match (standard scoring)
      NOT   — none of the filters may match (item passes only if 0 match)
      IF    — filters are optional; only score mods that are present
              (item always passes this active mod group; matched mods contribute to score)
      COUNT — at least count_min (and at most count_max if > 0) filters match
    """
    if not filters:
        return True, [], 0.0

    result = score_item(item, filters)
    n_matched = len(result.matched)

    if behaviour == ActiveModBehaviour.NOT:
        passes = (n_matched == 0)
        return passes, [], 0.0

    if behaviour == ActiveModBehaviour.IF:
        # Always passes; contributes matched mods to score
        return True, result.matched, result.score

    if behaviour == ActiveModBehaviour.COUNT:
        passes = n_matched >= count_min
        if count_max > 0:
            passes = passes and (n_matched <= count_max)
        return passes, result.matched, result.score

    # AND (default)
    passes = (n_matched == len(filters)) and not result.missing_required
    return passes, result.matched, result.score


def _group_filters_by_active_mod_group(filters: list[ModFilter]) -> list[dict]:
    """Group a flat filter list into active-mod-group dictionaries.

    Consecutive filters with the same behaviour and count settings are merged
    into one active mod group entry.
    """
    if not filters:
        return []

    groups: list[dict] = []
    cur_beh   = None
    cur_min   = 1
    cur_max   = 0
    cur_filts: list[ModFilter] = []

    for f in filters:
        beh = getattr(f, "_group_behaviour", ActiveModBehaviour.AND) or ActiveModBehaviour.AND
        if isinstance(beh, str):
            beh = ActiveModBehaviour(beh)
        cmin  = getattr(f, "_count_min", 1)  or 1
        cmax  = getattr(f, "_count_max", 0)  or 0

        if beh != cur_beh or (beh == ActiveModBehaviour.COUNT and (cmin != cur_min or cmax != cur_max)):
            if cur_filts:
                groups.append({"behaviour": cur_beh, "count_min": cur_min,
                                "count_max": cur_max, "filters": cur_filts})
            cur_beh, cur_min, cur_max, cur_filts = beh, cmin, cmax, []
        cur_filts.append(f)

    if cur_filts:
        groups.append({"behaviour": cur_beh, "count_min": cur_min,
                        "count_max": cur_max, "filters": cur_filts})
    return groups


def _pass_mods(item: ParsedItem, slot_filters: dict[str, list[ModFilter]]) -> bool:
    if not slot_filters:
        return True
    slot = item.equipment_slot
    filters = slot_filters.get(slot) or slot_filters.get("Any") or []
    if not filters:
        if list(slot_filters.keys()) == ["Any"]:
            filters = slot_filters["Any"]
        else:
            return True
    if not filters:
        return True

    groups = _group_filters_by_active_mod_group(filters)
    for group in groups:
        passes, _, _ = _eval_group(
            item, group["behaviour"], group["filters"],
            group["count_min"], group["count_max"]
        )
        if not passes:
            return False
    return True


# ── Base type check ────────────────────────────────────────────────────────

def _pass_bases(item: ParsedItem,
                base_selections: dict[str, list[str]],
                slot_filters: dict) -> bool:
    if not slot_filters and not base_selections:
        return True
    slot = item.equipment_slot
    targeted_slots = set(slot_filters.keys()) | set(base_selections.keys())
    if "Any" not in targeted_slots and slot not in targeted_slots:
        return False
    bases = base_selections.get(slot)
    if bases:
        return item.base_type in bases
    return True


# ── Property check ─────────────────────────────────────────────────────────

def _pass_properties(item: ParsedItem,
                     item_props: dict) -> bool:
    """Check item against slot-scoped property filters.
    item_props = {slot: filter_dict} from ItemPropertyPanel.get_all_slot_filters()"""
    if not item_props:
        return True
    slot  = item.equipment_slot
    props = item_props.get(slot) or item_props.get("Any") or {}
    if not props:
        return True

    # Rarity
    if "rarity" in props:
        rmap = {
            ItemRarity.NORMAL.value: FRAME_NORMAL,
            ItemRarity.MAGIC.value: FRAME_MAGIC,
            ItemRarity.RARE.value: FRAME_RARE,
            ItemRarity.UNIQUE.value: FRAME_UNIQUE,
        }
        allowed = {rmap[r] for r in props["rarity"] if r in rmap}
        if allowed and item.frame_type not in allowed:
            return False

    # Weapon stats
    if "weapon" in props:
        w = props["weapon"]
        if not _in_range(item.phys_dps,   w.get("w_pdps_min",0), w.get("w_pdps_max") or None): return False
        if not _in_range(item.elem_dps,   w.get("w_edps_min",0), w.get("w_edps_max") or None): return False
        if not _in_range(item.attacks_ps, w.get("w_aps_min",0),  w.get("w_aps_max")  or None): return False

    # Armour stats
    if "armour" in props:
        a = props["armour"]
        if not _in_range(item.armour,        a.get("a_arm_min",0),  a.get("a_arm_max")  or None): return False
        if not _in_range(item.evasion,       a.get("a_eva_min",0),  a.get("a_eva_max")  or None): return False
        if not _in_range(item.energy_shield, a.get("a_es_min",0),   a.get("a_es_max")   or None): return False
        if not _in_range(item.ward,          a.get("a_ward_min",0), a.get("a_ward_max") or None): return False
        if not _in_range(item.block,         a.get("a_blk_min",0),  a.get("a_blk_max")  or None): return False

    # Sockets
    if "sockets" in props:
        s = props["sockets"]
        if not _in_range(item.sockets, s.get("soc_min",0), s.get("soc_max") or None): return False
        if not _in_range(item.links,   s.get("lnk_min",0), s.get("lnk_max") or None): return False

    # Misc
    if "misc" in props:
        m = props["misc"]
        if not _in_range(item.quality, m.get("qual_min",0), m.get("qual_max") or None): return False
        if not _in_range(item.ilvl,    m.get("ilvl_min",0), m.get("ilvl_max") or None): return False
        if not _yesno(item.corrupted,          m.get("corrupted",   "Any")): return False
        if not _yesno(item.identified,         m.get("identified",  "Any")): return False
        if not _yesno(item.mirrored,           m.get("mirrored",    "Any")): return False
        if not _yesno(item.split,              m.get("split",       "Any")): return False
        if not _yesno(item.veiled,             m.get("veiled",      "Any")): return False
        if not _yesno(item.synthesised,        m.get("synthesised", "Any")): return False
        if not _yesno(item.fractured,          m.get("fractured",   "Any")): return False
        if not _yesno(item.foulborn,           m.get("foulborn",    "Any")): return False
        if not _yesno(bool(item.crafted_mods), m.get("crafted",     "Any")): return False
        if not _yesno(item.influences.get("searing_exarch", False),  m.get("searing", "Any")): return False
        if not _yesno(item.influences.get("eater_of_worlds", False), m.get("eater",   "Any")): return False

    # Memory strands filter (stored in props["memory_strand"])
    ms_props = props.get("memory_strand")
    if ms_props:
        ms_min = ms_props.get("ms_min", 0)
        ms_max = ms_props.get("ms_max", 0)
        if ms_min > 0 and item.memory_strands < ms_min: return False
        if ms_max > 0 and item.memory_strands > ms_max: return False

    # Requirements
    if "req" in props:
        r = props["req"]
        if not _in_range(item.req_level, r.get("req_level_min",0), r.get("req_level_max") or None): return False
        if not _in_range(item.req_str,   r.get("req_str_min",  0), r.get("req_str_max")   or None): return False
        if not _in_range(item.req_dex,   r.get("req_dex_min",  0), r.get("req_dex_max")   or None): return False
        if not _in_range(item.req_int,   r.get("req_int_min",  0), r.get("req_int_max")   or None): return False

    return True



# ── Main entry point ───────────────────────────────────────────────────────

def apply_unified_filter(
    items:           list[ParsedItem],
    slot_filters:    dict[str, list[ModFilter]],
    base_selections: dict[str, list[str]],
    item_props:      dict[str, dict],
) -> list[ParsedItem]:
    """
    Filter items using AND logic across all three filter groups.
    Sets item.score and item.matched_mods on each passing item.
    Returns only items that pass all active groups.
    Returns all items with score=0 if no filters are active at all.
    """
    has_mods  = bool(slot_filters)
    has_bases = bool(base_selections) or bool(slot_filters)
    has_props = bool(item_props)
    # Slots that have property filters (used when no loadout slots active)
    prop_slots = set(item_props.keys()) if item_props else set()

    if not has_mods and not has_bases and not has_props:
        for item in items:
            item.score = 0
            item.matched_mods = []
        return items

    result = []
    for item in items:
        # Skip non-equipment (gems=4, currency=5, divination cards=6)
        if item.frame_type in (4, 5, 6):
            continue

        if has_bases and not _pass_bases(item, base_selections, slot_filters):
            continue

        # Property-only mode: only show items whose slot has a configured filter
        if has_props and not has_bases:
            if item.equipment_slot not in prop_slots:
                continue

        if has_props and not _pass_properties(item, item_props):
            continue

        if has_mods:
            slot = item.equipment_slot
            filters = slot_filters.get(slot) or slot_filters.get("Any") or []
            if filters:
                groups = _group_filters_by_active_mod_group(filters)
                all_matched: list[str] = []
                total_score = 0.0
                passes_all = True
                for group in groups:
                    passes, matched, score_value = _eval_group(
                        item,
                        group["behaviour"],
                        group["filters"],
                        group["count_min"],
                        group["count_max"],
                    )
                    if not passes:
                        passes_all = False
                        break
                    all_matched.extend(matched)
                    total_score += score_value
                if not passes_all:
                    continue
                if not all_matched and not any(
                    ActiveModBehaviour(group["behaviour"]) in {ActiveModBehaviour.AND, ActiveModBehaviour.COUNT} for group in groups
                ):
                    # Only IF/NOT groups and nothing matched — slot-only style.
                    item.score = 1
                    item.matched_mods = []
                else:
                    number_of_groups = max(1, len(groups))
                    item.score = min(1.0, total_score / number_of_groups)
                    item.matched_mods = all_matched
                item.total_filters = len(filters)
            else:
                # Slot is targeted but no mods required — slot-only filter, fully matched.
                item.score = 1
                item.matched_mods = []
        else:
            item.score        = 1
            item.matched_mods = []

        result.append(item)

    return result
