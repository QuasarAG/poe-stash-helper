"""
ui/tabs/scan_filters_tab.py
─────────────────────────────────────────────────────────────────────────────
PURPOSE
    Builds and manages the "Scan & Filters" tab in the MainWindow.

    This tab contains three main areas:

    1. loadout selector row
    2. slot bar for the current loadout
    3. sub-tabs for item bases, item properties, and mod stats

WHY THIS FILE WAS REFACTORED AGAIN
    This file used to build every small user-interface row inline. That made
    the tab harder to read because it mixed:

    - high-level loadout / slot behaviour
    - low-level button layout code

    The loadout selector row now lives in ui/widgets/loadout_selector_bar.py.
    The slot bar now lives in ui/widgets/slot_bar.py.

    This file now focuses more on the behaviour of the tab itself.
"""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QTabWidget,
    QMessageBox, QInputDialog,
)

from logic.mod_scorer import ModFilter
from repositories.loadout_repository import (
    load_all_loadouts,
    save_all_loadouts,
    migrate_loadout_to_slot_dict,
)
from ui.shared import ITEM_SLOTS, make_scrollable
from ui.widgets.loadout_selector_bar import LoadoutSelectorBar
from ui.widgets.slot_bar import SlotBar

ACTIVE_MOD_GROUPS_SUFFIX = "_active_mod_groups"


