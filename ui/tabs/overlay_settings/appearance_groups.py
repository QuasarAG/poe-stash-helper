"""Appearance-related groups for overlay settings."""

from __future__ import annotations

import config as _config

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ui.tabs.overlay_settings.constants import FONT_SLIDER_ROWS, OUTLINE_COLOR_ROWS
from models import OutlineColorRole


class OutlineSettingsGroup(QGroupBox):
    """Colour pickers and outline thickness settings."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Item Outline Colours & Thresholds", parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        for label_text, colour_key, default_hex in OUTLINE_COLOR_ROWS:
            layout.addLayout(self._build_colour_picker_row(label_text, colour_key, default_hex))

        saved_overlay_colors = _config.get("overlay_colors") or {}
        thickness_row = QHBoxLayout()
        thickness_row.addWidget(QLabel("Outline thickness (px):"))

        self._outline_thickness_spinbox = QSpinBox()
        self._outline_thickness_spinbox.setRange(1, 10)
        self._outline_thickness_spinbox.setValue(int(saved_overlay_colors.get("thickness", 3)))
        self._outline_thickness_spinbox.setFixedWidth(60)
        self._outline_thickness_spinbox.valueChanged.connect(self._on_outline_thickness_changed)

        thickness_row.addWidget(self._outline_thickness_spinbox)
        thickness_row.addStretch()
        layout.addLayout(thickness_row)

        hint = QLabel("0 = outline all items · 1 = at least 1 mod must match · 10 = very strict")
        hint.setStyleSheet("color:#666; font-size:10px;")
        layout.addWidget(hint)

    def _build_colour_picker_row(self, label_text: str, colour_role: OutlineColorRole, default_hex: str) -> QHBoxLayout:
        row = QHBoxLayout()
        label = QLabel(label_text)
        label.setMinimumWidth(220)
        row.addWidget(label)

        swatch_button = QPushButton()
        swatch_button.setFixedSize(48, 22)
        swatch_button.setToolTip("Click to pick colour")

        def apply_colour(hex_colour: str) -> None:
            swatch_button.setStyleSheet(
                f"background:{hex_colour}; border:1px solid #666; border-radius:4px;"
            )
            from ui.overlay import set_outline_color

            set_outline_color(colour_role, hex_colour)
            overlay_colors = _config.get("overlay_colors") or {}
            overlay_colors[colour_role.value] = hex_colour
            _config.set_key("overlay_colors", overlay_colors)

        saved_overlay_colors = _config.get("overlay_colors") or {}
        current_hex = saved_overlay_colors.get(colour_role.value, default_hex)
        apply_colour(current_hex)

        def choose_colour() -> None:
            chosen = QColorDialog.getColor(QColor(current_hex), self, f"Choose colour for {colour_role.value}")
            if chosen.isValid():
                apply_colour(chosen.name())

        swatch_button.clicked.connect(choose_colour)
        row.addWidget(swatch_button)
        row.addStretch()
        return row

    def _on_outline_thickness_changed(self, value: int) -> None:
        from ui.overlay import set_outline_thickness

        set_outline_thickness(value)
        overlay_colors = _config.get("overlay_colors") or {}
        overlay_colors["thickness"] = value
        _config.set_key("overlay_colors", overlay_colors)


class BadgeSettingsGroup(QGroupBox):
    """Badge visibility toggles and hover tooltip control."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Overlay Badges  (toggle each on/off)", parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        saved_badge_config = _config.get("overlay_badges") or {}

        self._add_badge_checkbox(
            layout,
            label_text="Mod count badge  (e.g. '3/4' — matched / total)",
            badge_key="mod_count",
            default_on=True,
            tooltip="Shows how many of your filter mods the item has",
            saved_badge_config=saved_badge_config,
        )

        saved_ui_config = _config.get("ui") or {}
        self._hover_tooltip_checkbox = QCheckBox(
            'Hover tooltip  ("Why highlighted?" — show matched mods on mouse-over)'
        )
        self._hover_tooltip_checkbox.setChecked(saved_ui_config.get("hover_tooltip", True))
        self._hover_tooltip_checkbox.setStyleSheet("QCheckBox { color:#cccccc; font-size:10px; }")
        self._hover_tooltip_checkbox.setToolTip(
            "When enabled, hovering over a highlighted item shows a popup\n"
            "listing which mods matched and the overall score."
        )
        self._hover_tooltip_checkbox.stateChanged.connect(self._on_hover_tooltip_toggled)
        layout.addWidget(self._hover_tooltip_checkbox)

        future_note = QLabel("More badges may be added in future updates.")
        future_note.setStyleSheet("color:#555; font-size:9px; font-style:italic;")
        layout.addWidget(future_note)

    def _add_badge_checkbox(
        self,
        parent_layout: QVBoxLayout,
        label_text: str,
        badge_key: str,
        default_on: bool,
        tooltip: str,
        saved_badge_config: dict,
    ) -> None:
        checkbox = QCheckBox(label_text)
        checkbox.setChecked(saved_badge_config.get(badge_key, default_on))
        checkbox.setStyleSheet("QCheckBox { color:#cccccc; font-size:10px; }")
        checkbox.setToolTip(tooltip)

        def on_state_changed(state: int) -> None:
            is_enabled = state == Qt.Checked
            from ui.overlay import set_badge_flag

            set_badge_flag(badge_key, is_enabled)
            badges = _config.get("overlay_badges") or {}
            badges[badge_key] = is_enabled
            _config.set_key("overlay_badges", badges)

        checkbox.stateChanged.connect(on_state_changed)

        from ui.overlay import set_badge_flag

        set_badge_flag(badge_key, saved_badge_config.get(badge_key, default_on))
        parent_layout.addWidget(checkbox)

    def _on_hover_tooltip_toggled(self, state: int) -> None:
        is_enabled = state == Qt.Checked
        ui_cfg = _config.get("ui") or {}
        ui_cfg["hover_tooltip"] = is_enabled
        _config.set_key("ui", ui_cfg)
        try:
            from ui.overlay import get_running_instance as _get_stash_overlay

            overlay = _get_stash_overlay()
            if overlay:
                if is_enabled:
                    overlay.tooltip.start()
                else:
                    overlay.tooltip.stop()
        except Exception:
            # The overlay may not exist yet.  In that case the saved config is
            # still correct, and the setting will be applied when the overlay starts.
            pass


