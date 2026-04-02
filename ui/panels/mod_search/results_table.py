"""Reusable table widget for mod search results."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

from ui.panels.mod_search.constants import (
    MAX_SEARCH_RESULTS,
    AFFIX_TYPE_BADGE_TEXT,
    AFFIX_TYPE_COLOURS,
    INFLUENCE_TAG_COLOURS,
)


class ModSearchResultsTable(QTableWidget):
    """Displays search results and stores stat identifiers in row item data."""

    add_row_requested = pyqtSignal(int)
    selected_rows_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(0, 3, parent)
        self._build_ui()

    def _build_ui(self) -> None:
        self.setHorizontalHeaderLabels(["Affix", "Tag", "Mod Name"])
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setStretchLastSection(True)
        header.setSectionsMovable(False)

        self.setColumnWidth(0, 40)
        self.setColumnWidth(1, 36)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.verticalHeader().setDefaultSectionSize(20)
        self.verticalHeader().hide()
        self.setStyleSheet(
            "QTableWidget { font-size:10px; }"
            "QTableWidget::item { padding:1px 3px; }"
        )
        self.cellDoubleClicked.connect(lambda row, _column: self.add_row_requested.emit(row))
        self.itemSelectionChanged.connect(self._emit_selection_state)

    def _emit_selection_state(self) -> None:
        self.selected_rows_changed.emit(self.has_selection())

    def has_selection(self) -> bool:
        """Return True when at least one real result row is selected.

        The surrounding panel uses this to decide whether the "Add Selected"
        button should be enabled.  Keeping the check on the table itself makes
        the panel code simpler and avoids repeating the Qt selection-model
        details in several places.
        """
        selection_model = self.selectionModel()
        if selection_model is None:
            return False
        return bool(selection_model.selectedRows())

    def apply_font_size(self, font_size: int) -> None:
        self.setStyleSheet(
            f"QTableWidget {{ font-size:{font_size}px; }}"
            f"QTableWidget::item {{ padding:1px 3px; }}"
            f"QHeaderView::section {{ font-size:{font_size}px; }}"
        )

    def populate(self, pool: list[tuple[str, dict]], current_slot: str) -> None:
        self.setRowCount(0)

        for stat_id, mod_dict in pool[:MAX_SEARCH_RESULTS]:
            label = mod_dict.get("label", "")
            affix_type = mod_dict.get("affix_type", "")
            influence = mod_dict.get("influence") or ""

            slot_tier_data = mod_dict.get("slot_tiers", {})
            tiers = (
                slot_tier_data.get(current_slot)
                if current_slot and current_slot != "Any" and current_slot in slot_tier_data
                else mod_dict.get("tiers", [])
            )
            tier_count = len(tiers)

            row_index = self.rowCount()
            self.insertRow(row_index)

            badge_text = AFFIX_TYPE_BADGE_TEXT.get(affix_type, "")
            badge_colour = QColor(AFFIX_TYPE_COLOURS.get(affix_type, "#666666"))
            affix_cell = QTableWidgetItem(badge_text)
            affix_cell.setTextAlignment(Qt.AlignCenter)
            affix_cell.setForeground(badge_colour)
            affix_cell.setData(Qt.UserRole, stat_id)
            affix_cell.setData(Qt.UserRole + 1, affix_type)
            affix_cell.setFlags(affix_cell.flags() & ~Qt.ItemIsEditable)
            self.setItem(row_index, 0, affix_cell)

            if affix_type == "pseudo":
                tag_text = "PSEUDO"
                tag_colour = QColor("#bb88ff")
            elif affix_type == "meta":
                tag_text = "META"
                tag_colour = QColor("#55cccc")
            elif influence:
                tag_text = influence[:3].upper()
                tag_colour = QColor(INFLUENCE_TAG_COLOURS.get(influence, "#aaaaaa"))
            else:
                tag_text = ""
                tag_colour = None

            tag_cell = QTableWidgetItem(tag_text)
            tag_cell.setTextAlignment(Qt.AlignCenter)
            if tag_colour:
                tag_cell.setForeground(tag_colour)
            tag_cell.setFlags(tag_cell.flags() & ~Qt.ItemIsEditable)
            self.setItem(row_index, 1, tag_cell)

            tier_suffix = f"  ({tier_count}T)" if tier_count > 0 else ""
            name_cell = QTableWidgetItem(f"{label}{tier_suffix}")
            name_cell.setData(Qt.UserRole, stat_id)
            name_cell.setData(Qt.UserRole + 1, affix_type)

            tooltip_lines = [f"Stat ID: {stat_id}"]
            if tiers:
                t1 = tiers[0]
                slot_note = f" on {current_slot}" if current_slot and current_slot != "Any" else ""
                tooltip_lines.append(f"T1{slot_note}: {t1[0]}–{t1[1]}  ({tier_count} tiers)")
            if influence:
                tooltip_lines.append(f"Influence: {influence}")
            if not tiers and mod_dict.get("tiers"):
                tooltip_lines.append(f"({len(mod_dict['tiers'])} tiers across all slots)")
            if affix_type == "pseudo":
                tooltip_lines.append("Sums values of all matching mods on the item")
                name_cell.setForeground(QColor("#cc99ff"))
            elif affix_type == "meta":
                meta_description = mod_dict.get("meta_description") or mod_dict.get("meta_influence_key", "")
                if meta_description:
                    tooltip_lines.append(f"Meta: {meta_description}")
                name_cell.setForeground(QColor("#66dddd"))

            name_cell.setToolTip("\n".join(tooltip_lines))
            name_cell.setFlags(name_cell.flags() & ~Qt.ItemIsEditable)
            self.setItem(row_index, 2, name_cell)

        if len(pool) > MAX_SEARCH_RESULTS:
            overflow_count = len(pool) - MAX_SEARCH_RESULTS
            self.insertRow(self.rowCount())
            overflow_cell = QTableWidgetItem(f"… {overflow_count} more — refine your search")
            overflow_cell.setForeground(QColor("#666677"))
            overflow_cell.setFlags(overflow_cell.flags() & ~Qt.ItemIsEditable)
            self.setItem(self.rowCount() - 1, 2, overflow_cell)
