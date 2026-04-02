from __future__ import annotations
"""
Build the actual nested item-base tree shown inside the Item Base panel.

This file owns the detailed button hierarchy for one selected slot.
The parent panel owns the long-lived per-slot state. This content widget only
renders and edits one slot at a time.
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from .styles import (
    INSTRUCTION_LABEL_STYLE,
    STAT_COLOURS,
    UI_SCALE,
    base_off_style,
    base_on_style,
    child_button_style,
    group_button_style,
    make_group_button,
    make_stat_button,
    make_weapon_type_button,
    CollapsibleSection,
    FlowWidget,
    wtype_base,
    wtype_stat,
)


class HierarchyContent(QWidget):
    """Build the full hierarchy for one slot and emit state updates."""

    state_changed = pyqtSignal(dict)

    def __init__(self, slot: str, state: dict, base_repository, parent=None):
        super().__init__(parent)
        self._slot = slot
        self._state = state
        self._base_repository = base_repository
        self._base_buttons: dict[str, QPushButton] = {}
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(4, 4, 4, 4)

        if not self._slot:
            label = QLabel("Select a slot from the Loadout bar to browse base types.")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color:#555566;font-size:11px;font-style:italic;padding:20px;")
            layout.addWidget(label)
            layout.addStretch()
            return

        instruction = QLabel("Base types  (expand categories, select bases):")
        instruction.setStyleSheet(INSTRUCTION_LABEL_STYLE)
        layout.addWidget(instruction)

        if self._slot in self._base_repository.slots_weapon_type:
            self._build_weapons(layout, self._slot)
        elif self._slot == "Flask":
            self._build_flask(layout)
        elif self._slot in self._base_repository.slots_no_attribute:
            self._build_flat(layout, self._slot)
        else:
            self._build_armour(layout, self._slot)

        self._summary_label = QLabel("")
        self._summary_label.setWordWrap(True)
        self._summary_label.setStyleSheet("color:#666688;font-size:9px;font-style:italic;")
        layout.addWidget(self._summary_label)
        layout.addStretch()
        self._update_summary()

    def _build_armour(self, layout: QVBoxLayout, slot: str) -> None:
        groups = self._state.setdefault("groups", {})
        for attribute in self._base_repository.get_attributes_for_slot(slot):
            bases = self._base_repository.get_bases_for_slot_attribute(slot, attribute)
            if not bases:
                continue

            group_state = groups.setdefault(attribute, {"active": False, "bases": set()})
            toggle_button = make_stat_button(attribute, group_state["active"], self._base_repository)
            section = CollapsibleSection(toggle_button)
            section.set_expanded(group_state["active"])

            flow = FlowWidget()
            for base in sorted(bases, key=lambda entry: entry["req_ilvl"]):
                flow.add(self._make_base_button(base, group_state["bases"]))
            section.body_layout().addWidget(flow)

            toggle_button.toggled.connect(
                lambda checked, key=attribute, collapsible=section, data=group_state:
                    self._on_group_toggle(key, checked, collapsible, data)
            )
            layout.addWidget(section)

    def _build_weapons(self, layout: QVBoxLayout, slot: str) -> None:
        groups = self._state.setdefault("groups", {})
        if slot == "Main Hand":
            weapon_groups = self._base_repository.weapon_groups_main
        elif slot == "Quiver":
            weapon_groups = self._base_repository.weapon_groups_quiver
        else:
            weapon_groups = self._base_repository.weapon_groups_off

        for group in weapon_groups:
            group_label = group["label"]
            bases = group["bases"]
            is_flat_group = group.get("is_flat", False)
            group_state = groups.setdefault(group_label, {"active": False, "children": {}, "bases": set()})

            group_button = make_group_button(group_label, group_state["active"])
            group_section = CollapsibleSection(group_button)
            group_section.set_expanded(group_state["active"])

            if is_flat_group:
                flow = FlowWidget()
                for base in sorted(bases, key=lambda entry: entry.get("req_ilvl", 0)):
                    flow.add(self._make_base_button(base, group_state["bases"]))
                group_section.body_layout().addWidget(flow)
            else:
                weapon_types = list(dict.fromkeys(base["wtype"] for base in bases if "wtype" in base))
                for weapon_type in weapon_types:
                    weapon_type_bases = [base for base in bases if base.get("wtype") == weapon_type]
                    child_state = group_state["children"].setdefault(weapon_type, {"active": False, "bases": set()})
                    child_button = make_weapon_type_button(weapon_type, child_state["active"])
                    child_section = CollapsibleSection(child_button, indent=12)
                    child_section.set_expanded(child_state["active"])

                    flow = FlowWidget()
                    for base in sorted(weapon_type_bases, key=lambda entry: entry.get("req_ilvl", 0)):
                        flow.add(self._make_base_button(base, child_state["bases"]))
                    child_section.body_layout().addWidget(flow)

                    child_button.toggled.connect(
                        lambda checked, key=weapon_type, collapsible=child_section, data=child_state:
                            self._on_child_toggle(key, checked, collapsible, data)
                    )
                    group_section.body_layout().addWidget(child_section)

            group_button.toggled.connect(
                lambda checked, key=group_label, collapsible=group_section, data=group_state:
                    self._on_group_toggle(key, checked, collapsible, data)
            )
            layout.addWidget(group_section)

    def _build_flask(self, layout: QVBoxLayout) -> None:
        flask_colours = {
            "Life Flask": "#cc4444",
            "Mana Flask": "#4488cc",
            "Hybrid Flask": "#8844cc",
            "Utility Flask": "#44aa88",
        }
        flask_icons = {
            "Life Flask": "♥",
            "Mana Flask": "✦",
            "Hybrid Flask": "⬡",
            "Utility Flask": "⚗",
        }

        groups = self._state.setdefault("groups", {})
        flask_groups = self._base_repository.get_flask_groups()

        for flask_type, bases in flask_groups.items():
            colour = flask_colours.get(flask_type, "#888888")
            icon = flask_icons.get(flask_type, "⬡")
            group_state = groups.setdefault(flask_type, {"active": False, "bases": set()})

            point_size = UI_SCALE["btn_pt"]
            padding = f"{max(2, point_size // 5)}px {max(8, point_size)}px"
            label = f"{icon}  {flask_type}"
            group_button = QPushButton(label)
            group_button.setCheckable(True)
            group_button.setChecked(group_state["active"])
            group_button.setMinimumHeight(max(22, point_size * 2 + 4))

            def build_flask_style(is_checked: bool, *, current_colour: str = colour, current_point_size: int = point_size) -> str:
                current_padding = f"{max(2, current_point_size // 5)}px {max(8, current_point_size)}px"
                if is_checked:
                    return (
                        "QPushButton{" 
                        f"color:#ffffff;background:{current_colour}33;"
                        f"border:2px solid {current_colour};border-radius:5px;"
                        f"padding:{current_padding};font-size:{current_point_size}px;"
                        "font-weight:bold;text-align:left;}"
                    )
                return (
                    "QPushButton{" 
                    f"color:{current_colour}88;background:#0d0d0d;"
                    f"border:1px solid {current_colour}44;border-radius:5px;"
                    f"padding:{current_padding};font-size:{current_point_size}px;"
                    "text-align:left;}"
                )

            group_button.setStyleSheet(build_flask_style(group_state["active"]))
            section = CollapsibleSection(group_button)
            section.set_expanded(group_state["active"])

            flow = FlowWidget()
            for base in bases:
                flow.add(self._make_base_button(base, group_state["bases"]))
            if not bases:
                empty_label = QLabel("  (run Update from RePoE to populate flask list)")
                empty_label.setStyleSheet("color:#444455;font-size:9px;font-style:italic;")
                section.body_layout().addWidget(empty_label)
            else:
                section.body_layout().addWidget(flow)

            def on_flask_group_toggle(
                is_checked,
                *,
                current_state=group_state,
                collapsible=section,
                current_colour=colour,
            ) -> None:
                current_point_size = UI_SCALE["btn_pt"]
                current_state["active"] = is_checked
                collapsible.set_expanded(is_checked)
                header_button = collapsible.header_widget
                if isinstance(header_button, QPushButton):
                    current_padding = f"{max(2, current_point_size // 5)}px {max(8, current_point_size)}px"
                    if is_checked:
                        header_button.setStyleSheet(
                            "QPushButton{" 
                            f"color:#ffffff;background:{current_colour}33;"
                            f"border:2px solid {current_colour};border-radius:5px;"
                            f"padding:{current_padding};font-size:{current_point_size}px;"
                            "font-weight:bold;text-align:left;}"
                        )
                    else:
                        header_button.setStyleSheet(
                            "QPushButton{" 
                            f"color:{current_colour}88;background:#0d0d0d;"
                            f"border:1px solid {current_colour}44;border-radius:5px;"
                            f"padding:{current_padding};font-size:{current_point_size}px;"
                            "text-align:left;}"
                        )
                self._emit()

            group_button.toggled.connect(on_flask_group_toggle)
            layout.addWidget(section)

    def _build_flat(self, layout: QVBoxLayout, slot: str) -> None:
        group_state = self._state.setdefault("groups", {}).setdefault("_all", {"active": True, "bases": set()})
        bases = sorted(
            [base for base in self._base_repository.base_types if base["slot"] == slot],
            key=lambda entry: entry["req_ilvl"],
        )
        flow = FlowWidget()
        for base in bases:
            flow.add(self._make_base_button(base, group_state["bases"]))
        layout.addWidget(flow)

    def _make_base_button(self, base: dict, selected_set: set) -> QPushButton:
        point_size = UI_SCALE["btn_pt"]
        name = base["name"]
        required_item_level = base["req_ilvl"]
        button = QPushButton(f"{name}  ilvl {required_item_level}")
        button.setCheckable(True)
        button.setChecked(name in selected_set)
        button.setToolTip(f"Minimum ilvl {required_item_level}")
        button.setMinimumHeight(max(20, point_size * 2))
        button.setStyleSheet(base_on_style(point_size) if name in selected_set else base_off_style(point_size))
        button.clicked.connect(lambda _, base_name=name, selection=selected_set: self._on_base(base_name, selection))
        self._base_buttons[name] = button
        return button

    def _on_group_toggle(self, key: str, is_checked: bool, collapsible: CollapsibleSection, group_state: dict) -> None:
        point_size = UI_SCALE["btn_pt"]
        group_state["active"] = is_checked
        collapsible.set_expanded(is_checked)

        header_button = collapsible.header_widget
        if isinstance(header_button, QPushButton):
            stat_colour = STAT_COLOURS.get(key)
            padding = f"{max(2, point_size // 5)}px {max(8, point_size)}px"
            if stat_colour:
                if is_checked:
                    header_button.setStyleSheet(
                        "QPushButton{" 
                        f"color:#ffffff;background:{stat_colour}33;border:2px solid {stat_colour};"
                        f"border-radius:5px;padding:{padding};font-size:{point_size}px;"
                        "font-weight:bold;letter-spacing:1px;text-align:left;}"
                    )
                else:
                    header_button.setStyleSheet(
                        "QPushButton{" 
                        "color:#556677;background:#0d1118;border:1px solid #2a3344;"
                        f"border-radius:5px;padding:{padding};font-size:{point_size}px;"
                        "letter-spacing:1px;text-align:left;}"
                    )
            else:
                header_button.setStyleSheet(group_button_style(is_checked, point_size=point_size))
        self._emit()

    def _on_child_toggle(self, key: str, is_checked: bool, collapsible: CollapsibleSection, child_state: dict) -> None:
        point_size = UI_SCALE["btn_pt"]
        child_state["active"] = is_checked
        collapsible.set_expanded(is_checked)

        header_button = collapsible.header_widget
        if isinstance(header_button, QPushButton):
            stat = wtype_stat(key)
            colour = STAT_COLOURS.get(stat, "#7799aa") if stat else "#7799aa"
            header_button.setStyleSheet(child_button_style(is_checked, colour, point_size=point_size))
        self._emit()

    def _on_base(self, name: str, selected_set: set) -> None:
        point_size = UI_SCALE["btn_pt"]
        if name in selected_set:
            selected_set.discard(name)
        else:
            selected_set.add(name)

        button = self._base_buttons.get(name)
        if button is not None:
            button.setStyleSheet(base_on_style(point_size) if name in selected_set else base_off_style(point_size))
        self._update_summary()
        self._emit()

    def _emit(self) -> None:
        self.state_changed.emit(self._state)
        self._update_summary()

    def _update_summary(self) -> None:
        if not hasattr(self, "_summary_label"):
            return
        bases = self._collect_explicit_bases()
        if bases:
            self._summary_label.setText("Selected: " + ", ".join(sorted(bases)))
        else:
            description = self._describe_active()
            self._summary_label.setText(description if description else "No filter — all bases for this slot apply.")

    def _collect_explicit_bases(self) -> set:
        selected: set = set()
        for group_data in self._state.get("groups", {}).values():
            if isinstance(group_data, dict):
                selected |= group_data.get("bases", set())
                for child_data in group_data.get("children", {}).values():
                    selected |= child_data.get("bases", set())
        return selected

    def _describe_active(self) -> str:
        parts = []
        for group_key, group_data in self._state.get("groups", {}).items():
            if not group_data.get("active"):
                continue
            active_children = [
                child_key
                for child_key, child_data in group_data.get("children", {}).items()
                if child_data.get("active")
            ]
            if active_children:
                parts.append(f"{group_key} › " + ", ".join(wtype_base(child) for child in active_children))
            elif group_key != "_all":
                parts.append(group_key)
        return "Active: " + " | ".join(parts) if parts else ""
