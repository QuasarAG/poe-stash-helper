"""
Public overlay settings tab.

This file is intentionally much smaller than the old flat the overlay settings tab.
The detailed section widgets now live in their own files so this class can
focus on the tab's public role:
- assemble the groups
- forward important signals
- expose the few methods the rest of the application needs
"""

from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

from ui.shared import make_scrollable
from ui.tabs.overlay_settings.appearance_groups import (
    BadgeSettingsGroup,
    FontSizeSettingsGroup,
    OutlineSettingsGroup,
)
from ui.tabs.overlay_settings.calibration_group import CalibrationGroup
from ui.tabs.overlay_settings.sidebar_keybind_groups import (
    KeybindSettingsGroup,
    SidebarOrientationGroup,
)


class OverlayTab(QWidget):
    """Top-level widget used for the application's Overlay tab."""

    grid_params_changed = pyqtSignal(int, int, float, int, int)
    sidebar_orientation_changed = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._build_layout()

    def _build_layout(self) -> None:
        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)
        main_layout.setSpacing(10)

        self._calibration_group = CalibrationGroup()
        self._outline_group = OutlineSettingsGroup()
        self._badges_group = BadgeSettingsGroup()
        self._font_sizes_group = FontSizeSettingsGroup()
        self._sidebar_group = SidebarOrientationGroup()
        self._keybinds_group = KeybindSettingsGroup()

        self._calibration_group.params_changed.connect(self.grid_params_changed)
        self._font_sizes_group.font_sizes_changed.connect(self._apply_font_sizes)
        self._sidebar_group.orientation_changed.connect(self.sidebar_orientation_changed)

        main_layout.addWidget(self._calibration_group)
        main_layout.addWidget(self._outline_group)
        main_layout.addWidget(self._badges_group)
        main_layout.addWidget(self._font_sizes_group)
        main_layout.addWidget(self._sidebar_group)

        self._db_status = QLabel("")
        self._db_status.hide()
        self._db_update_status = self._db_status

        main_layout.addWidget(self._keybinds_group)
        main_layout.addStretch()

        scroll = make_scrollable(content_widget)
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(scroll)

    def update_grid_display(self, grid_x: int, grid_y: int, cell_size: float, columns: int, rows: int) -> None:
        self._calibration_group.update_display(grid_x, grid_y, cell_size, columns, rows)

    def save_calibration_to_config(self) -> None:
        self._calibration_group.save_to_config()

    def set_sidebar_horizontal(self, is_horizontal: bool) -> None:
        self._sidebar_group.set_horizontal(is_horizontal)

    def _apply_font_sizes(self) -> None:
        """Ask the top-level window to reapply the saved font-size settings."""
        parent = self.parent()
        while parent is not None:
            if hasattr(parent, "_apply_font_sizes"):
                parent._apply_font_sizes()
                return
            parent = parent.parent() if hasattr(parent, "parent") else None
