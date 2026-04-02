from __future__ import annotations
"""Top-level active mod panel.

This panel owns the active mod groups for the current slot.
"""

import copy
from typing import List

from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QHBoxLayout, QPushButton, QMenu

from logic.mod_scorer import ModFilter

from models import ActiveModBehaviour
from .common import BEHAVIOUR_TIPS
from .active_mod_group import ActiveModGroup
from .active_mod_row import ActiveModRow


class ActiveModPanel(QWidget):
    """Container that holds every active-mod group for the current slot."""

    active_mods_changed = pyqtSignal(list)

    def __init__(self, slot: str = "", parent=None):
        super().__init__(parent)
        self._slot = slot
        self._groups: List[ActiveModGroup] = []
        self._build()
        self._add_group(ActiveModBehaviour.AND)

    def _build(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setSpacing(0)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        self._groups_container = QWidget()
        self._groups_layout = QVBoxLayout(self._groups_container)
        self._groups_layout.setSpacing(4)
        self._groups_layout.setContentsMargins(2, 2, 2, 2)
        self._groups_layout.addStretch()
        scroll.setWidget(self._groups_container)
        outer_layout.addWidget(scroll, 1)

        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(4, 4, 4, 2)
        footer_layout.setSpacing(4)

        add_group_button = QPushButton("+ Add Active Mod Group  ▾")
        add_group_button.setStyleSheet(
            "QPushButton{background:#1e2e1e;border:1px solid #446644;border-radius:4px;"
            "color:#88cc88;padding:4px 14px;font-weight:bold;}"
            "QPushButton:hover{background:#264426;color:#aaffaa;}"
            "QPushButton::menu-indicator{width:0;}"
        )
        add_group_button.setToolTip("Choose a rule type and add a new active mod group")

        def show_add_menu() -> None:
            menu = QMenu(add_group_button)
            menu.setStyleSheet(
                "QMenu{background:#1a1a2a;border:1px solid #444466;color:#ccccff;font-size:9px;padding:2px;}"
                "QMenu::item{padding:4px 18px;}"
                "QMenu::item:selected{background:#2a2a5a;}"
            )
            for behaviour, tooltip in BEHAVIOUR_TIPS.items():
                action = menu.addAction(behaviour)
                action.setToolTip(tooltip)
                action.triggered.connect(lambda checked=False, b=behaviour: self._add_group(b))
            menu.exec_(add_group_button.mapToGlobal(QPoint(0, add_group_button.height())))

        add_group_button.clicked.connect(show_add_menu)
        footer_layout.addWidget(add_group_button)
        footer_layout.addStretch()

        clear_all_button = QPushButton("Clear All")
        clear_all_button.setObjectName("danger")
        clear_all_button.setStyleSheet(
            "QPushButton{background:#2a1010;border:1px solid #663333;border-radius:4px;"
            "color:#cc6666;padding:4px 10px;}"
            "QPushButton:hover{background:#3a1515;color:#ff8888;}"
        )
        clear_all_button.setToolTip("Remove all active mods from all groups")
        clear_all_button.clicked.connect(self.clear_all)
        footer_layout.addWidget(clear_all_button)

        outer_layout.addLayout(footer_layout)

    def _add_group(self, behaviour: ActiveModBehaviour = ActiveModBehaviour.AND) -> ActiveModGroup:
        group = ActiveModGroup(behaviour, self._slot)
        group._panel_ref = self
        group.changed.connect(self._on_changed)
        group.remove_requested.connect(self._on_remove_group)
        self._groups.append(group)
        index_before_stretch = self._groups_layout.count() - 1
        self._groups_layout.insertWidget(index_before_stretch, group)
        return group

    def _destroy_all_groups(self) -> None:
        for group in list(self._groups):
            self._groups.remove(group)
            self._groups_layout.removeWidget(group)
            group.hide()
            group.setParent(None)
            group.deleteLater()
        self._groups.clear()
        self._add_group(ActiveModBehaviour.AND)

    def _on_remove_group(self, group: ActiveModGroup) -> None:
        if len(self._groups) == 1:
            self._groups[0].clear()
        else:
            self._groups.remove(group)
            self._groups_layout.removeWidget(group)
            group.hide()
            group.setParent(None)
            group.deleteLater()
        self._on_changed()

    def _remove_mod_from_group_by_id(self, group_id: int, stat_id: str) -> None:
        for group in self._groups:
            if id(group) == group_id:
                for row in list(group._rows):
                    if row._filt.stat_id == stat_id:
                        group._remove_row(row)
                        return

    def _on_changed(self) -> None:
        self.active_mods_changed.emit(self.get_filters())

    def set_slot(self, slot: str) -> None:
        self._slot = slot
        for group in self._groups:
            group.set_slot(slot)

    def add_mod(self, filt: ModFilter) -> None:
        target_group = None
        for group in reversed(self._groups):
            if group.enabled:
                target_group = group
                if group.behaviour == ActiveModBehaviour.AND:
                    break
        if target_group is None:
            target_group = self._add_group(ActiveModBehaviour.AND)
        target_group.add_mod(filt)
        self._on_changed()

    def get_filters(self) -> list[ModFilter]:
        result: list[ModFilter] = []
        for group in self._groups:
            if not group.enabled:
                continue
            filters = group.get_active_filters()
            behaviour = group.behaviour
            for filt in filters:
                filter_copy = copy.copy(filt)
                filter_copy._group_behaviour = behaviour
                if behaviour == ActiveModBehaviour.COUNT:
                    count_min, count_max = group.count_range()
                    filter_copy._count_min = count_min
                    filter_copy._count_max = count_max
                result.append(filter_copy)
        return result

    def get_active_mod_groups_state(self) -> list[dict]:
        """Serialize the full active-mod group structure for saving."""
        output = []
        for group in self._groups:
            count_min, count_max = group.count_range()
            mods = []
            for row in group._rows:
                filt = row.filter
                mod_dict = {
                    "stat_id": filt.stat_id,
                    "label": filt.label,
                    "min": filt.min,
                    "max": filt.max,
                    "weight": filt.weight,
                    "min_tier": getattr(filt, "min_tier", 0),
                    "enabled": row.enabled,
                }
                influence_value = getattr(filt, "meta_influence_value", None)
                if influence_value:
                    mod_dict["meta_influence_value"] = influence_value
                mods.append(mod_dict)
            output.append({
                "behaviour": group.behaviour.value,
                "enabled": group.enabled,
                "count_min": count_min,
                "count_max": count_max,
                "mods": mods,
            })
        return output

    def load_active_mod_groups_state(self, state: list[dict]) -> None:
        self._destroy_all_groups()
        if self._groups:
            ghost_group = self._groups[0]
            self._groups.remove(ghost_group)
            self._groups_layout.removeWidget(ghost_group)
            ghost_group.hide()
            ghost_group.setParent(None)
            ghost_group.deleteLater()

        if not state:
            self._add_group(ActiveModBehaviour.AND)
            return

        for group_data in state:
            behaviour = ActiveModBehaviour(group_data.get("behaviour", ActiveModBehaviour.AND.value))
            group = self._add_group(behaviour)
            if not group_data.get("enabled", True):
                group._enable_checkbox.blockSignals(True)
                group._enable_checkbox.setChecked(False)
                group._enabled = False
                group._body.setVisible(False)
                group._enable_checkbox.blockSignals(False)
            if behaviour == ActiveModBehaviour.COUNT:
                group._count_min_spinbox.setValue(group_data.get("count_min", 1))
                group._count_max_spinbox.setValue(group_data.get("count_max", 0))
            for mod_data in group_data.get("mods", []):
                filt = ModFilter(
                    stat_id=mod_data.get("stat_id", ""),
                    label=mod_data.get("label", ""),
                    min=mod_data.get("min"),
                    max=mod_data.get("max"),
                    weight=float(mod_data.get("weight", 1.0)),
                )
                filt.min_tier = mod_data.get("min_tier", 0)
                influence_value = mod_data.get("meta_influence_value")
                if influence_value:
                    filt.meta_influence_value = influence_value
                row = ActiveModRow(filt, self._slot)
                if influence_value and hasattr(row, "_influence_cb") and row._influence_cb is not None:
                    index = row._influence_cb.findData(influence_value)
                    if index >= 0:
                        row._influence_cb.blockSignals(True)
                        row._influence_cb.setCurrentIndex(index)
                        row._influence_cb.blockSignals(False)
                if not mod_data.get("enabled", True):
                    row._chk.blockSignals(True)
                    row._chk.setChecked(False)
                    row._chk.blockSignals(False)
                row.changed.connect(self._on_changed)
                row.removed.connect(group._remove_row)
                group._rows.append(row)
                group._body_layout.addWidget(row)
            group._update_empty_hint()

        self._on_changed()

    def load_filters(self, filters: list[ModFilter]) -> None:
        self._destroy_all_groups()
        if self._groups:
            ghost_group = self._groups[0]
            self._groups.remove(ghost_group)
            self._groups_layout.removeWidget(ghost_group)
            ghost_group.hide()
            ghost_group.setParent(None)
            ghost_group.deleteLater()

        group = self._add_group(ActiveModBehaviour.AND)
        for filt in filters:
            group.add_mod(filt)
        if not filters:
            group._update_empty_hint()

    def clear_all(self) -> None:
        self._destroy_all_groups()
