from __future__ import annotations
"""
Shared visual helpers for the Item Base filter user interface.

WHY THIS FILE EXISTS
    This package split means the item-base filter feature no longer needs one giant flat file for:

    - colour lookup tables
    - text formatting helpers
    - button stylesheet builders
    - custom small widget classes

    all mixed together above the main panel class.

    That worked, but it made the file long and harder to scan for a beginner.
    This file keeps the purely visual parts together so the main panel code can
    focus on behaviour.
"""

import re as _re

from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QPushButton, QSizePolicy, QVBoxLayout, QWidget

# This mutable dictionary is intentionally simple.
# The main window updates the button size slider by mutating this shared value,
# then asks the panel to rebuild itself.
UI_SCALE: dict[str, int] = {"btn_pt": 10}

INSTRUCTION_LABEL_STYLE = "color:#8888aa;font-size:9px;font-style:italic;"

STAT_COLOURS = {
    "STR": "#cc4444",
    "DEX": "#44aa44",
    "INT": "#4488cc",
    "STR/DEX": "#cc8844",
    "STR/INT": "#8844cc",
    "DEX/INT": "#44aaaa",
    "STR/DEX/INT": "#dddddd",
    "All": "#dddddd",
    "WARD": "#ddaa33",
    "NONE": "#888888",
}


def wtype_base(weapon_type: str) -> str:
    """Remove the stat suffix from a weapon type label.

    Example:
        "Tower Shield (STR)" -> "Tower Shield"
    """
    return _re.sub(r"\s*\([^)]+\)", "", weapon_type).strip()



def wtype_stat(weapon_type: str) -> str:
    """Return the stat suffix from a weapon type label, if present."""
    match = _re.search(r"\(([^)]+)\)", weapon_type)
    return match.group(1) if match else ""



def group_button_style(is_checked: bool, point_size: int = 10) -> str:
    padding = f"{max(2, point_size // 5)}px {max(8, point_size)}px"
    if is_checked:
        return (
            "QPushButton{" 
            "color:#ffcc66;background:#2a1e00;border:2px solid #cc8844;"
            f"border-radius:4px;padding:{padding};font-size:{point_size}px;"
            "font-weight:bold;text-align:left;letter-spacing:1px;}"
        )
    return (
        "QPushButton{" 
        "color:#886644;background:#140e00;border:1px solid #443322;"
        f"border-radius:4px;padding:{padding};font-size:{point_size}px;"
        "letter-spacing:1px;text-align:left;}"
    )



def child_button_style(is_checked: bool, colour: str = "#aaaacc", point_size: int = 10) -> str:
    padding = f"{max(2, point_size // 5)}px {max(7, point_size - 1)}px"
    if is_checked:
        return (
            "QPushButton{" 
            f"color:{colour};background:#0e1a26;border:2px solid {colour};"
            f"border-radius:4px;padding:{padding};font-size:{point_size}px;"
            "font-weight:bold;text-align:left;}"
        )
    return (
        "QPushButton{" 
        "color:#445566;background:#0a0e14;border:1px solid #223344;"
        f"border-radius:4px;padding:{padding};font-size:{point_size}px;"
        "text-align:left;}"
    )



def base_on_style(point_size: int = 10) -> str:
    padding = f"{max(2, point_size // 5)}px {max(6, point_size - 1)}px"
    return (
        "border:2px solid #aaccff;background:#1e2e4e;color:#cce0ff;"
        f"border-radius:4px;padding:{padding};font-size:{point_size}px;"
        "font-weight:bold;"
    )



def base_off_style(point_size: int = 10) -> str:
    padding = f"{max(2, point_size // 5)}px {max(6, point_size - 1)}px"
    return (
        "border:1px solid #2a2a44;background:#161626;color:#8888aa;"
        f"border-radius:4px;padding:{padding};font-size:{point_size}px;"
    )


