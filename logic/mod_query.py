from __future__ import annotations
"""
logic/mod_query.py — Query helpers over MOD_DB + PSEUDO_DB + META_DB.

PSEUDO_DB: synthetic mods that sum multiple real stat values across the item
           (mirrors PoE Trade "Pseudo" filters).
META_DB:   structural item properties (# of affixes, influences, enchants…)
           evaluated against the item itself rather than its mod values.
"""
from typing import Optional, List, Tuple, Dict, Any
from data.mod_data import MOD_DB, AFFIX_LABELS  # noqa: F401 — re-exported for UI

# ── Slot lists ─────────────────────────────────────────────────────────────
_ARMOUR_ACC = [
    "Helmet", "Body Armour", "Gloves", "Boots",
    "Ring", "Amulet", "Belt",
]
_WEAPONS = ["Main Hand", "Off-hand"]
_ALL_SLOTS = _ARMOUR_ACC + _WEAPONS + [
    "Quiver", "Jewel", "Abyss Jewel", "Cluster Jewel",
]


# ══════════════════════════════════════════════════════════════════════════════
#  PSEUDO_DB — mirrors PoE Trade "Pseudo" tab
#  Keys use "pseudo." prefix.
#  "pseudo_components":     stat_ids to sum for OAuth (extended) mode.
#  "pseudo_text_keywords":  substrings to match in mod text for sessid mode.
# ══════════════════════════════════════════════════════════════════════════════

