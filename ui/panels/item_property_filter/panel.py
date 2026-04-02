from __future__ import annotations
"""
Public item property filter panel.

This class is the entry point the rest of the application should use.
It owns per-slot saved state and recreates the slot-specific content widget
whenever the selected slot changes. That keeps the implementation simple and
avoids stale user interface state.
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from .content import ItemPropertyContent


class ItemPropertyFilterPanel(QWidget):
    property_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._slot = ""
        self._states: dict[str, dict] = {}
        self._content: ItemPropertyContent | None = None
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
        self._refresh_content()

    def _refresh_content(self) -> None:
        while self._container_layout.count():
            item = self._container_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

        saved_state = self._states.get(self._slot, {}) if self._slot else {}
        new_content = ItemPropertyContent(self._slot, saved_state)
        new_content.changed.connect(self._on_content_changed)
        self._container_layout.addWidget(new_content)
        self._content = new_content
        new_content.show()

    def _on_content_changed(self, filt: dict) -> None:
        if self._slot:
            self._states[self._slot] = filt
        self.property_changed.emit(filt)

    def set_slot(self, slot: str) -> None:
        if self._slot and self._content:
            self._states[self._slot] = self._content.get_filter()
        self._slot = slot
        self._refresh_content()

    def get_filter(self) -> dict:
        return self._content.get_filter() if self._content else {}

    def get_all_slot_filters(self) -> dict[str, dict]:
        if self._slot and self._content:
            self._states[self._slot] = self._content.get_filter()
        return {slot: state for slot, state in self._states.items() if state}

    def clear_slot(self, slot: str) -> None:
        self._states.pop(slot, None)
        if slot == self._slot:
            self._refresh_content()

    def reset(self) -> None:
        self._states.clear()
        self._slot = ""
        self._refresh_content()
