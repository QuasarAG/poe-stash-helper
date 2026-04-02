from __future__ import annotations
"""
Helpers that convert a built content widget into the final filter dictionary.

This logic is separated from the widget construction because it is really a
small "state to data" transformation step. Keeping it outside the main widget
class makes the code easier to test and easier to explain.
"""


def build_filter_from_widgets(rarity_buttons: dict, sections: list, widgets: dict) -> dict:
    filters: dict = {}

    selected_rarity = [name for name, button in rarity_buttons.items() if button.isChecked()]
    if selected_rarity:
        filters["rarity"] = selected_rarity

    for section in sections:
        if not section.is_enabled():
            continue

        title = section.title

        if "Weapon" in title:
            filters["weapon"] = {
                key: widgets[key].value()
                for key in [
                    "w_pdps_min",
                    "w_pdps_max",
                    "w_edps_min",
                    "w_edps_max",
                    "w_aps_min",
                    "w_aps_max",
                    "w_crit_min",
                    "w_crit_max",
                ]
                if key in widgets
            }
        elif "Armour" in title:
            filters["armour"] = {
                key: widgets[key].value()
                for key in [
                    "a_arm_min",
                    "a_arm_max",
                    "a_eva_min",
                    "a_eva_max",
                    "a_es_min",
                    "a_es_max",
                    "a_ward_min",
                    "a_ward_max",
                    "a_blk_min",
                    "a_blk_max",
                ]
                if key in widgets
            }
        elif "Socket" in title:
            filters["sockets"] = {
                key: widgets[key].value()
                for key in ["soc_min", "soc_max", "lnk_min", "lnk_max"]
                if key in widgets
            }
        elif "Misc" in title:
            misc_filters = {}
            for key in ["qual_min", "qual_max", "ilvl_min", "ilvl_max"]:
                if key in widgets:
                    misc_filters[key] = widgets[key].value()
            for key in [
                "corrupted",
                "identified",
                "mirrored",
                "split",
                "crafted",
                "veiled",
                "synthesised",
                "fractured",
                "foulborn",
                "searing",
                "eater",
            ]:
                if key in widgets:
                    misc_filters[key] = widgets[key].currentText()
            if misc_filters:
                filters["misc"] = misc_filters
        elif "Memory" in title:
            memory_filters = {}
            for key in ["ms_min", "ms_max"]:
                if key in widgets:
                    memory_filters[key] = widgets[key].value()
            if memory_filters:
                filters["memory_strand"] = memory_filters
        elif "Req" in title:
            requirement_filters = {}
            for key in [
                "req_level_min",
                "req_level_max",
                "req_str_min",
                "req_str_max",
                "req_dex_min",
                "req_dex_max",
                "req_int_min",
                "req_int_max",
            ]:
                if key in widgets:
                    requirement_filters[key] = widgets[key].value()
            if requirement_filters:
                filters["req"] = requirement_filters

    return filters