PSEUDO_DB: Dict[str, Dict[str, Any]] = {

    # ── Resistances ───────────────────────────────────────────────────────
    "pseudo.total_fire_resistance": {
        "label": "+#% total to Fire Resistance",
        "affix_type": "pseudo", "influence": None,
        "slots": _ARMOUR_ACC, "tiers": [], "slot_tiers": {},
        "group": "pseudo_fire_res", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_3372524247"],
        "pseudo_text_keywords": ["fire resistance"],
    },
    "pseudo.total_cold_resistance": {
        "label": "+#% total to Cold Resistance",
        "affix_type": "pseudo", "influence": None,
        "slots": _ARMOUR_ACC, "tiers": [], "slot_tiers": {},
        "group": "pseudo_cold_res", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_4220027924"],
        "pseudo_text_keywords": ["cold resistance"],
    },
    "pseudo.total_lightning_resistance": {
        "label": "+#% total to Lightning Resistance",
        "affix_type": "pseudo", "influence": None,
        "slots": _ARMOUR_ACC, "tiers": [], "slot_tiers": {},
        "group": "pseudo_light_res", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_1671376347"],
        "pseudo_text_keywords": ["lightning resistance"],
    },
    "pseudo.total_chaos_resistance": {
        "label": "+#% total to Chaos Resistance",
        "affix_type": "pseudo", "influence": None,
        "slots": _ARMOUR_ACC, "tiers": [], "slot_tiers": {},
        "group": "pseudo_chaos_res", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_2923486259"],
        "pseudo_text_keywords": ["chaos resistance"],
    },
    "pseudo.total_elemental_resistance": {
        "label": "+#% total Elemental Resistance",
        "affix_type": "pseudo", "influence": None,
        "slots": _ARMOUR_ACC, "tiers": [], "slot_tiers": {},
        "group": "pseudo_ele_res", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    [
            "explicit.stat_3372524247",
            "explicit.stat_4220027924",
            "explicit.stat_1671376347",
        ],
        "pseudo_text_keywords": ["fire resistance", "cold resistance", "lightning resistance"],
    },
    "pseudo.total_all_resistance": {
        "label": "+#% total to all Resistances",
        "affix_type": "pseudo", "influence": None,
        "slots": _ARMOUR_ACC, "tiers": [], "slot_tiers": {},
        "group": "pseudo_all_res", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    [
            "explicit.stat_3372524247",
            "explicit.stat_4220027924",
            "explicit.stat_1671376347",
            "explicit.stat_2923486259",
        ],
        "pseudo_text_keywords": ["fire resistance", "cold resistance",
                                  "lightning resistance", "chaos resistance"],
    },

    # ── Life / Mana / ES ──────────────────────────────────────────────────
    "pseudo.total_life": {
        "label": "+# total maximum Life",
        "affix_type": "pseudo", "influence": None,
        "slots": _ARMOUR_ACC, "tiers": [], "slot_tiers": {},
        "group": "pseudo_life", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_3299347043"],
        "pseudo_text_keywords": ["to maximum life"],
    },
    "pseudo.total_mana": {
        "label": "+# total maximum Mana",
        "affix_type": "pseudo", "influence": None,
        "slots": _ARMOUR_ACC, "tiers": [], "slot_tiers": {},
        "group": "pseudo_mana", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_1050105434"],
        "pseudo_text_keywords": ["to maximum mana"],
    },
    "pseudo.total_energy_shield": {
        "label": "+# total maximum Energy Shield",
        "affix_type": "pseudo", "influence": None,
        "slots": _ARMOUR_ACC, "tiers": [], "slot_tiers": {},
        "group": "pseudo_es", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_1571049121"],
        "pseudo_text_keywords": ["to maximum energy shield"],
    },

    # ── Attributes ────────────────────────────────────────────────────────
    "pseudo.total_strength": {
        "label": "+# total to Strength",
        "affix_type": "pseudo", "influence": None,
        "slots": _ARMOUR_ACC, "tiers": [], "slot_tiers": {},
        "group": "pseudo_str", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    [
            "explicit.stat_4080418644",   # +# to Strength
            "explicit.stat_1379411836",   # +# to all Attributes
        ],
        "pseudo_text_keywords": ["to strength", "to all attributes"],
    },
    "pseudo.total_dexterity": {
        "label": "+# total to Dexterity",
        "affix_type": "pseudo", "influence": None,
        "slots": _ARMOUR_ACC, "tiers": [], "slot_tiers": {},
        "group": "pseudo_dex", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    [
            "explicit.stat_3261801346",   # +# to Dexterity
            "explicit.stat_1379411836",   # +# to all Attributes
        ],
        "pseudo_text_keywords": ["to dexterity", "to all attributes"],
    },
    "pseudo.total_intelligence": {
        "label": "+# total to Intelligence",
        "affix_type": "pseudo", "influence": None,
        "slots": _ARMOUR_ACC, "tiers": [], "slot_tiers": {},
        "group": "pseudo_int", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    [
            "explicit.stat_328541901",    # +# to Intelligence
            "explicit.stat_1379411836",   # +# to all Attributes
        ],
        "pseudo_text_keywords": ["to intelligence", "to all attributes"],
    },
    "pseudo.total_all_attributes": {
        "label": "+# total to all Attributes",
        "affix_type": "pseudo", "influence": None,
        "slots": _ARMOUR_ACC, "tiers": [], "slot_tiers": {},
        "group": "pseudo_all_attr", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_1379411836"],
        "pseudo_text_keywords": ["to all attributes"],
    },

    # ── Speed ─────────────────────────────────────────────────────────────
    "pseudo.total_attack_speed": {
        "label": "+#% total Attack Speed",
        "affix_type": "pseudo", "influence": None,
        "slots": _WEAPONS + _ARMOUR_ACC, "tiers": [], "slot_tiers": {},
        "group": "pseudo_atk_spd", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_210067635"],
        "pseudo_text_keywords": ["attack speed"],
    },
    "pseudo.total_cast_speed": {
        "label": "+#% total Cast Speed",
        "affix_type": "pseudo", "influence": None,
        "slots": _ARMOUR_ACC, "tiers": [], "slot_tiers": {},
        "group": "pseudo_cast_spd", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_2891184991"],
        "pseudo_text_keywords": ["cast speed"],
    },
    "pseudo.total_movement_speed": {
        "label": "+#% total increased Movement Speed",
        "affix_type": "pseudo", "influence": None,
        "slots": ["Boots"], "tiers": [], "slot_tiers": {},
        "group": "pseudo_move_spd", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_2250533757"],
        "pseudo_text_keywords": ["movement speed"],
    },

    # ── Critical Strike ───────────────────────────────────────────────────
    "pseudo.total_crit_chance": {
        "label": "+#% total Global Critical Strike Chance",
        "affix_type": "pseudo", "influence": None,
        "slots": _WEAPONS + _ARMOUR_ACC, "tiers": [], "slot_tiers": {},
        "group": "pseudo_crit_chance", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_587431675"],
        "pseudo_text_keywords": ["global critical strike chance"],
    },
    "pseudo.total_crit_multi": {
        "label": "+#% total Global Critical Strike Multiplier",
        "affix_type": "pseudo", "influence": None,
        "slots": _WEAPONS + _ARMOUR_ACC, "tiers": [], "slot_tiers": {},
        "group": "pseudo_crit_multi", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_3556462232"],
        "pseudo_text_keywords": ["critical strike multiplier"],
    },

    # ── Damage (spells / physical) ────────────────────────────────────────
    "pseudo.total_spell_damage": {
        "label": "+#% total increased Spell Damage",
        "affix_type": "pseudo", "influence": None,
        "slots": _WEAPONS + _ARMOUR_ACC, "tiers": [], "slot_tiers": {},
        "group": "pseudo_spell_dmg", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_2974417149"],
        "pseudo_text_keywords": ["increased spell damage"],
    },
    "pseudo.total_physical_damage_pct": {
        "label": "+#% total increased Physical Damage",
        "affix_type": "pseudo", "influence": None,
        "slots": _WEAPONS, "tiers": [], "slot_tiers": {},
        "group": "pseudo_phys_dmg_pct", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_1509134228"],
        "pseudo_text_keywords": ["increased physical damage"],
    },

    # ── Added damage to attacks ───────────────────────────────────────────
    "pseudo.total_added_physical_damage": {
        "label": "# total Added Physical Damage to Attacks",
        "affix_type": "pseudo", "influence": None,
        "slots": _WEAPONS + ["Ring", "Amulet", "Gloves"], "tiers": [], "slot_tiers": {},
        "group": "pseudo_add_phys", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_960081730"],   # adds phys damage (avg)
        "pseudo_text_keywords": ["adds physical damage", "to attacks"],
    },
    "pseudo.total_added_fire_damage": {
        "label": "# total Added Fire Damage to Attacks",
        "affix_type": "pseudo", "influence": None,
        "slots": _WEAPONS + ["Ring", "Amulet", "Gloves"], "tiers": [], "slot_tiers": {},
        "group": "pseudo_add_fire", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_1255753075"],
        "pseudo_text_keywords": ["adds fire damage", "to attacks"],
    },
    "pseudo.total_added_cold_damage": {
        "label": "# total Added Cold Damage to Attacks",
        "affix_type": "pseudo", "influence": None,
        "slots": _WEAPONS + ["Ring", "Amulet", "Gloves"], "tiers": [], "slot_tiers": {},
        "group": "pseudo_add_cold", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_3291658075"],
        "pseudo_text_keywords": ["adds cold damage", "to attacks"],
    },
    "pseudo.total_added_lightning_damage": {
        "label": "# total Added Lightning Damage to Attacks",
        "affix_type": "pseudo", "influence": None,
        "slots": _WEAPONS + ["Ring", "Amulet", "Gloves"], "tiers": [], "slot_tiers": {},
        "group": "pseudo_add_light", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_3962278098"],
        "pseudo_text_keywords": ["adds lightning damage", "to attacks"],
    },
    "pseudo.total_added_chaos_damage": {
        "label": "# total Added Chaos Damage to Attacks",
        "affix_type": "pseudo", "influence": None,
        "slots": _WEAPONS + ["Ring", "Amulet", "Gloves"], "tiers": [], "slot_tiers": {},
        "group": "pseudo_add_chaos", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_2435536961"],
        "pseudo_text_keywords": ["adds chaos damage", "to attacks"],
    },

    # ── Added spell damage ─────────────────────────────────────────────────
    "pseudo.total_added_fire_damage_spells": {
        "label": "# total Added Fire Damage to Spells",
        "affix_type": "pseudo", "influence": None,
        "slots": _WEAPONS + ["Ring", "Amulet", "Wand", "Sceptre"], "tiers": [], "slot_tiers": {},
        "group": "pseudo_add_fire_spell", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_1573130764"],
        "pseudo_text_keywords": ["adds fire damage to spells"],
    },
    "pseudo.total_added_cold_damage_spells": {
        "label": "# total Added Cold Damage to Spells",
        "affix_type": "pseudo", "influence": None,
        "slots": _WEAPONS + ["Ring", "Amulet", "Wand", "Sceptre"], "tiers": [], "slot_tiers": {},
        "group": "pseudo_add_cold_spell", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_3291658075"],
        "pseudo_text_keywords": ["adds cold damage to spells"],
    },
    "pseudo.total_added_lightning_damage_spells": {
        "label": "# total Added Lightning Damage to Spells",
        "affix_type": "pseudo", "influence": None,
        "slots": _WEAPONS + ["Ring", "Amulet", "Wand", "Sceptre"], "tiers": [], "slot_tiers": {},
        "group": "pseudo_add_light_spell", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_3962278098"],
        "pseudo_text_keywords": ["adds lightning damage to spells"],
    },

    # ── Global defences ────────────────────────────────────────────────────
    "pseudo.total_increased_armour": {
        "label": "#% total increased Armour",
        "affix_type": "pseudo", "influence": None,
        "slots": ["Helmet","Body Armour","Gloves","Boots","Shield"], "tiers": [], "slot_tiers": {},
        "group": "pseudo_armour", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_809229260"],
        "pseudo_text_keywords": ["increased armour"],
    },
    "pseudo.total_increased_evasion": {
        "label": "#% total increased Evasion Rating",
        "affix_type": "pseudo", "influence": None,
        "slots": ["Helmet","Body Armour","Gloves","Boots","Shield"], "tiers": [], "slot_tiers": {},
        "group": "pseudo_evasion", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_2144192055"],
        "pseudo_text_keywords": ["increased evasion rating"],
    },
    "pseudo.total_increased_es": {
        "label": "#% total increased Energy Shield",
        "affix_type": "pseudo", "influence": None,
        "slots": ["Helmet","Body Armour","Gloves","Boots","Shield"], "tiers": [], "slot_tiers": {},
        "group": "pseudo_es_pct", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_2866361420"],
        "pseudo_text_keywords": ["increased energy shield"],
    },

    # ── Mana ───────────────────────────────────────────────────────────────
    "pseudo.total_mana_regen": {
        "label": "+# total Mana Regenerated per Second",
        "affix_type": "pseudo", "influence": None,
        "slots": _ARMOUR_ACC, "tiers": [], "slot_tiers": {},
        "group": "pseudo_mana_regen", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_789117908"],
        "pseudo_text_keywords": ["mana regenerated per second"],
    },

    # ── Resistance flavours ────────────────────────────────────────────────
    "pseudo.total_fire_and_cold_resistance": {
        "label": "+#% total to Fire and Cold Resistance",
        "affix_type": "pseudo", "influence": None,
        "slots": _ARMOUR_ACC, "tiers": [], "slot_tiers": {},
        "group": "pseudo_fire_cold_res", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_3372524247", "explicit.stat_4220027924"],
        "pseudo_text_keywords": ["fire resistance", "cold resistance"],
    },
    "pseudo.total_fire_and_lightning_resistance": {
        "label": "+#% total to Fire and Lightning Resistance",
        "affix_type": "pseudo", "influence": None,
        "slots": _ARMOUR_ACC, "tiers": [], "slot_tiers": {},
        "group": "pseudo_fire_light_res", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_3372524247", "explicit.stat_1671376347"],
        "pseudo_text_keywords": ["fire resistance", "lightning resistance"],
    },
    "pseudo.total_cold_and_lightning_resistance": {
        "label": "+#% total to Cold and Lightning Resistance",
        "affix_type": "pseudo", "influence": None,
        "slots": _ARMOUR_ACC, "tiers": [], "slot_tiers": {},
        "group": "pseudo_cold_light_res", "type": "pseudo", "stat_ids": [],
        "pseudo_components":    ["explicit.stat_4220027924", "explicit.stat_1671376347"],
        "pseudo_text_keywords": ["cold resistance", "lightning resistance"],
    },
}


