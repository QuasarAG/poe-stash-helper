from __future__ import annotations
"""
Slot-specific content widget for item property filtering.

This widget is recreated whenever the selected slot changes. That is a simple
and beginner-friendly approach because it avoids stale child widgets and stale
layout state. The panel keeps the saved per-slot data, and this content widget
just builds one current view from that data.
"""

from PyQt5.QtCore import Qt, pyqtSignal
from models import ItemRarity
from PyQt5.QtWidgets import QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget, QHBoxLayout

from .auto_layout import AutoSectionLayout
from .constants import TWO_COLUMN_THRESHOLD, sections_for_slot
from .filter_state import build_filter_from_widgets
from .widgets import (
    Section,
    add_boolean_row,
    add_min_max_row,
    horizontal_separator,
    make_double_spinbox,
    make_spinbox,
    make_yes_no_combo,
    rarity_button_style,
)


class ItemPropertyContent(QWidget):
    changed = pyqtSignal(dict)

    def __init__(self, slot: str, saved_state: dict, parent=None):
        super().__init__(parent)
        self._slot = slot
        self._widgets: dict = {}
        self._sections: list[Section] = []
        self._rarity_buttons: dict[ItemRarity, QPushButton] = {}
        self._build(slot, saved_state)

    def _build(self, slot: str, saved_state: dict) -> None:
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        root_layout = QVBoxLayout(self)
        root_layout.setSpacing(4)
        root_layout.setContentsMargins(6, 6, 6, 6)

        if not slot:
            empty_label = QLabel("Select a slot in the Loadout bar to set item property filters.")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet(
                "color:#555566;font-size:11px;font-style:italic;padding:20px;"
            )
            root_layout.addWidget(empty_label)
            root_layout.addStretch()
            return

        active_sections = sections_for_slot(slot)
        widgets = self._widgets

        if "rarity" in active_sections:
            self._build_rarity_area(root_layout, saved_state)

        built_sections: list[Section] = []

        if "weapon" in active_sections:
            built_sections.append(self._build_weapon_section(saved_state, widgets))
        if "armour" in active_sections:
            built_sections.append(self._build_armour_section(saved_state, widgets))
        if "socket" in active_sections:
            built_sections.append(self._build_socket_section(saved_state, widgets))
        if "misc_quality" in active_sections or "misc_other" in active_sections:
            built_sections.append(self._build_misc_section(saved_state, widgets, active_sections))
        if "requirements" in active_sections:
            built_sections.append(self._build_requirements_section(saved_state, widgets))
        if "memory_strand" in active_sections:
            built_sections.append(self._build_memory_strand_section(saved_state, widgets))

        if built_sections:
            self._sections.extend(built_sections)
            auto_layout = AutoSectionLayout(built_sections, threshold=TWO_COLUMN_THRESHOLD)
            root_layout.addWidget(auto_layout)
            root_layout.addStretch()

    def _build_rarity_area(self, root_layout: QVBoxLayout, saved_state: dict) -> None:
        header = QLabel("ITEM RARITY")
        header.setStyleSheet(
            "color:#8888aa;font-size:9px;font-weight:bold;letter-spacing:1px;"
        )

        rarity_row = QWidget()
        rarity_layout = QHBoxLayout(rarity_row)
        rarity_layout.setSpacing(5)
        rarity_layout.setContentsMargins(0, 0, 0, 0)

        saved_rarity = saved_state.get("rarity", [])
        for rarity in ItemRarity:
            button = QPushButton(rarity.value)
            button.setCheckable(True)
            is_active = rarity.value in saved_rarity
            button.setChecked(is_active)
            button.setStyleSheet(rarity_button_style(rarity, is_active))
            button.clicked.connect(lambda _, rarity_name=rarity: self._on_rarity_clicked(rarity_name))
            rarity_layout.addWidget(button)
            self._rarity_buttons[rarity] = button

        rarity_layout.addStretch()
        root_layout.addWidget(header)
        root_layout.addWidget(rarity_row)
        root_layout.addWidget(horizontal_separator())

    def _build_weapon_section(self, saved_state: dict, widgets: dict) -> Section:
        section = Section("Weapon Filters")
        weapon_state = saved_state.get("weapon", {})
        rows = [
            ("Physical DPS", "w_pdps_min", "w_pdps_max"),
            ("Elemental DPS", "w_edps_min", "w_edps_max"),
            ("Attacks/Sec", "w_aps_min", "w_aps_max"),
            ("Critical %", "w_crit_min", "w_crit_max"),
        ]
        for label, low_key, high_key in rows:
            low_widget = make_double_spinbox()
            high_widget = make_double_spinbox()
            low_widget.setValue(weapon_state.get(low_key, 0))
            high_widget.setValue(weapon_state.get(high_key, 0))
            widgets[low_key] = low_widget
            widgets[high_key] = high_widget
            low_widget.valueChanged.connect(self._emit)
            high_widget.valueChanged.connect(self._emit)
            add_min_max_row(section, label, low_widget, high_widget)
        section.changed.connect(self._emit)
        if "weapon" in saved_state:
            section.set_enabled(True)
        return section

    def _build_armour_section(self, saved_state: dict, widgets: dict) -> Section:
        section = Section("Armour Filters")
        armour_state = saved_state.get("armour", {})
        rows = [
            ("Armour", "a_arm_min", "a_arm_max"),
            ("Evasion", "a_eva_min", "a_eva_max"),
            ("Energy Shield", "a_es_min", "a_es_max"),
            ("Ward", "a_ward_min", "a_ward_max"),
            ("Block %", "a_blk_min", "a_blk_max"),
        ]
        for label, low_key, high_key in rows:
            low_widget = make_spinbox()
            high_widget = make_spinbox()
            low_widget.setValue(armour_state.get(low_key, 0))
            high_widget.setValue(armour_state.get(high_key, 0))
            widgets[low_key] = low_widget
            widgets[high_key] = high_widget
            low_widget.valueChanged.connect(self._emit)
            high_widget.valueChanged.connect(self._emit)
            add_min_max_row(section, label, low_widget, high_widget)
        section.changed.connect(self._emit)
        if "armour" in saved_state:
            section.set_enabled(True)
        return section

    def _build_socket_section(self, saved_state: dict, widgets: dict) -> Section:
        section = Section("Socket Filters")
        socket_state = saved_state.get("sockets", {})
        rows = [
            ("Sockets", "soc_min", "soc_max"),
            ("Links", "lnk_min", "lnk_max"),
        ]
        for label, low_key, high_key in rows:
            low_widget = make_spinbox(0, 6)
            high_widget = make_spinbox(0, 6)
            low_widget.setValue(socket_state.get(low_key, 0))
            high_widget.setValue(socket_state.get(high_key, 0))
            widgets[low_key] = low_widget
            widgets[high_key] = high_widget
            low_widget.valueChanged.connect(self._emit)
            high_widget.valueChanged.connect(self._emit)
            add_min_max_row(section, label, low_widget, high_widget)
        section.changed.connect(self._emit)
        if "sockets" in saved_state:
            section.set_enabled(True)
        return section

    def _build_misc_section(self, saved_state: dict, widgets: dict, active_sections: set[str]) -> Section:
        section = Section("Misc Filters")
        misc_state = saved_state.get("misc", {})

        if "misc_quality" in active_sections:
            quality_low = make_spinbox(0, 30)
            quality_high = make_spinbox(0, 30)
            quality_low.setValue(misc_state.get("qual_min", 0))
            quality_high.setValue(misc_state.get("qual_max", 0))
            widgets["qual_min"] = quality_low
            widgets["qual_max"] = quality_high
            quality_low.valueChanged.connect(self._emit)
            quality_high.valueChanged.connect(self._emit)
            add_min_max_row(section, "Quality", quality_low, quality_high)

        if "misc_other" in active_sections:
            item_level_low = make_spinbox(0, 100)
            item_level_high = make_spinbox(0, 100)
            item_level_low.setValue(misc_state.get("ilvl_min", 0))
            item_level_high.setValue(misc_state.get("ilvl_max", 0))
            widgets["ilvl_min"] = item_level_low
            widgets["ilvl_max"] = item_level_high
            item_level_low.valueChanged.connect(self._emit)
            item_level_high.valueChanged.connect(self._emit)
            add_min_max_row(section, "Item Level", item_level_low, item_level_high)

            boolean_rows = [
                ("Corrupted", "corrupted"),
                ("Identified", "identified"),
                ("Mirrored", "mirrored"),
                ("Split", "split"),
                ("Crafted", "crafted"),
                ("Veiled", "veiled"),
                ("Synthesised", "synthesised"),
                ("Fractured", "fractured"),
                ("Foulborn", "foulborn"),
                ("Searing Exarch", "searing"),
                ("Eater of Worlds", "eater"),
            ]
            for label, key in boolean_rows:
                combo = make_yes_no_combo()
                combo.setCurrentText(misc_state.get(key, "Any"))
                combo.currentIndexChanged.connect(self._emit)
                widgets[key] = combo
                add_boolean_row(section, label, combo)

        section.changed.connect(self._emit)
        if "misc" in saved_state:
            section.set_enabled(True)
        return section

    def _build_requirements_section(self, saved_state: dict, widgets: dict) -> Section:
        section = Section("Requirements")
        requirement_state = saved_state.get("req", {})
        rows = [
            ("req_level_min", "req_level_max", "Level"),
            ("req_str_min", "req_str_max", "Strength"),
            ("req_dex_min", "req_dex_max", "Dexterity"),
            ("req_int_min", "req_int_max", "Intelligence"),
        ]
        for low_key, high_key, label in rows:
            low_widget = make_spinbox()
            high_widget = make_spinbox()
            low_widget.setValue(requirement_state.get(low_key, 0))
            high_widget.setValue(requirement_state.get(high_key, 0))
            widgets[low_key] = low_widget
            widgets[high_key] = high_widget
            low_widget.valueChanged.connect(self._emit)
            high_widget.valueChanged.connect(self._emit)
            add_min_max_row(section, label, low_widget, high_widget)
        section.changed.connect(self._emit)
        if "req" in saved_state:
            section.set_enabled(True)
        return section

    def _build_memory_strand_section(self, saved_state: dict, widgets: dict) -> Section:
        section = Section("Memory Strands")
        memory_state = saved_state.get("memory_strand", {})
        low_widget = make_spinbox(0, 9999)
        high_widget = make_spinbox(0, 9999)
        low_widget.setValue(memory_state.get("ms_min", 0))
        high_widget.setValue(memory_state.get("ms_max", 0))
        widgets["ms_min"] = low_widget
        widgets["ms_max"] = high_widget
        low_widget.valueChanged.connect(self._emit)
        high_widget.valueChanged.connect(self._emit)
        add_min_max_row(section, "Memory Strands", low_widget, high_widget)
        section.changed.connect(self._emit)
        if "memory_strand" in saved_state:
            section.set_enabled(True)
        return section

    def _on_rarity_clicked(self, rarity_name: ItemRarity) -> None:
        button = self._rarity_buttons[rarity_name]
        button.setStyleSheet(rarity_button_style(rarity_name, button.isChecked()))
        self._emit()

    def _emit(self, *_args) -> None:
        self.changed.emit(self.get_filter())

    def get_filter(self) -> dict:
        return build_filter_from_widgets(
            rarity_buttons=self._rarity_buttons,
            sections=self._sections,
            widgets=self._widgets,
        )
