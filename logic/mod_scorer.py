"""
logic/mod_scorer.py — Tier-aware mod scoring engine.

Key improvements over previous version:
  1. Stat ID matching is primary — text matching is strict fallback only
  2. Multi-value (hybrid) mods handled: takes the average of both values
  3. Tier detection: roll_pct is computed against the T1 range by default,
     but can be overridden by filter min/max sliders
  4. Required mods zero the whole item score if absent
  5. Tier thresholds (T1/T2/T3...) used in score_tier() are configurable

Mod filter format (stored in config):
    {
        "stat_id":  "explicit.stat_3299347043",
        "label":    "Maximum Life",
        "min":      80,       # optional manual override; defaults to T3 min
        "max":      120,      # optional manual override; defaults to T1 max
        "weight":   1.5,
        "required": false,
        "use_tier_range": true,  # if true, auto-set min/max from tier DB
    }
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from logic.item_parser import ParsedItem, ParsedMod
from data.mod_data     import MOD_DB
from logic.mod_query   import tier_of_value as _q_tier_of_value, tier_range
from logic.tier_utils  import tier_label


# ── Tier score thresholds (configurable, defaults match original colour tiers)
TIER_THRESHOLDS = {
    "tier1": 0.90,
    "tier2": 0.70,
    "tier3": 0.50,
    "tier4": 0.30,
}


@dataclass
class ModFilter:
    stat_id:         str
    label:           str
    weight:          float = 1.0
    min:             Optional[float] = None
    max:             Optional[float] = None
    required:        bool = False
    use_tier_range:  bool = True   # auto-populate min/max from tier DB if not set

    @classmethod
    def from_dict(cls, d: dict) -> "ModFilter":
        f = cls(
            stat_id        = d.get("stat_id", ""),
            label          = d.get("label", ""),
            weight         = float(d.get("weight", 1.0)),
            min            = d.get("min"),
            max            = d.get("max"),
            required       = bool(d.get("required", False)),
            use_tier_range = bool(d.get("use_tier_range", True)),
        )
        # Runtime-only attributes not in the dataclass fields
        if d.get("meta_influence_value"):
            f.meta_influence_value = d["meta_influence_value"]
        return f

    def to_dict(self) -> dict:
        d = {
            "stat_id":        self.stat_id,
            "label":          self.label,
            "weight":         self.weight,
            "min":            self.min,
            "max":            self.max,
            "required":       self.required,
            "use_tier_range": self.use_tier_range,
        }
        v = getattr(self, "meta_influence_value", None)
        if v:
            d["meta_influence_value"] = v
        return d

    def effective_range(self) -> tuple[Optional[float], Optional[float]]:
        """
        Return (lo, hi) for range checking and roll_pct scoring.

        Rules:
        - lo (minimum): user value if set, otherwise T_worst lo from tier DB
        - hi (maximum): user value if set → HARD CAP (val > hi = reject)
                        tier DB T1 hi if not set → soft scoring ceiling only
        Returns (lo, hi, user_set_max) via effective_range_full() for enforcement.
        Use effective_range() for scoring hi only (no hard cap from tier DB).
        """
        lo = self.min
        hi = self.max   # None if user didn't set a maximum
        if self.use_tier_range and self.stat_id:
            db_entry = MOD_DB.get(self.stat_id)
            if db_entry:
                t1      = db_entry["tiers"][0]
                t_worst = db_entry["tiers"][-1]
                if lo is None:
                    lo = float(t_worst[0])
                if hi is None:
                    hi = float(t1[1])   # soft scoring ceiling only
        return lo, hi

    @property
    def user_set_max(self) -> Optional[float]:
        """Return user-set maximum (hard cap) or None if not explicitly set."""
        return self.max  # self.max is only non-None when user set it explicitly

    def tier_at_value(self, value: float) -> Optional[int]:
        """Return tier (1=best) of a rolled value against MOD_DB."""
        return _q_tier_of_value(self.stat_id, value)


@dataclass
class ScoreResult:
    score:             float
    matched:           list[str] = field(default_factory=list)
    matched_tiers:     dict[str, int] = field(default_factory=dict)  # label → tier
    missing_required:  list[str] = field(default_factory=list)


# ── Value extraction ───────────────────────────────────────────────────────

def _nums(text: str) -> list[float]:
    return [float(x) for x in re.findall(r"[-+]?\d*\.?\d+", text)]


def _effective_value(mod: ParsedMod,
                     text_mode: bool = False) -> Optional[float]:
    """
    Extract a representative numeric value from a mod.

    When extended stat data is available (text_mode=False):
      - Two-value mods (e.g. 'Adds 5 to 12 Fire Damage'): return average.
      - Single-value: return the value.

    When only raw text is available (text_mode=True, SESSID mode):
      - Take the FIRST number only to avoid averaging unrelated stats
        in hybrid mods like '+45 Life and +12% ES'.
      - Averaging 45 and 12 would give 28.5 which is meaningless.
    """
    if mod.values:
        # Extended data available — averaging is safe (same stat)
        if len(mod.values) >= 2:
            return (mod.values[0] + mod.values[-1]) / 2.0
        return mod.values[0]
    # Text-only mode: first number is the primary stat
    vals = _nums(mod.text)
    if not vals:
        return None
    if text_mode:
        return vals[0]   # first number only — avoids hybrid false averaging
    return (vals[0] + vals[-1]) / 2.0 if len(vals) >= 2 else vals[0]


# ── Text-based fallback ───────────────────────────────────────────────────
# Used when mod.stat_ids is empty (SESSID API doesn't return extended data)
# Also used when filter has no stat_id.
#
# Strategy: strip common PoE prefixes from mod text, then keyword-match
# the meaningful words from the filter label.
# e.g. label="Maximum Life"       → matches "+92 to maximum Life"
#      label="Fire Resistance"     → matches "+40% to Fire Resistance"
#      label="% increased Armour"  → matches "74% increased Armour"

import re as _re

# Words to strip from filter labels before matching
_STOP_WORDS = {
    "to", "of", "a", "an", "the", "and", "or", "for", "with",
    "by", "from", "on", "in", "at", "is", "has", "#", "%",
    "increased", "reduced",   # keep these meaningful, remove generic connectors
}
# Actually keep "increased"/"reduced" since they differentiate mods — remove only
# very generic words:
_STOP_WORDS = {"to", "of", "a", "an", "the", "and", "or", "for", "with",
               "by", "from", "on", "in", "at", "is", "has", "#"}


def _key_words(label: str) -> list:
    """Extract meaningful lowercase words from a filter label."""
    # Remove stat-notation tokens like #, %, +#%
    cleaned = label.replace("#", "").replace("%", "").strip()
    words = [w.lower() for w in cleaned.split() if w.lower() not in _STOP_WORDS and len(w) > 1]
    return words


def _text_matches(mod_text: str, filt: ModFilter) -> bool:
    """
    Keyword match of filter label against raw mod text.
    Works even when extended (stat_id) data is absent.
    """
    label = filt.label
    # Remove prefix/suffix type tags like [Prefix], [Pseudo]
    label = _re.sub(r'\[.*?\]\s*', '', label).strip()
    words = _key_words(label)
    if not words:
        return False
    text_lower = mod_text.lower()
    # All key words must appear in the mod text
    return all(w in text_lower for w in words)


# ── Meta value extractor ───────────────────────────────────────────────────

def _max_affix_slots(item: "ParsedItem") -> int:
    """Max prefix OR suffix slots based on rarity (same for both)."""
    ft = item.frame_type
    if ft == 1:   return 1   # Magic: 1 prefix + 1 suffix
    if ft == 2:   return 3   # Rare:  3 prefix + 3 suffix
    return 0                  # Normal / Unique / other


def _count_affix_type(item: "ParsedItem", affix: str) -> int:
    """Count explicit mods with a known affix_type.

    Works when:
    - OAuth: extended data populated affix_type from GGG API
    - Sessid: MOD_DB lookup populated affix_type for known mods

    Returns -1 when affix_type is unknowable (all mods lack it).
    """
    known = [m for m in item.explicit_mods + item.crafted_mods if m.affix_type]
    if not known:
        return -1   # signal: cannot determine
    return sum(1 for m in known if m.affix_type == affix)


def _eval_meta_value(item: "ParsedItem", stat_id: str) -> Optional[float]:
    """Return the numeric value for a meta.* stat_id, or None if unknowable."""
    if stat_id == "meta.num_explicit_mods":
        return float(len(item.explicit_mods) + len(item.crafted_mods))

    if stat_id == "meta.num_implicit_mods":
        return float(len(item.implicit_mods))

    if stat_id == "meta.num_enchants":
        return float(len(item.enchant_mods))

    if stat_id == "meta.num_fractured_mods":
        return float(len(item.fractured_mods))

    if stat_id == "meta.num_crafted_mods":
        return float(len(item.crafted_mods))

    if stat_id == "meta.num_prefixes":
        n = _count_affix_type(item, "prefix")
        return float(n) if n >= 0 else None

    if stat_id == "meta.num_suffixes":
        n = _count_affix_type(item, "suffix")
        return float(n) if n >= 0 else None

    if stat_id == "meta.num_empty_prefix_slots":
        n = _count_affix_type(item, "prefix")
        if n < 0:
            return None
        return float(max(0, _max_affix_slots(item) - n))

    if stat_id == "meta.num_empty_suffix_slots":
        n = _count_affix_type(item, "suffix")
        if n < 0:
            return None
        return float(max(0, _max_affix_slots(item) - n))

    if stat_id == "meta.is_corrupted":
        return 1.0 if item.corrupted else 0.0

    if stat_id == "meta.is_veiled":
        return 1.0 if item.veiled else 0.0

    if stat_id == "meta.is_influenced":
        return 1.0 if any(item.influences.values()) else 0.0

    if stat_id == "meta.item_level":
        return float(item.ilvl)

    return None   # unknown meta stat_id


# ── Core scorer ────────────────────────────────────────────────────────────

def score_item(item: ParsedItem, filters: list[ModFilter]) -> ScoreResult:
    if not filters:
        return ScoreResult(score=0.0)

    all_mods: list[ParsedMod] = (
        item.explicit_mods + item.crafted_mods +
        item.implicit_mods + item.enchant_mods
    )

    # Detect whether we have extended data for this item
    # (at least one mod has stat_ids → extended data available)\
    has_extended = any(m.stat_ids for m in all_mods)
    text_mode    = not has_extended

    total_weight  = sum(f.weight for f in filters)
    earned_weight = 0.0
    matched:       list[str]      = []
    matched_tiers: dict[str, int] = {}
    missing_req:   list[str]      = []

    # Deduplication: each mod can only be claimed by one filter.
    # Prevents a hybrid mod matching two separate filters.
    claimed_mod_indices: set = set()

    for filt in filters:
        best_roll_pct = -1.0   # -1 = no match yet; 0.0 = val exactly at lo (valid)
        best_tier     = None
        found         = False
        best_mod_idx  = -1

        # ── Pseudo mod: sum values across all component stat_ids ────────────
        if filt.stat_id and filt.stat_id.startswith("pseudo."):
            from logic.mod_query import get_mod as _gm
            entry = _gm(filt.stat_id)
            if not entry:
                continue

            total_val = 0.0
            matched_any = False

            if has_extended:
                # OAuth mode: exact stat_id matching
                components = entry.get("pseudo_components", [])
                for mod in all_mods:
                    for comp_id in components:
                        if comp_id in mod.stat_ids:
                            v = _effective_value(mod)
                            if v is not None:
                                total_val += v
                                matched_any = True
            else:
                # Sessid / text mode: keyword matching against mod text
                keywords = entry.get("pseudo_text_keywords", [])
                if keywords:
                    for mod in all_mods:
                        mod_lower = mod.text.lower()
                        # Match if any keyword appears in the mod text
                        for kw in keywords:
                            if kw.lower() in mod_lower:
                                v = _effective_value(mod, text_mode=True)
                                if v is not None:
                                    total_val += v
                                    matched_any = True
                                break   # don't double-count same mod

            if not matched_any and total_val == 0.0:
                # Mod not present on item — passes unless required
                if filt.required:
                    missing_req.append(filt.label)
                continue

            lo, hi = filt.effective_range()
            if lo is None:
                lo = 0.0

            if hi and hi > lo:
                roll_pct = min(1.0, (total_val - lo) / (hi - lo))
                roll_pct = max(-1.0, roll_pct) if total_val < lo else roll_pct
            else:
                roll_pct = 1.0 if total_val >= lo else -1.0

            if roll_pct >= 0.0:
                earned_weight += filt.weight * roll_pct
                matched.append(filt.label)
            elif filt.required:
                missing_req.append(filt.label)
            continue   # skip normal mod-loop for pseudo filters

        # ── Meta filter: structural item properties ─────────────────────────
        if filt.stat_id and filt.stat_id.startswith("meta."):
            # Special case: influence picker — value stored on the filter itself
            if filt.stat_id == "meta.has_influence":
                influence_key = getattr(filt, "meta_influence_value", None) or ""
                if not influence_key:
                    continue
                if influence_key == "any":
                    has_it = bool(any(item.influences.values()))
                else:
                    has_it = bool(item.influences.get(influence_key))
                if has_it:
                    earned_weight += filt.weight
                    matched.append(filt.label)
                elif filt.required:
                    missing_req.append(filt.label)
                continue

            meta_val = _eval_meta_value(item, filt.stat_id)
            lo, hi = filt.effective_range()

            if meta_val is None:
                # Meta value not computable (e.g. needs extended data)
                if filt.required:
                    missing_req.append(filt.label)
                continue

            if lo is None:
                lo = 0.0

            # Boolean meta values (influence/corrupted): 1.0 = present
            # min=1 in the filter means "must have this". min=0 or None = "don't care"
            if hi and hi > lo:
                roll_pct = min(1.0, (meta_val - lo) / (hi - lo))
                roll_pct = max(-1.0, roll_pct) if meta_val < lo else roll_pct
            else:
                roll_pct = 1.0 if meta_val >= lo else -1.0

            if roll_pct >= 0.0:
                earned_weight += filt.weight * roll_pct
                matched.append(filt.label)
            elif filt.required:
                missing_req.append(filt.label)
            continue

        for mod_idx, mod in enumerate(all_mods):
            # Primary: exact stat_id match (extended data available)
            if filt.stat_id and mod.stat_ids:
                if filt.stat_id not in mod.stat_ids:
                    continue
                hit = True
            elif text_mode:
                # SESSID fallback: keyword text match
                hit = _text_matches(mod.text, filt)
            else:
                hit = _text_matches(mod.text, filt)
            if not hit:
                continue

            # Skip mods already claimed by a previous filter (dedup)
            if text_mode and mod_idx in claimed_mod_indices:
                continue

            found = True
            val   = _effective_value(mod, text_mode=text_mode)

            lo, hi = filt.effective_range()

            if val is not None and lo is not None and hi is not None:
                # Hard cap: user-set max (filt.max) is strict. Tier-auto hi is soft (scoring only).
                hard_max = filt.user_set_max  # only non-None if user explicitly set a max
                if val < lo or (hard_max is not None and val > hard_max):
                    roll_pct = -1.0   # out of range → disqualified
                else:
                    spread   = hi - lo
                    roll_pct = ((val - lo) / spread) if spread > 0 else 1.0
                    roll_pct = max(0.0, min(1.0, roll_pct))
            elif val is not None and lo is not None:
                # lo set (possibly from tier DB), no hi at all
                hard_max = filt.user_set_max
                if val < lo or (hard_max is not None and val > hard_max):
                    roll_pct = -1.0
                else:
                    roll_pct = 1.0
            elif val is not None and filt.user_set_max is not None:
                # Only user max set, no lo
                roll_pct = 1.0 if val <= filt.user_set_max else -1.0
            else:
                roll_pct = 1.0

            if roll_pct > best_roll_pct:
                best_roll_pct = roll_pct
                best_mod_idx  = mod_idx
                if val is not None:
                    best_tier = _q_tier_of_value(filt.stat_id, val)

        if found and best_roll_pct >= 0.0:  # 0.0 = val==lo (valid); -1.0 = below lo (invalid)
            # Claim this mod index so no other filter can reuse it (text mode)
            if text_mode and best_mod_idx >= 0:
                claimed_mod_indices.add(best_mod_idx)
            earned_weight += filt.weight * best_roll_pct
            matched.append(filt.label)
            if best_tier is not None:
                matched_tiers[filt.label] = best_tier
        elif filt.required:
            missing_req.append(filt.label)

    if missing_req:
        return ScoreResult(score=0.0, matched=matched,
                           matched_tiers=matched_tiers,
                           missing_required=missing_req)

    score = earned_weight / total_weight if total_weight > 0 else 0.0
    return ScoreResult(score=score, matched=matched,
                       matched_tiers=matched_tiers)


# ── Tier colour mapping ─────────────────────────────────────────────────────

def score_tier(score: float) -> str:
    """Map a 0-1 score to a tier name used for colour lookup."""
    thresholds = TIER_THRESHOLDS
    if   score >= thresholds["tier1"]: return "tier1"
    elif score >= thresholds["tier2"]: return "tier2"
    elif score >= thresholds["tier3"]: return "tier3"
    elif score >= thresholds["tier4"]: return "tier4"
    else:                              return "tier5"


def set_tier_thresholds(t1: float, t2: float, t3: float, t4: float):
    """Allow the UI to push updated thresholds."""
    TIER_THRESHOLDS["tier1"] = t1
    TIER_THRESHOLDS["tier2"] = t2
    TIER_THRESHOLDS["tier3"] = t3
    TIER_THRESHOLDS["tier4"] = t4


def apply_scores(items: list[ParsedItem],
                 filters: list[ModFilter]) -> list[ParsedItem]:
    """Score all items in-place and return the list."""
    for item in items:
        if not item.identified:
            continue
        result            = score_item(item, filters)
        item.score        = result.score
        tier_labels = []
        for label in result.matched:
            t = result.matched_tiers.get(label)
            tier_labels.append(f"{label} [{tier_label(t) if t else '?'}]")
        item.matched_mods = tier_labels
    return items


def apply_scores_slot_aware(items: list[ParsedItem],
                            slot_filters: dict) -> list[ParsedItem]:
    """
    Score items strictly by slot.

    Rules:
    - If slot_filters has specific slots (Body Armour, Boots etc):
        Only items whose equipment_slot matches get a score.
        All other items get score=0 / no outline.
    - "Any" slot filters apply to EVERY item (cross-slot broad search),
        BUT ONLY when no specific slot is added alongside it.
        If specific slots exist, "Any" still applies to all,
        but unmatched specific slots get no outline.

    This means: if you add Body Armour + Boots slots only,
    rings/belts/amulets get NO outline regardless of matching mods.
    """
    has_any    = "Any" in slot_filters
    any_filt   = slot_filters.get("Any", [])
    # Specific slots = everything except "Any"
    spec_slots = {k: v for k, v in slot_filters.items() if k != "Any"}

    for item in items:
        # Always clear first
        item.score       = 0.0
        item.matched_mods = []

        if not item.identified:
            continue

        slot = item.equipment_slot   # "" if unknown

        if spec_slots:
            # Strict mode: item must match one of the defined specific slots
            slot_filt = spec_slots.get(slot, [])
            if not slot_filt and not has_any:
                # This item's slot is not in the filter → no outline
                continue
            if not slot_filt and has_any:
                # Slot not specified but "Any" exists → score against Any only
                relevant = any_filt
            else:
                # Use slot-specific filters + Any filters combined
                relevant = slot_filt + any_filt
        elif has_any:
            # Only "Any" defined → apply to everything
            relevant = any_filt
        else:
            continue

        if not relevant:
            continue

        result = score_item(item, relevant)
        item.score = result.score
        tier_labels = []
        for label in result.matched:
            t = result.matched_tiers.get(label)
            tier_labels.append(f"{label} [{tier_label(t) if t else '?'}]")
        item.matched_mods = tier_labels

    return items
