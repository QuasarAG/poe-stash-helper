from __future__ import annotations
"""
Translate the nested item-base selection state into the final flat list of base
names used by the scan logic.

WHY THIS FILE EXISTS
    The old panel file mixed together:
    - user interface construction
    - click handlers
    - final selection resolution rules

    The resolution rules are domain behaviour. They are not really visual code.
    Pulling them into their own file makes the main panel easier to read and
    makes this logic easier to test later.
"""


def resolve_selected_bases(slot: str, state: dict, base_repository) -> list[str]:
    """Resolve the nested selection state into a sorted list of base names.

    Important rule:
        returning an empty list means "no base restriction" for that slot.
    """
    if not state.get("groups"):
        return []

    result: set[str] = set()
    any_active = False

    for group_key, group_data in state.get("groups", {}).items():
        if not isinstance(group_data, dict) or not group_data.get("active"):
            continue
        any_active = True

        if group_key == "_all":
            result |= group_data.get("bases", set())
            continue

        selected_group_bases = group_data.get("bases", set())
        children = group_data.get("children", {})
        active_children = {
            child_key: child_data
            for child_key, child_data in children.items()
            if child_data.get("active")
        }

        if active_children:
            for child_key, child_data in active_children.items():
                selected_child_bases = child_data.get("bases", set())
                if selected_child_bases:
                    result |= selected_child_bases
                else:
                    if slot == "Main Hand":
                        groups = base_repository.weapon_groups_main
                    elif slot == "Quiver":
                        groups = base_repository.weapon_groups_quiver
                    else:
                        groups = base_repository.weapon_groups_off

                    for group in groups:
                        for base in group["bases"]:
                            if base.get("wtype") == child_key:
                                result.add(base["name"])
        elif selected_group_bases:
            result |= selected_group_bases
        else:
            if slot == "Flask":
                flask_groups = base_repository.get_flask_groups()
                if group_key in flask_groups:
                    result |= {base["name"] for base in flask_groups[group_key]}
                    continue

            stat_bases = base_repository.get_bases_for_slot_attribute(slot, group_key)
            if stat_bases:
                result |= {base["name"] for base in stat_bases}
            else:
                if slot == "Main Hand":
                    weapon_groups = base_repository.weapon_groups_main
                elif slot == "Quiver":
                    weapon_groups = base_repository.weapon_groups_quiver
                else:
                    weapon_groups = base_repository.weapon_groups_off

                found_matching_group = False
                for group in weapon_groups:
                    if group["label"] == group_key:
                        result |= {base["name"] for base in group["bases"]}
                        found_matching_group = True

                if not found_matching_group:
                    result |= {
                        base["name"]
                        for base in base_repository.base_types
                        if base.get("slot") == slot and base.get("wtype", "_all") == group_key
                    }

    if not any_active:
        return []

    return sorted(result)