class FontSizeSettingsGroup(QGroupBox):
    """Sliders that control font sizes across the application."""

    font_sizes_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Font Sizes", parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        saved_font_sizes = _config.get("font_sizes") or {}

        self._sliders_by_key = {}
        for label_text, size_key, default, minimum, maximum in FONT_SLIDER_ROWS:
            self._sliders_by_key[size_key] = self._add_font_slider(
                layout,
                label_text=label_text,
                size_key=size_key,
                default=default,
                minimum=minimum,
                maximum=maximum,
                saved_font_sizes=saved_font_sizes,
            )

        explanation = QLabel(
            "General text adjusts the base. Each other slider adds/subtracts from that base. "
            "Changes apply immediately."
        )
        explanation.setStyleSheet("color:#555; font-size:9px; font-style:italic;")
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

    def _add_font_slider(
        self,
        parent_layout: QVBoxLayout,
        label_text: str,
        size_key: str,
        default: int,
        minimum: int,
        maximum: int,
        saved_font_sizes: dict,
    ) -> QSlider:
        row = QHBoxLayout()
        label = QLabel(label_text)
        label.setMinimumWidth(250)
        row.addWidget(label)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(saved_font_sizes.get(size_key, default))
        slider.setFixedWidth(160)
        slider.setTickPosition(QSlider.TicksBelow)
        slider.setTickInterval(1)

        value_label = QLabel(str(slider.value()))
        value_label.setFixedWidth(24)
        value_label.setStyleSheet("font-weight:bold; color:#aaccff;")

        def on_value_changed(value: int) -> None:
            value_label.setText(str(value))
            sizes = _config.get("font_sizes") or {}
            sizes[size_key] = value
            _config.set_key("font_sizes", sizes)
            self.font_sizes_changed.emit()

        slider.valueChanged.connect(on_value_changed)

        row.addWidget(slider)
        row.addWidget(value_label)
        row.addStretch()
        parent_layout.addLayout(row)
        return slider