# ══════════════════════════════════════════════════════════════════════════════
#  META_DB — structural item filters (affix counts, influences, …)
#  Keys use "meta." prefix.
#  Scoring is handled in mod_scorer._eval_meta_filter().
# ══════════════════════════════════════════════════════════════════════════════

META_DB: Dict[str, Dict[str, Any]] = {

    # ── Affix counts ──────────────────────────────────────────────────────
    "meta.num_prefixes": {
        "label": "# of Prefixes",
        "affix_type": "meta", "influence": None,
        "slots": [], "tiers": [], "slot_tiers": {},
        "group": "meta_affixes", "type": "meta", "stat_ids": [],
        "meta_description": "Number of prefix mods on the item",
    },
    "meta.num_suffixes": {
        "label": "# of Suffixes",
        "affix_type": "meta", "influence": None,
        "slots": [], "tiers": [], "slot_tiers": {},
        "group": "meta_affixes", "type": "meta", "stat_ids": [],
        "meta_description": "Number of suffix mods on the item",
    },
    "meta.num_empty_prefix_slots": {
        "label": "# of Empty Prefix Slots",
        "affix_type": "meta", "influence": None,
        "slots": [], "tiers": [], "slot_tiers": {},
        "group": "meta_affixes", "type": "meta", "stat_ids": [],
        "meta_description": "How many prefix slots are still open",
    },
    "meta.num_empty_suffix_slots": {
        "label": "# of Empty Suffix Slots",
        "affix_type": "meta", "influence": None,
        "slots": [], "tiers": [], "slot_tiers": {},
        "group": "meta_affixes", "type": "meta", "stat_ids": [],
        "meta_description": "How many suffix slots are still open",
    },
    "meta.num_explicit_mods": {
        "label": "# of Explicit Mods",
        "affix_type": "meta", "influence": None,
        "slots": [], "tiers": [], "slot_tiers": {},
        "group": "meta_mods", "type": "meta", "stat_ids": [],
        "meta_description": "Total explicit + crafted mods on the item",
    },
    "meta.num_implicit_mods": {
        "label": "# of Implicit Mods",
        "affix_type": "meta", "influence": None,
        "slots": [], "tiers": [], "slot_tiers": {},
        "group": "meta_mods", "type": "meta", "stat_ids": [],
        "meta_description": "Number of implicit mods",
    },
    "meta.num_enchants": {
        "label": "# of Enchantments",
        "affix_type": "meta", "influence": None,
        "slots": [], "tiers": [], "slot_tiers": {},
        "group": "meta_mods", "type": "meta", "stat_ids": [],
        "meta_description": "Number of enchantment mods",
    },
    "meta.num_fractured_mods": {
        "label": "# of Fractured Mods",
        "affix_type": "meta", "influence": None,
        "slots": [], "tiers": [], "slot_tiers": {},
        "group": "meta_mods", "type": "meta", "stat_ids": [],
        "meta_description": "Number of fractured mods",
    },
    "meta.num_crafted_mods": {
        "label": "# of Crafted Mods",
        "affix_type": "meta", "influence": None,
        "slots": [], "tiers": [], "slot_tiers": {},
        "group": "meta_mods", "type": "meta", "stat_ids": [],
        "meta_description": "Number of crafted (master-crafted) mods",
    },

    # ── Influence (unified dropdown picker) ──────────────────────────────
    # The exact influence to match is stored at runtime in
    # ModFilter.meta_influence_value (not in to_dict/from_dict).
    # The ModRow widget renders a dropdown instead of min/max fields.
    "meta.has_influence": {
        "label":            "Item has Influence",
        "affix_type":       "meta",
        "influence":        None,
        "slots":            [],
        "tiers":            [],
        "slot_tiers":       {},
        "group":            "meta_influence",
        "type":             "meta",
        "stat_ids":         [],
        "meta_type":        "influence_picker",
        "meta_description": "Item has a specific influence — choose from dropdown",
        "influence_choices": [
            "any",
            "shaper", "elder",
            "crusader", "redeemer", "warlord", "hunter",
            "searing_exarch", "eater_of_worlds",
        ],
    },
    "meta.is_veiled": {
        "label": "Item has Veiled Mods",
        "affix_type": "meta", "influence": None,
        "slots": [], "tiers": [], "slot_tiers": {},
        "group": "meta_state", "type": "meta", "stat_ids": [],
        "meta_description": "Item has at least one veiled mod",
    },
}