class FlowWidget(QWidget):
    """Simple wrapping layout widget for base buttons.

    Qt does not provide a small built-in flow layout widget here, so this class
    keeps the custom wrapping behaviour in one small reusable place.
    """

    def __init__(self, spacing: int = 5, parent=None):
        super().__init__(parent)
        self._spacing = spacing
        self._items: list[QWidget] = []
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

    def add(self, widget: QWidget) -> None:
        widget.setParent(self)
        self._items.append(widget)
        self._layout_items()
        self.updateGeometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_items()

    def _layout_items(self) -> None:
        x = y = row_height = 0
        available_width = max(self.width(), 200)
        for widget in self._items:
            width = widget.sizeHint().width()
            height = widget.sizeHint().height()
            if x + width > available_width and x > 0:
                x = 0
                y += row_height + self._spacing
                row_height = 0
            widget.setGeometry(x, y, width, height)
            widget.show()
            x += width + self._spacing
            row_height = max(row_height, height)
        self.setFixedHeight(max(y + row_height + 6, 4))

    def sizeHint(self) -> QSize:
        return QSize(200, self.height() or 30)


class CollapsibleSection(QWidget):
    """Header widget plus a body that can be shown or hidden."""

    def __init__(self, header_widget: QWidget, indent: int = 0, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        root_layout = QVBoxLayout(self)
        root_layout.setSpacing(0)
        root_layout.setContentsMargins(indent, 0, 0, 2)

        self.header_widget = header_widget
        self.body_widget = QWidget()
        self.body_widget.setVisible(False)

        self._body_layout = QVBoxLayout(self.body_widget)
        self._body_layout.setSpacing(3)
        self._body_layout.setContentsMargins(16, 2, 0, 4)

        root_layout.addWidget(self.header_widget)
        root_layout.addWidget(self.body_widget)

    def body_layout(self) -> QVBoxLayout:
        return self._body_layout

    def set_expanded(self, is_expanded: bool) -> None:
        self.body_widget.setVisible(is_expanded)

    def is_expanded(self) -> bool:
        return self.body_widget.isVisible()



def make_stat_button(attribute: str, is_checked: bool, base_repository) -> QPushButton:
    point_size = UI_SCALE["btn_pt"]
    info = base_repository.stat_attributes.get(attribute, {"label": attribute})
    colour = STAT_COLOURS.get(attribute, "#cc8844")
    label = info.get("label", attribute) if isinstance(info, dict) else attribute

    button = QPushButton(label)
    button.setCheckable(True)
    button.setChecked(is_checked)
    button.setMinimumHeight(max(22, point_size * 2))
    padding = f"{max(2, point_size // 5)}px {max(8, point_size)}px"

    if is_checked:
        button.setStyleSheet(
            "QPushButton{" 
            f"color:{colour};background:#0d1a2a;border:2px solid {colour};"
            f"border-radius:4px;padding:{padding};font-size:{point_size}px;"
            "font-weight:bold;letter-spacing:1px;}"
        )
    else:
        button.setStyleSheet(
            "QPushButton{" 
            "color:#445566;background:#0a0e14;border:1px solid #223344;"
            f"border-radius:4px;padding:{padding};font-size:{point_size}px;"
            "letter-spacing:1px;text-align:left;}"
        )
    return button



def make_group_button(label: str, is_checked: bool) -> QPushButton:
    point_size = UI_SCALE["btn_pt"]
    button = QPushButton(label.upper())
    button.setCheckable(True)
    button.setChecked(is_checked)
    button.setMinimumHeight(max(24, point_size * 2 + 4))
    button.setStyleSheet(group_button_style(is_checked, point_size=point_size))
    return button



def make_weapon_type_button(weapon_type: str, is_checked: bool) -> QPushButton:
    point_size = UI_SCALE["btn_pt"]
    stat = wtype_stat(weapon_type)
    base = wtype_base(weapon_type)
    colour = STAT_COLOURS.get(stat, "#7799aa") if stat else "#7799aa"
    label = f"{base}  ({stat})" if stat else base

    button = QPushButton(label)
    button.setCheckable(True)
    button.setChecked(is_checked)
    button.setMinimumHeight(max(20, point_size * 2))
    button.setStyleSheet(child_button_style(is_checked, colour, point_size=point_size))
    return button
