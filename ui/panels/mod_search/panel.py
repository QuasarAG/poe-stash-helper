"""
ui/panels/mod_search/panel.py
─────────────────────────────────────────────────────────────────────────────
PURPOSE
    The full "Mod Stats" panel inside the Scan & Filters tab.

    This panel has two halves:

    LEFT SIDE  — Search for modifiers to add
        • category filter buttons
        • search input
        • results table
        • add-selected button

    RIGHT SIDE — Configure active modifier groups
        • ActiveModPanel
        • minimum matched-mod threshold slider

WHY THIS FILE EXISTS
    Earlier refactors moved the category buttons and results table into their
    own files. This phase also moved the search bar and the minimum-match
    slider into small widgets, then moved the public panel into this package
    so the whole feature now follows one clear package structure.
"""

from __future__ import annotations

import re as _regex

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QSplitter, QFrame,
)
from PyQt5.QtCore import Qt

import config as _config
from models import ModSearchCategory
from logic.mod_scorer import ModFilter
from ui.panels.active_mods import ActiveModPanel
from ui.panels.mod_search.category_bar import ModSearchCategoryBar
from ui.panels.mod_search.results_table import ModSearchResultsTable
from ui.panels.mod_search.search_bar import ModSearchBar
from ui.panels.mod_search.min_match_slider import MinMatchSlider
from ui.panels.mod_search.constants import (
    CONQUEROR_INFLUENCES,
    ELDRITCH_INFLUENCES,
    INFLUENCE_SORT_ORDER,
    AFFIX_TYPE_SORT_ORDER,
)