# Merged view: pseudo → meta → real mods (pseudo/meta appear first)
_COMBINED_DB: Dict[str, Dict[str, Any]] = {**PSEUDO_DB, **META_DB, **MOD_DB}


# ── Query helpers ──────────────────────────────────────────────────────────

def mods_for_slot(slot: str) -> List[dict]:
    """Return all _COMBINED_DB entries valid for the given slot, stat_id injected."""
    result = []
    for stat_id, data in _COMBINED_DB.items():
        allowed = data.get("slots", [])
        # META mods (empty slots list) apply to all slots
        if not allowed or slot in allowed:
            result.append({"stat_id": stat_id, **data})
    return result


def get_mod(stat_id: str) -> Optional[dict]:
    return _COMBINED_DB.get(stat_id)


def is_pseudo(stat_id: str) -> bool:
    return stat_id.startswith("pseudo.")


def is_meta(stat_id: str) -> bool:
    return stat_id.startswith("meta.")


def _tiers_for_slot(mod: dict, slot: str) -> List[Tuple]:
    if slot:
        st = mod.get("slot_tiers", {})
        if slot in st:
            return st[slot]
    return mod.get("tiers", [])


def get_mod_tiers_for_slot(stat_id: str, slot: str = "") -> List[Tuple[float, float]]:
    mod = _COMBINED_DB.get(stat_id)
    if not mod:
        return []
    return _tiers_for_slot(mod, slot)


