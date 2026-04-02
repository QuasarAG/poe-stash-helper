"""
ui/tabs/config_tab.py
─────────────────────────────────────────────────────────────────────────────
PURPOSE
    Placeholder for the "Config" tab in the MainWindow.

    This tab is intentionally empty for now.  It is reserved for future
    app-level configuration settings that don't fit naturally into the
    Account, Scan & Filters, or Overlay tabs.

    Possible future contents:
        • Cache management (clear cached stash data)
        • Logging verbosity settings
        • Export / import loadouts
        • App update checks
        • Theme customisation beyond the current dark theme

HOW TO ADD CONTENT
    Replace the placeholder label with real widgets and layouts.
    Follow the same pattern as account_tab.py or the overlay settings package:
        1. Create the widgets in helper methods.
        2. Wire signals to dedicated services or repositories.
        3. Import and add the tab in main_window.py.
"""

from __future__ import annotations

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore    import Qt

from ui.shared import make_scrollable


class ConfigTab(QWidget):
    """
    The "Config" tab widget — currently a placeholder.

    When this tab gains real content, the _build_layout method should be
    expanded.  For now it shows a short message so the tab is not blank.
    """

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._build_layout()

    def _build_layout(self) -> None:
        content_widget = QWidget()
        main_layout    = QVBoxLayout(content_widget)
        main_layout.setSpacing(10)

        # ── Placeholder label ─────────────────────────────────────────────────
        placeholder = QLabel(
            "Config tab — reserved for future settings.\n\n"
            "This tab will contain app-level configuration\n"
            "that doesn't belong in Account or Overlay."
        )
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet(
            "color:#555; font-size:11px; font-style:italic;"
            " background:#101018; border:1px solid #222236;"
            " border-radius:4px; padding:32px;"
        )
        main_layout.addWidget(placeholder)
        main_layout.addStretch()

        scroll = make_scrollable(content_widget)
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(scroll)
