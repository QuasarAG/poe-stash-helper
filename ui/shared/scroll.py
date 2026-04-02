"""Small shared Qt helpers used by many tabs and panels."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QScrollArea, QWidget


def make_scrollable(widget: QWidget) -> QScrollArea:
    """Wrap a widget in a transparent ``QScrollArea``.

    Many tabs in this project can become taller than the visible window.
    This helper keeps the scroll-area setup identical everywhere instead of
    repeating the same boilerplate in every file.
    """
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll_area.setFrameShape(QScrollArea.NoFrame)
    scroll_area.setWidget(widget)
    return scroll_area
