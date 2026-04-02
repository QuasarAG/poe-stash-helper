from __future__ import annotations

"""Build the payload used by the stash scan flow.

This service keeps scan-preparation logic out of the Qt window classes.
That makes the user interface easier to read and gives the project one clear
place for the rules that convert saved loadout state into the final scan data.
"""

from dataclasses import dataclass

from logic.mod_scorer import ModFilter
from repositories.loadout_repository import (
    migrate_loadout_to_slot_dict,
    reconstruct_filters_from_active_mod_groups_state,
    save_all_loadouts,
)


@dataclass
class ScanPayload:
    """Container with all scan information.

    `flat_filters` is kept for older code paths.
    `slot_filters` is the modern per-slot structure.
    """

    flat_filters: list[ModFilter]
    slot_filters: dict


ACTIVE_MOD_GROUPS_SUFFIX = "_active_mod_groups"


def build_scan_payload(loadout_tab) -> ScanPayload:
    """Read the current tab state and convert it into scan-ready data."""
    loadout_name = loadout_tab.get_current_loadout_name()
    active_mod_panel = loadout_tab.get_active_mod_panel()

    if not loadout_name:
        return ScanPayload(
            flat_filters=active_mod_panel.get_filters(),
            slot_filters={},
        )

    current_slot = loadout_tab.get_current_slot()
    raw_loadout = migrate_loadout_to_slot_dict(loadout_tab.loadouts.get(loadout_name, {}))

    if current_slot:
        raw_loadout[current_slot] = [filt.to_dict() for filt in active_mod_panel.get_filters()]
        raw_loadout[current_slot + ACTIVE_MOD_GROUPS_SUFFIX] = active_mod_panel.get_active_mod_groups_state()
        loadout_tab.loadouts[loadout_name] = raw_loadout
        save_all_loadouts(loadout_tab.loadouts)

    latest_raw_loadout = migrate_loadout_to_slot_dict(loadout_tab.loadouts.get(loadout_name, {}))

    slot_filters: dict = {}
    for slot_name, filter_list in latest_raw_loadout.items():
        if not slot_name:
            continue
        if slot_name.endswith(ACTIVE_MOD_GROUPS_SUFFIX):
            continue

        if slot_name == current_slot:
            slot_filters[slot_name] = active_mod_panel.get_filters()
            continue

        saved_group_state = latest_raw_loadout.get(slot_name + ACTIVE_MOD_GROUPS_SUFFIX)
        if saved_group_state:
            slot_filters[slot_name] = reconstruct_filters_from_active_mod_groups_state(saved_group_state)
        else:
            slot_filters[slot_name] = [ModFilter.from_dict(entry) for entry in filter_list]

    flat_filter_dicts = [
        entry
        for slot_name, filter_list in latest_raw_loadout.items()
        if slot_name
        and not slot_name.endswith(ACTIVE_MOD_GROUPS_SUFFIX)
        for entry in filter_list
    ]

    return ScanPayload(
        flat_filters=[ModFilter.from_dict(entry) for entry in flat_filter_dicts],
        slot_filters=slot_filters,
    )
