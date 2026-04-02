"""Minimum matched-mod threshold row used by the mod search panel."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QSlider


class MinMatchSlider(QWidget):
    """Row with a label, slider, and numeric value display."""

    value_changed = pyqtSignal(int)

    def __init__(self, initial_value: int = 1, parent: QWidget | None = None):
        super().__init__(parent)
        self._build_layout(initial_value)

    def _build_layout(self, initial_value: int) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 6)

        label = QLabel("Min mods to highlight:")
        label.setStyleSheet("color:#aaaacc; font-size:10px;")
        layout.addWidget(label)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, 6)
        self._slider.setValue(initial_value)
        self._slider.setFixedWidth(140)
        self._slider.setTickPosition(QSlider.TicksBelow)
        self._slider.setTickInterval(1)
        self._slider.setToolTip(
            "0 = highlight all matched items\n"
            "1 = at least 1 mod must match (default)\n"
            "2 = at least 2 mods must match, etc."
        )

        self._value_label = QLabel(str(initial_value))
        self._value_label.setFixedWidth(16)
        self._value_label.setStyleSheet(
            "font-weight:bold; color:#aaccff; font-size:10px;"
        )

        self._slider.valueChanged.connect(self._on_slider_changed)

        layout.addWidget(self._slider)
        layout.addWidget(self._value_label)
        layout.addStretch()

    def _on_slider_changed(self, value: int) -> None:
        self._value_label.setText(str(value))
        self.value_changed.emit(value)

    def value(self) -> int:
        return self._slider.value()

    def set_value(self, value: int) -> None:
        self._slider.setValue(value)
