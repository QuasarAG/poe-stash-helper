from __future__ import annotations

"""
ui/widgets/scan_action_bar.py
─────────────────────────────────────────────────────────────────────────────
Reusable bottom action bar for the configuration window.

WHY THIS FILE EXISTS
    MainWindow previously built the scan button, stash dropdown, and status
    label inline. That was not wrong, but it made the root window file longer
    and mixed layout details with window-level orchestration.

    By moving the bar into its own widget, MainWindow becomes more like a
    composition root: it assembles bigger pieces rather than drawing every
    single row itself.
"""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QWidget


class ScanActionBar(QWidget):
    """Bottom bar with the scan button, stash selector, and status text."""

    scan_clicked = pyqtSignal()
    stash_selection_changed = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        self.scan_button = QPushButton("Scan Stash")
        self.scan_button.setObjectName("Accent")
        self.scan_button.setMinimumHeight(34)
        self.scan_button.setStyleSheet(
            "background:#2a4a2a; color:#88ff88; border:1px solid #448844;"
            " border-radius:4px; font-weight:bold; font-size:13px;"
        )
        self.scan_button.clicked.connect(self.scan_clicked)
        self.scan_button.setVisible(False)

        self.stash_dropdown = QComboBox()
        self.stash_dropdown.setMinimumWidth(180)
        self.stash_dropdown.setMaximumHeight(34)
        self.stash_dropdown.setToolTip("Which stash tab to scan")
        self.stash_dropdown.setStyleSheet(
            "QComboBox { background:#1a2a1a; color:#aaddaa; border:1px solid #336633;"
            "  border-radius:4px; padding:4px 8px; font-size:11px; }"
            "QComboBox QAbstractItemView { background:#1a2a1a; color:#ccffcc;"
            "  border:1px solid #448844; min-width:220px; font-size:11px; }"
        )
        self.stash_dropdown.currentIndexChanged.connect(self.stash_selection_changed)
        self.stash_dropdown.setVisible(False)

        self.status_label = QLabel("Ready")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.scan_button)
        layout.addWidget(self.stash_dropdown)
        layout.addSpacing(10)
        layout.addWidget(self.status_label, stretch=1)

    def set_scan_controls_visible(self, visible: bool) -> None:
        self.scan_button.setVisible(visible)
        self.stash_dropdown.setVisible(visible)

    def set_status(self, message: str) -> None:
        self.status_label.setText(message)
