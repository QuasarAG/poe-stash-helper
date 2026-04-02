from __future__ import annotations
"""
Public Item Base filter panel.

This panel is now intentionally thin:
- it owns per-slot saved state
- it creates the hierarchy widget for the current slot
- it resolves nested selections into the final flat base list used by scans

The detailed hierarchy widget and the resolution rules live in separate files so
this file stays easier to read for a beginner.
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from repositories.base_repository import get_default_base_repository

from .hierarchy_content import HierarchyContent
from .state_resolver import resolve_selected_bases


class ItemBaseFilterPanel(QWidget):
    """Hierarchical item-base selector used in the Scan & Filters tab."""

    selected_bases_changed = pyqtSignal(str, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._base_repository = get_default_base_repository()
        self._slot = ""
        self._states: dict[str, dict] = {}
        self._content: HierarchyContent | None = None
        self._build_scaffold()

    def _build_scaffold(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setSpacing(0)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setSpacing(0)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._scroll.setWidget(self._container)
        outer_layout.addWidget(self._scroll)

        self._refresh()

    def _refresh(self) -> None:
        while self._container_layout.count():
            item = self._container_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

        state = self._states.setdefault(self._slot, {}) if self._slot else {}
        content_widget = HierarchyContent(self._slot, state, self._base_repository)
        content_widget.state_changed.connect(self._on_state_changed)
        self._container_layout.addWidget(content_widget)
        self._content = content_widget
        content_widget.show()

    def _on_state_changed(self, state: dict) -> None:
        if self._slot:
            self._states[self._slot] = state
        resolved = self._resolve(self._slot, state)
        self.selected_bases_changed.emit(self._slot, resolved)

    def _resolve(self, slot: str, state: dict) -> list[str]:
        return resolve_selected_bases(slot, state, self._base_repository)

    def set_slot(self, slot: str) -> None:
        self._slot = slot
        self._refresh()

    def get_selected_bases(self) -> list[str]:
        state = self._states.get(self._slot, {})
        return self._resolve(self._slot, state)

    def get_all_selections(self) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for slot, state in self._states.items():
            resolved = self._resolve(slot, state)
            if resolved:
                result[slot] = resolved
        return result

    def clear_slot(self, slot: str) -> None:
        self._states.pop(slot, None)
        if slot == self._slot:
            self._refresh()

    def reset(self) -> None:
        self._states.clear()
        self._slot = ""
        self._refresh()