class ModSearchPanel(QWidget):
    """The full modifier search and active-mod configuration panel."""

    def __init__(self, initial_slot: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self._current_slot: str = initial_slot
        self._active_category: ModSearchCategory = ModSearchCategory.ALL
        self._build_layout()

    def _build_layout(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(5)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_left_search_side())
        splitter.addWidget(self._build_right_filters_side())
        splitter.setSizes([370, 540])

        main_layout.addWidget(splitter, stretch=1)

    def _build_left_search_side(self) -> QWidget:
        left_widget = QWidget()
        left_widget.setMinimumWidth(290)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 6, 0)
        left_layout.setSpacing(4)

        header_label = QLabel("Search Mods")
        header_label.setStyleSheet("color:#aabbff; font-weight:bold;")
        left_layout.addWidget(header_label)

        self._category_bar = ModSearchCategoryBar()
        self._category_bar.category_changed.connect(self._on_category_changed)
        left_layout.addWidget(self._category_bar)

        self._search_bar = ModSearchBar()
        self._search_bar.text_changed.connect(self._on_search_text_changed)
        left_layout.addWidget(self._search_bar)

        self._results_table = ModSearchResultsTable()
        self._results_table.add_row_requested.connect(self._add_mod_from_row)
        self._results_table.selected_rows_changed.connect(self._set_add_button_enabled)
        left_layout.addWidget(self._results_table, stretch=1)

        hint_label = QLabel("Double-click or press Add to add a mod →")
        hint_label.setStyleSheet("color:#555; font-size:9px;")
        left_layout.addWidget(hint_label)

        self._add_selected_button = QPushButton("Add Selected  →")
        self._add_selected_button.clicked.connect(self._on_add_selected_mod_clicked)
        self._add_selected_button.setEnabled(False)
        left_layout.addWidget(self._add_selected_button)

        return left_widget

    def _build_right_filters_side(self) -> QWidget:
        right_widget = QWidget()
        right_widget.setMinimumWidth(340)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(6, 0, 0, 0)
        right_layout.setSpacing(5)

        header_label = QLabel("Stat Filters")
        header_label.setStyleSheet("color:#aabbff; font-weight:bold;")
        right_layout.addWidget(header_label)

        self.active_mod_panel = ActiveModPanel(slot=self._current_slot)
        right_layout.addWidget(self.active_mod_panel, stretch=1)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("color:#222236;")
        right_layout.addWidget(separator)

        saved_overlay_colors = _config.get("overlay_colors") or {}
        saved_min_matching = int(saved_overlay_colors.get("min_matching", 1))
        self._min_match_slider = MinMatchSlider(saved_min_matching)
        self._min_match_slider.value_changed.connect(self._on_min_matching_changed)
        right_layout.addWidget(self._min_match_slider)

        return right_widget

    def _set_add_button_enabled(self, has_selection: bool) -> None:
        self._add_selected_button.setEnabled(has_selection and self._search_enabled())

    def _search_enabled(self) -> bool:
        return bool(self._current_slot)

    def set_slot(self, slot: str) -> None:
        self._current_slot = slot
        if slot:
            self._search_bar.set_placeholder_text(f"Search mods for {slot}…")
        else:
            self._search_bar.set_placeholder_text("Select a slot first to search mods…")
        self._search_bar.clear()
        self._on_search_text_changed("")
        self.active_mod_panel.set_slot(slot)

    def set_search_enabled(self, enabled: bool) -> None:
        self._search_bar.set_search_enabled(enabled)
        self._results_table.setEnabled(enabled)
        self._add_selected_button.setEnabled(enabled and self._results_table.has_selection())

    def get_current_slot(self) -> str:
        return self._current_slot

    def refresh_results(self) -> None:
        self._on_search_text_changed(self._search_bar.text())

    def apply_font_sizes(self, font_size: int) -> None:
        self._search_bar.apply_font_size(font_size)
        self._results_table.apply_font_size(font_size)
        self.active_mod_panel.setStyleSheet(
            f"QLabel {{ font-size:{font_size}px; }}"
            f"QLineEdit {{ font-size:{font_size}px; }}"
            f"QComboBox {{ font-size:{font_size}px; }}"
            f"QPushButton {{ font-size:{font_size}px; }}"
        )

    def _on_category_changed(self, category_key: ModSearchCategory) -> None:
        self._active_category = category_key
        self._category_bar.set_active_category(category_key)
        self._on_search_text_changed(self._search_bar.text())

    def _on_search_text_changed(self, text: str = "") -> None:
        from logic.mod_query import PSEUDO_DB, META_DB
        from data.mod_data import MOD_DB

        slot = self._current_slot
        category = self._active_category
        text_lower = text.lower().strip()

        pseudo_entries = [
            (sid, d) for sid, d in PSEUDO_DB.items()
            if not slot or slot == "Any" or not d.get("slots") or slot in d.get("slots", [])
        ]
        meta_entries = list(META_DB.items())
        real_entries = [
            (sid, d) for sid, d in MOD_DB.items()
            if not slot or slot == "Any" or not d.get("slots") or slot in d.get("slots", [])
        ]
        all_candidates = pseudo_entries + meta_entries + real_entries

        def matches_active_category(mod_dict: dict) -> bool:
            affix_type = mod_dict.get("affix_type", "")
            influence = mod_dict.get("influence")
            if category == ModSearchCategory.ALL:
                return True
            if category == ModSearchCategory.PSEUDO:
                return affix_type == "pseudo"
            if category == ModSearchCategory.META:
                return affix_type == "meta"
            if category == ModSearchCategory.PREFIX:
                return affix_type == "prefix" and not influence
            if category == ModSearchCategory.SUFFIX:
                return affix_type == "suffix" and not influence
            if category == ModSearchCategory.INFLUENCE:
                return influence in CONQUEROR_INFLUENCES
            if category == ModSearchCategory.ELDRITCH:
                return influence in ELDRITCH_INFLUENCES
            return False

        def sort_key(entry):
            _sid, mod_dict = entry
            influence = mod_dict.get("influence") or ""
            affix_type = mod_dict.get("affix_type", "")
            influence_group = 0 if not influence else (2 if influence in ELDRITCH_INFLUENCES else 1)
            type_group = 0 if affix_type == "meta" else (1 if affix_type == "pseudo" else 2)
            return (
                type_group,
                influence_group,
                INFLUENCE_SORT_ORDER.get(influence, 99),
                AFFIX_TYPE_SORT_ORDER.get(affix_type, 9),
                mod_dict.get("label", "").lower(),
            )

        filtered_pool = sorted(
            [
                (sid, mod_dict) for sid, mod_dict in all_candidates
                if matches_active_category(mod_dict)
                and (not text_lower or text_lower in mod_dict.get("label", "").lower())
            ],
            key=sort_key,
        )
        self._results_table.populate(filtered_pool, self._current_slot)

    def _on_add_selected_mod_clicked(self) -> None:
        for index in self._results_table.selectionModel().selectedRows():
            self._add_mod_from_row(index.row())

    def _add_mod_from_row(self, row: int) -> None:
        affix_cell = self._results_table.item(row, 0)
        label_cell = self._results_table.item(row, 2)
        if label_cell is None:
            return

        stat_id = (
            (affix_cell.data(Qt.UserRole) if affix_cell else None)
            or label_cell.data(Qt.UserRole)
            or ""
        )
        if not stat_id:
            return

        clean_label = _regex.sub(r"\s*\(\d+T\)$", "", label_cell.text()).strip()
        self.active_mod_panel.add_mod(ModFilter(stat_id=stat_id, label=clean_label))
        self._on_search_text_changed(self._search_bar.text())

    def _on_min_matching_changed(self, value: int) -> None:
        from ui.overlay import set_min_matching

        set_min_matching(value)
        overlay_colors = _config.get("overlay_colors") or {}
        overlay_colors["min_matching"] = value
        _config.set_key("overlay_colors", overlay_colors)
