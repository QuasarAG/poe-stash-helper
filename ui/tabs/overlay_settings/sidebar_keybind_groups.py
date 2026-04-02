"""Sidebar-orientation and keybind groups for the overlay settings tab."""

from __future__ import annotations

import config as _config

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QButtonGroup,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QKeySequenceEdit,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)


class SidebarOrientationGroup(QGroupBox):
    """Radio buttons for vertical versus horizontal sidebar layout."""

    orientation_changed = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Sidebar Orientation", parent)
        self._build_ui()
        self.restore_from_config()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setSpacing(16)

        self._radio_vertical = QRadioButton("Vertical  (left edge)")
        self._radio_horizontal = QRadioButton("Horizontal  (top)")
        self._radio_vertical.setChecked(True)

        self._button_group = QButtonGroup(self)
        self._button_group.addButton(self._radio_vertical, 0)
        self._button_group.addButton(self._radio_horizontal, 1)
        self._button_group.buttonClicked.connect(self._on_button_clicked)

        layout.addWidget(self._radio_vertical)
        layout.addWidget(self._radio_horizontal)
        layout.addStretch()

    def restore_from_config(self) -> None:
        self.set_horizontal(bool(_config.get("sidebar_horizontal") or False))

    def set_horizontal(self, is_horizontal: bool) -> None:
        if is_horizontal:
            self._radio_horizontal.setChecked(True)
        else:
            self._radio_vertical.setChecked(True)

    def _on_button_clicked(self, button) -> None:
        is_horizontal = button is self._radio_horizontal
        _config.set_key("sidebar_horizontal", is_horizontal)
        self.orientation_changed.emit(is_horizontal)


class KeybindSettingsGroup(QGroupBox):
    """Editable hotkey rows used by the overlay settings tab."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Keybinds", parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        saved_ui_config = _config.get("ui") or {}

        self._keybind_editors = {}
        self._add_keybind_row(
            layout,
            saved_ui_config,
            label_text="Scan stash  (also shows grid):",
            config_key="hotkey_scan",
            default_key="F10",
        )
        self._add_keybind_row(
            layout,
            saved_ui_config,
            label_text="Toggle sidebar  (HUD):",
            config_key="hotkey_toggle_overlay",
            default_key="F9",
        )

        restart_note = QLabel(
            "Click Apply after each change. App restart needed for hotkeys to fully reload."
        )
        restart_note.setStyleSheet("color:#666; font-size:10px;")
        restart_note.setWordWrap(True)
        layout.addWidget(restart_note)

    def _add_keybind_row(
        self,
        parent_layout: QVBoxLayout,
        saved_ui_config: dict,
        label_text: str,
        config_key: str,
        default_key: str,
    ) -> None:
        row = QHBoxLayout()

        label = QLabel(label_text)
        label.setMinimumWidth(180)
        row.addWidget(label)

        key_editor = QKeySequenceEdit()
        key_editor.setKeySequence(QKeySequence(saved_ui_config.get(config_key, default_key)))
        key_editor.setFixedWidth(120)
        row.addWidget(key_editor)

        apply_button = QPushButton("Apply")
        apply_button.setFixedWidth(55)
        apply_button.clicked.connect(
            lambda _checked=False, editor=key_editor, key=config_key: self._apply_keybind(editor, key)
        )
        row.addWidget(apply_button)
        row.addStretch()

        self._keybind_editors[config_key] = key_editor
        parent_layout.addLayout(row)

    def _apply_keybind(self, key_editor: QKeySequenceEdit, config_key: str) -> None:
        sequence = key_editor.keySequence().toString()
        if not sequence:
            return
        ui_cfg = _config.get("ui") or {}
        ui_cfg[config_key] = sequence
        _config.set_key("ui", ui_cfg)
