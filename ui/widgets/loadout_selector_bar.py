from __future__ import annotations

"""Small widget that owns the loadout selector row.

Why this widget exists
----------------------
`ScanFiltersTab` used to build the whole loadout selector row inline.
That made the tab file longer and mixed two different concerns together:

- high-level tab behaviour
- low-level button / dropdown construction

This widget keeps the row focused on presentation. The parent tab still owns
what happens when the user creates, selects, or deletes a loadout.
"""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QComboBox


class LoadoutSelectorBar(QWidget):
    """Row with New button, loadout dropdown, and Delete button."""

    new_requested = pyqtSignal()
    delete_requested = pyqtSignal()
    selection_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._new_button = QPushButton("New")
        self._new_button.setToolTip("Create a new empty loadout")
        self._new_button.setStyleSheet(
            "background:#1e2e1e; color:#88cc88; border:1px solid #446644;"
            " border-radius:3px; padding:4px 10px; font-weight:bold;"
        )
        self._new_button.clicked.connect(self.new_requested.emit)

        self._dropdown = QComboBox()
        self._dropdown.setMinimumWidth(140)
        self._dropdown.currentIndexChanged.connect(self.selection_changed.emit)

        self._delete_button = QPushButton("Delete")
        self._delete_button.setObjectName("danger")
        self._delete_button.clicked.connect(self.delete_requested.emit)

        layout.addWidget(self._new_button)
        layout.addWidget(self._dropdown, stretch=1)
        layout.addWidget(self._delete_button)

    def refresh_names(self, names: list[str], selected_name: str = "") -> None:
        """Replace the dropdown contents while preserving selection when possible."""

        self._dropdown.blockSignals(True)

        previous_name = selected_name or self._dropdown.currentText()

        self._dropdown.clear()

        # Only show the placeholder when there are no real loadouts.
        if not names:
            self._dropdown.addItem("-- select --")
            self._dropdown.setCurrentIndex(0)
            self._dropdown.blockSignals(False)
            return

        for name in names:
            self._dropdown.addItem(name)

        index = self._dropdown.findText(previous_name)

        # If the previous selection no longer exists, fall back to the first real loadout.
        if index < 0:
            index = 0

        self._dropdown.setCurrentIndex(index)
        self._dropdown.blockSignals(False)

    def current_name(self) -> str:
        return self._dropdown.currentText()

    def set_current_name(self, name: str) -> None:
        index = self._dropdown.findText(name)
        self._dropdown.setCurrentIndex(max(index, 0))

    def current_index(self) -> int:
        return self._dropdown.currentIndex()
