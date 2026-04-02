from __future__ import annotations

"""
repositories/loadout_repository.py
─────────────────────────────────────────────────────────────────────────────
Read and write saved loadouts.

WHY THIS FILE EXISTS
    User interface widgets should not be the main place that knows where the
    loadout JSON file lives on disk or how it is saved.

    This repository gives the project one place for that responsibility.
"""

import json
from pathlib import Path

from models import ActiveModBehaviour

LOADOUTS_FILE_PATH = Path(__file__).resolve().parent.parent / "data" / "loadouts.json"


def load_all_loadouts() -> dict:
    """Load every saved loadout from disk. Return an empty dict on failure."""
    if LOADOUTS_FILE_PATH.exists():
        try:
            with open(LOADOUTS_FILE_PATH, encoding="utf-8") as file_handle:
                return json.load(file_handle)
        except Exception:
            # Deliberately return a safe default because this function is used
            # by startup UI code. A broken file should not crash the whole app.
            pass
    return {}


def save_all_loadouts(loadouts: dict) -> None:
    """Persist the full loadout dictionary to disk."""
    LOADOUTS_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOADOUTS_FILE_PATH, "w", encoding="utf-8") as file_handle:
        json.dump(loadouts, file_handle, indent=2)


def migrate_loadout_to_slot_dict(raw_loadout_data) -> dict:
    """
    Normalize older or unexpected loadout shapes into the slot-dict format.

    This project is still evolving, so this helper acts like a tiny adapter
    layer between old saved data and the current expected structure.
    """
    if isinstance(raw_loadout_data, list):
        return {}
    if isinstance(raw_loadout_data, dict):
        return {
            key: value
            for key, value in raw_loadout_data.items()
            if key != "All Items"
        }
    return {}


def reconstruct_filters_from_active_mod_groups_state(groups_state: list[dict]) -> list:
    """
    Rebuild ModFilter objects from saved active mod group state.

    Why reconstruction is needed:
        the user interface can save advanced active mod group behaviour such as AND / NOT / IF / COUNT.
        When another slot is not currently visible on screen, we still need a way
        to rebuild the effective ModFilter list for scanning.
    """
    from logic.mod_scorer import ModFilter

    reconstructed_filters = []

    for group_dict in groups_state:
        group_behaviour = ActiveModBehaviour(group_dict.get("behaviour", ActiveModBehaviour.AND.value))
        group_enabled = group_dict.get("enabled", True)
        count_min = group_dict.get("count_min", 1)
        count_max = group_dict.get("count_max", 0)

        if not group_enabled:
            continue

        for mod_dict in group_dict.get("mods", []):
            if not mod_dict.get("enabled", True):
                continue

            mod_filter = ModFilter(
                stat_id=mod_dict.get("stat_id", ""),
                label=mod_dict.get("label", ""),
                min=mod_dict.get("min"),
                max=mod_dict.get("max"),
                weight=float(mod_dict.get("weight", 1.0)),
            )
            mod_filter._group_behaviour = group_behaviour
            mod_filter._count_min = count_min
            mod_filter._count_max = count_max
            mod_filter.count_min = count_min
            mod_filter.count_max = count_max
            reconstructed_filters.append(mod_filter)

    return reconstructed_filters