class ScanFiltersTab(QWidget):
    """Tab that owns loadouts, slots, and all scan-related filter panels."""

    slot_activated = pyqtSignal(str)
    loadout_selection_changed = pyqtSignal()
    scan_requested = pyqtSignal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._loadouts: dict = load_all_loadouts()
        self._current_slot_name: str = ""
        self._build_layout()

    def _build_layout(self) -> None:
        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(6)

        main_layout.addWidget(self._build_loadout_group())

        self._no_slot_prompt = QLabel(
            "⬆  Use  ＋ Add Slot  above to add an equipment slot.\n"
            "Mod search and item properties become available once a slot is added."
        )
        self._no_slot_prompt.setAlignment(Qt.AlignCenter)
        self._no_slot_prompt.setStyleSheet(
            "color:#556; font-size:11px; font-style:italic;"
            " background:#101018; border:1px solid #222236;"
            " border-radius:4px; padding:24px;"
        )
        main_layout.addWidget(self._no_slot_prompt, stretch=1)

        self._sub_tabs = self._build_sub_tabs()
        self._sub_tabs.setVisible(False)
        main_layout.addWidget(self._sub_tabs, stretch=1)

        scroll = make_scrollable(content_widget)
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(scroll)

        self._refresh_loadout_dropdown()
        self._on_loadout_dropdown_changed(self._loadout_selector.current_index())

    def _build_loadout_group(self) -> QGroupBox:
        group_box = QGroupBox("Loadouts")
        group_layout = QVBoxLayout(group_box)
        group_layout.setSpacing(4)

        self._loadout_selector = LoadoutSelectorBar()
        self._loadout_selector.new_requested.connect(self._on_new_loadout_clicked)
        self._loadout_selector.delete_requested.connect(self._on_delete_loadout_clicked)
        self._loadout_selector.selection_changed.connect(self._on_loadout_dropdown_changed)
        group_layout.addWidget(self._loadout_selector)

        self._slot_bar = SlotBar()
        self._slot_bar.slot_clicked.connect(self._on_slot_bar_slot_clicked)
        self._slot_bar.slot_remove_requested.connect(self._on_remove_slot_clicked)
        self._slot_bar.add_slot_requested.connect(self._on_add_slot_button_clicked)
        self._slot_bar.add_slot_selected.connect(self._on_add_slot)
        group_layout.addWidget(self._slot_bar)
        return group_box

    def _build_sub_tabs(self) -> QTabWidget:
        sub_tabs = QTabWidget()
        sub_tabs.setStyleSheet(
            "QTabBar::tab { background:#222238; padding:4px 12px; }"
            "QTabBar::tab:selected { background:#2a2a4e;"
            "  border-bottom:2px solid #5577ff; }"
        )

        from ui.panels.item_base_filter import ItemBaseFilterPanel
        self._item_base_panel = ItemBaseFilterPanel()
        self._item_base_panel.selected_bases_changed.connect(self._on_base_selection_changed)
        sub_tabs.addTab(self._item_base_panel, "Item Base")
        self._watch_base_types_json()

        from ui.panels.item_property_filter import ItemPropertyFilterPanel
        self._item_property_panel = ItemPropertyFilterPanel()
        self._item_property_panel.property_changed.connect(self._on_item_property_changed)
        sub_tabs.addTab(self._item_property_panel, "Item Properties")

        from ui.panels.mod_search import ModSearchPanel
        self._mod_search_panel = ModSearchPanel()
        sub_tabs.addTab(self._mod_search_panel, "Mod Stats")

        return sub_tabs

    def _watch_base_types_json(self) -> None:
        import pathlib
        from PyQt5.QtCore import QFileSystemWatcher

        json_path = str(pathlib.Path(__file__).resolve().parents[2] / "data" / "base_types.json")
        self._base_json_watcher = QFileSystemWatcher([json_path])
        self._base_json_watcher.fileChanged.connect(lambda path: self._schedule_base_types_reload(path))

    def _schedule_base_types_reload(self, path: str) -> None:
        from PyQt5.QtCore import QTimer
        try:
            self._base_json_watcher.addPath(path)
        except Exception:
            pass
        QTimer.singleShot(300, lambda p=path: self._reload_base_types(p))

    def _reload_base_types(self, _path: str) -> None:
        try:
            from repositories.base_repository import get_default_base_repository

            get_default_base_repository().reload()
            slot = self._current_slot_name
            if slot:
                self._item_base_panel.set_slot(slot)
                self.get_active_mod_panel().set_slot(slot)
            print("[scan_filters_tab] base_types.json auto-reloaded.")
        except Exception as error:
            print(f"[scan_filters_tab] base_types reload failed: {error}")

    @property
    def loadouts(self) -> dict:
        return self._loadouts

    def get_active_mod_panel(self):
        return self._mod_search_panel.active_mod_panel

    def get_mod_search_panel(self):
        return self._mod_search_panel

    def get_item_base_panel(self):
        return self._item_base_panel

    def get_item_property_panel(self):
        return self._item_property_panel

    def refresh_mod_search_results(self) -> None:
        """Re-run the current mod search text after new data loads."""
        self._mod_search_panel.refresh_results()

    def apply_font_sizes(self, mods_pt: int, props_pt: int, button_pt: int) -> None:
        """Apply font-size changes to child panels without exposing their internals."""
        self._mod_search_panel.apply_font_sizes(mods_pt)
        self._item_property_panel.setStyleSheet(
            f"QLabel {{ font-size:{props_pt}px; }}"
            f"QCheckBox {{ font-size:{props_pt}px; }}"
            f"QSpinBox {{ font-size:{props_pt}px; }}"
            f"QDoubleSpinBox {{ font-size:{props_pt}px; }}"
            f"QComboBox {{ font-size:{props_pt}px; }}"
        )
        try:
            from ui.panels.item_base_filter import UI_SCALE
            if UI_SCALE.get("btn_pt") != button_pt:
                UI_SCALE["btn_pt"] = button_pt
                slot = self.get_current_slot()
                if slot:
                    self._item_base_panel.set_slot(slot)
                    self.get_active_mod_panel().set_slot(slot)
        except Exception:
            pass

    def get_current_slot(self) -> str:
        return self._current_slot_name

    def get_all_base_selections(self) -> dict:
        try:
            return self._item_base_panel.get_all_selections()
        except AttributeError:
            return {}

    def get_item_property_filters(self) -> dict:
        try:
            return self._item_property_panel.get_all_slot_filters()
        except AttributeError:
            return {}

    def set_search_enabled(self, enabled: bool) -> None:
        self._mod_search_panel.set_search_enabled(enabled)
        self._sub_tabs.setVisible(enabled)
        self._no_slot_prompt.setVisible(not enabled)

    def set_add_slot_button_visible(self, visible: bool) -> None:
        self._slot_bar.set_add_slot_button_visible(visible)

    def _refresh_loadout_dropdown(self, selected_name: str = "") -> None:
        self._loadout_selector.refresh_names(sorted(self._loadouts.keys()), selected_name)

    def get_current_loadout_name(self) -> str:
        name = self._loadout_selector.current_name()
        return name if (name and not name.startswith("--") and name in self._loadouts) else ""

    def has_real_loadout(self) -> bool:
        return bool(self.get_current_loadout_name())

    def has_slots(self) -> bool:
        name = self.get_current_loadout_name()
        if not name:
            return False
        raw = migrate_loadout_to_slot_dict(self._loadouts.get(name, {}))
        return any(slot in raw for slot in ITEM_SLOTS)

    def _get_current_loadout_raw(self) -> dict:
        name = self.get_current_loadout_name()
        if not name:
            return {}
        return migrate_loadout_to_slot_dict(self._loadouts.get(name, {}))

    def _save_current_slot_state(self) -> None:
        """Save the visible slot panels back into the selected loadout."""
        loadout_name = self.get_current_loadout_name()
        slot_name = self._current_slot_name
        if not loadout_name or not slot_name:
            return
        raw = self._get_current_loadout_raw()
        active_mod_panel = self.get_active_mod_panel()
        raw[slot_name] = [filt.to_dict() for filt in active_mod_panel.get_filters()]
        raw[slot_name + ACTIVE_MOD_GROUPS_SUFFIX] = active_mod_panel.get_active_mod_groups_state()
        self._loadouts[loadout_name] = raw
        save_all_loadouts(self._loadouts)

    def _on_new_loadout_clicked(self) -> None:
        name, accepted = QInputDialog.getText(self, "New Loadout", "Loadout name:")
        if not accepted or not name.strip():
            return

        name = name.strip()
        if name in self._loadouts:
            QMessageBox.information(
                self,
                "Already exists",
                f"A loadout named '{name}' already exists. Choose a different name.",
            )
            return

        self._loadouts[name] = {}
        save_all_loadouts(self._loadouts)

        self._refresh_loadout_dropdown(selected_name=name)
        self._current_slot_name = ""
        self._on_loadout_dropdown_changed(self._loadout_selector.current_index())

    def _on_delete_loadout_clicked(self) -> None:
        name = self.get_current_loadout_name()
        if not name:
            return

        reply = QMessageBox.question(
            self,
            "Delete Loadout",
            f"Delete loadout '{name}' (all slots)?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        del self._loadouts[name]
        save_all_loadouts(self._loadouts)

        self._current_slot_name = ""
        self._refresh_loadout_dropdown()
        self._on_loadout_dropdown_changed(self._loadout_selector.current_index())

    def _on_loadout_dropdown_changed(self, _index: int) -> None:
        name = self.get_current_loadout_name()

        if not name:
            self._slot_bar.set_add_slot_button_visible(False)
            self._slot_bar.rebuild("", [])
            self.get_active_mod_panel().clear_all()
            self.set_search_enabled(False)
            self.loadout_selection_changed.emit()
            return

        raw = migrate_loadout_to_slot_dict(self._loadouts[name])
        slots = [slot_name for slot_name in ITEM_SLOTS if slot_name in raw]
        first_slot = slots[0] if slots else ""

        # Important: set visibility BEFORE rebuilding the flow widget.
        self._slot_bar.set_add_slot_button_visible(True)
        self._slot_bar.rebuild(first_slot, slots)
        self.get_active_mod_panel().clear_all()

        if first_slot:
            self._load_slot_into_panel(first_slot, raw)
        else:
            self.set_search_enabled(False)

        self.loadout_selection_changed.emit()

    def _on_add_slot_button_clicked(self) -> None:
        loadout_name = self.get_current_loadout_name()
        if not loadout_name:
            QMessageBox.information(self, "No loadout", "Select or save a loadout first, then add item slots.")
            return

        raw = self._get_current_loadout_raw()
        used_slots = {key for key in raw.keys() if not key.endswith(ACTIVE_MOD_GROUPS_SUFFIX)}
        available_slots = [slot_name for slot_name in ITEM_SLOTS if slot_name not in used_slots]
        self._slot_bar.show_add_slot_menu(available_slots)

    def _on_add_slot(self, slot_name: str) -> None:
        if not slot_name:
            return
        loadout_name = self.get_current_loadout_name()
        if not loadout_name:
            QMessageBox.information(self, "No loadout", "Select or save a loadout first, then add item slots.")
            return

        raw = self._get_current_loadout_raw()
        raw[slot_name] = raw.get(slot_name, [])
        self._loadouts[loadout_name] = raw
        save_all_loadouts(self._loadouts)

        slots = [slot for slot in ITEM_SLOTS if slot in raw]
        self._slot_bar.rebuild(slot_name, slots)
        self._activate_slot(slot_name, raw)
        self.loadout_selection_changed.emit()

    def _on_remove_slot_clicked(self, slot_name: str) -> None:
        loadout_name = self.get_current_loadout_name()
        if not loadout_name:
            return

        raw = self._get_current_loadout_raw()
        raw.pop(slot_name, None)
        raw.pop(slot_name + ACTIVE_MOD_GROUPS_SUFFIX, None)

        try:
            self._item_base_panel.clear_slot(slot_name)
        except AttributeError:
            pass
        try:
            self._item_property_panel.clear_slot(slot_name)
        except AttributeError:
            pass

        self._loadouts[loadout_name] = raw
        save_all_loadouts(self._loadouts)

        remaining_slots = [slot for slot in ITEM_SLOTS if slot in raw]
        first_remaining = remaining_slots[0] if remaining_slots else ""

        self._slot_bar.rebuild(first_remaining, remaining_slots)
        self.get_active_mod_panel().clear_all()

        if first_remaining:
            self._load_slot_into_panel(first_remaining, raw)
            self._set_child_panel_slot(first_remaining)
        else:
            self.set_search_enabled(False)
            self._set_child_panel_slot("")
            try:
                self._mod_search_panel.set_slot("")
            except AttributeError:
                pass

        self.loadout_selection_changed.emit()

    def _on_slot_bar_slot_clicked(self, slot_name: str) -> None:
        self._save_current_slot_state()
        self._current_slot_name = slot_name
        self._slot_bar.set_active_slot(slot_name)
        raw = self._get_current_loadout_raw()
        self._activate_slot(slot_name, raw)

    def _activate_slot(self, slot_name: str, raw_loadout: dict) -> None:
        self._current_slot_name = slot_name
        self._slot_bar.set_active_slot(slot_name)
        self._load_slot_into_panel(slot_name, raw_loadout)
        self.set_search_enabled(bool(slot_name))
        self._set_child_panel_slot(slot_name)
        try:
            self._mod_search_panel.set_slot(slot_name)
        except AttributeError:
            pass
        self.slot_activated.emit(slot_name)

    def _set_child_panel_slot(self, slot_name: str) -> None:
        try:
            self._item_base_panel.set_slot(slot_name)
            self.get_active_mod_panel().set_slot(slot_name)
        except AttributeError:
            pass
        try:
            self._item_property_panel.set_slot(slot_name)
        except AttributeError:
            pass

    def _load_slot_into_panel(self, slot_name: str, raw_loadout: dict) -> None:
        self.get_active_mod_panel().clear_all()

        active_mod_groups_state = raw_loadout.get(slot_name + ACTIVE_MOD_GROUPS_SUFFIX)
        if active_mod_groups_state:
            self.get_active_mod_panel().load_active_mod_groups_state(active_mod_groups_state)
        else:
            for filter_dict in raw_loadout.get(slot_name, []):
                self.get_active_mod_panel().add_mod(ModFilter.from_dict(filter_dict))

    def _on_base_selection_changed(self, _slot: str, _bases: list) -> None:
        self.loadout_selection_changed.emit()

    def _on_item_property_changed(self) -> None:
        self.loadout_selection_changed.emit()
