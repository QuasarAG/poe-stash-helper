"""Search input row used by the mod search panel.

This file exists so the main panel does not need to carry tiny button styling
and search-field wiring details inline. The widget has one clear public job:
manage the text box and clear button used to search modifier labels.
"""

from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton


class ModSearchBar(QWidget):
    """Small reusable row with a search field and a clear button."""

    text_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._build_layout()

    def _build_layout(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._line_edit = QLineEdit()
        self._line_edit.setPlaceholderText("Select a slot first to search mods…")
        self._line_edit.setEnabled(False)
        self._line_edit.textChanged.connect(self.text_changed)

        self._clear_button = QPushButton("✕")
        self._clear_button.setFixedSize(22, 22)
        self._clear_button.setToolTip("Clear search")
        self._clear_button.setEnabled(False)
        self._clear_button.setStyleSheet(
            "QPushButton { background:#2a1010; color:#cc4444;"
            "  border:1px solid #663333; border-radius:3px;"
            "  font-size:11px; font-weight:bold; padding:0px; }"
            "QPushButton:hover { background:#3a1515; color:#ff6666;"
            "  border-color:#993333; }"
        )
        self._clear_button.clicked.connect(self.clear)

        layout.addWidget(self._line_edit, stretch=1)
        layout.addWidget(self._clear_button)

    def clear(self) -> None:
        self._line_edit.clear()

    def text(self) -> str:
        return self._line_edit.text()

    def set_text(self, text: str) -> None:
        self._line_edit.setText(text)

    def set_placeholder_text(self, text: str) -> None:
        self._line_edit.setPlaceholderText(text)

    def set_search_enabled(self, enabled: bool) -> None:
        self._line_edit.setEnabled(enabled)
        self._clear_button.setEnabled(enabled)

    def apply_font_size(self, font_size: int) -> None:
        self._line_edit.setStyleSheet(f"font-size:{font_size}px;")