def tier_of_value(stat_id: str, value: float, slot: str = "") -> Optional[int]:
    tiers = get_mod_tiers_for_slot(stat_id, slot)
    for rank, (lo, hi) in enumerate(tiers, start=1):
        if lo <= value <= hi:
            return rank
    return None


def tier_range(stat_id: str, tier: int, slot: str = "") -> Optional[Tuple[float, float]]:
    tiers = get_mod_tiers_for_slot(stat_id, slot)
    if 1 <= tier <= len(tiers):
        return tuple(tiers[tier - 1])
    return None


def num_tiers(stat_id: str, slot: str = "") -> int:
    return len(get_mod_tiers_for_slot(stat_id, slot))


def find_entries_for_stat(internal_stat_id: str) -> List[dict]:
    return [
        {"stat_id": k, **v}
        for k, v in _COMBINED_DB.items()
        if internal_stat_id in v.get("stat_ids", [])
    ]


def find_entries_for_slot_and_stat(slot: str, internal_stat_id: str) -> List[dict]:
    candidates = [
        {"stat_id": k, **v}
        for k, v in _COMBINED_DB.items()
        if slot in v.get("slots", [])
        and internal_stat_id in v.get("stat_ids", [])
    ]
    candidates.sort(key=lambda x: len(x.get("slots", [])))
    return candidates
