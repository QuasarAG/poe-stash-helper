"""Small reusable widget for mod-search category buttons."""

from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton

from models import ModSearchCategory
from .constants import MOD_SEARCH_CATEGORY_BUTTONS


class ModSearchCategoryBar(QWidget):
    """Row of checkable category buttons."""

    category_changed = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._buttons: dict[ModSearchCategory, QPushButton] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        style = (
            "QPushButton { background:#1a1a2e; color:#aaaacc;"
            "  border:1px solid #333355; border-radius:3px;"
            "  padding:2px 6px; font-size:9px; font-weight:bold; }"
            "QPushButton:hover { background:#22223a; color:#ccccff; }"
            "QPushButton:checked { background:#2a2a5a; color:#ffffff;"
            "  border:1px solid #5577ff; }"
        )

        for display_label, category_key, tooltip in MOD_SEARCH_CATEGORY_BUTTONS:
            button = QPushButton(display_label)
            button.setCheckable(True)
            button.setToolTip(tooltip)
            button.setStyleSheet(style)
            button.clicked.connect(lambda _checked, cat=category_key: self.category_changed.emit(cat))
            self._buttons[category_key] = button
            layout.addWidget(button)

        self.set_active_category(ModSearchCategory.ALL)
        layout.addStretch()

    def set_active_category(self, category_key: ModSearchCategory) -> None:
        for key, button in self._buttons.items():
            button.setChecked(key == category_key)
