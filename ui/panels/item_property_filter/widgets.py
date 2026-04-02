from __future__ import annotations
"""
Small reusable helper widgets and style helpers for the item property filter.

The old single-file version mixed all of this directly inside the main panel.
That made the file feel heavy very early, before the reader even reached the
actual filtering logic. Splitting these helpers out keeps the public panel much
cleaner and easier to learn from.
"""

from PyQt5.QtCore import Qt, pyqtSignal
from models import ItemRarity
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .constants import RARITY_STYLES

SECTION_HEADER_STYLE = (
    "QCheckBox { color:#8888aa; font-size:9px; font-weight:bold;"
    " letter-spacing:1px; }"
)
FIELD_LABEL_STYLE = "color:#8888aa; font-size:10px;"
INPUT_STYLE = (
    "background:#141424; color:#bbbbdd; border:1px solid #2a2a4e;"
    " border-radius:3px; padding:2px 4px; font-size:10px;"
)
SEPARATOR_STYLE = "background:#2a2a3e;"


def horizontal_separator() -> QFrame:
    separator = QFrame()
    separator.setFixedHeight(1)
    separator.setStyleSheet("QFrame{" + SEPARATOR_STYLE + "}")
    return separator


def vertical_separator() -> QFrame:
    separator = QFrame()
    separator.setFixedWidth(1)
    separator.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
    separator.setStyleSheet("QFrame{" + SEPARATOR_STYLE + "}")
    return separator


def make_field_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(FIELD_LABEL_STYLE)
    return label


def make_property_label(text: str, width: int = 110) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(FIELD_LABEL_STYLE)
    label.setFixedWidth(width)
    return label


def make_min_label() -> QLabel:
    label = QLabel("Min")
    label.setStyleSheet(FIELD_LABEL_STYLE)
    label.setFixedWidth(24)
    return label


def make_max_label() -> QLabel:
    label = QLabel("Max")
    label.setStyleSheet(FIELD_LABEL_STYLE)
    label.setFixedWidth(24)
    return label


def make_spinbox(low: int = 0, high: int = 9999) -> QSpinBox:
    spinbox = QSpinBox()
    spinbox.setRange(low, high)
    spinbox.setValue(low)
    spinbox.setSpecialValueText("—")
    spinbox.setStyleSheet(INPUT_STYLE)
    spinbox.setFixedWidth(56)
    return spinbox


def make_double_spinbox(low: float = 0.0, high: float = 9999.0) -> QDoubleSpinBox:
    spinbox = QDoubleSpinBox()
    spinbox.setRange(low, high)
    spinbox.setDecimals(1)
    spinbox.setValue(low)
    spinbox.setSpecialValueText("—")
    spinbox.setStyleSheet(INPUT_STYLE)
    spinbox.setFixedWidth(64)
    return spinbox


def make_yes_no_combo() -> QComboBox:
    combo = QComboBox()
    combo.addItems(["Any", "Yes", "No"])
    combo.setStyleSheet(INPUT_STYLE + " min-width:64px;")
    combo.setFixedWidth(72)
    return combo


def rarity_button_style(name: ItemRarity | str, active: bool) -> str:
    if isinstance(name, str):
        try:
            name = ItemRarity(name)
        except ValueError:
            pass
    color, background = RARITY_STYLES[name]
    if active:
        return (
            f"QPushButton{{border:2px solid {color};background:{background};color:{color};"
            f"border-radius:4px;padding:3px 9px;font-size:10px;font-weight:bold;}}"
        )
    return (
        "QPushButton{border:1px solid #2a2a44;background:#141424;color:#555577;"
        "border-radius:4px;padding:3px 9px;font-size:10px;}"
    )


class Section(QWidget):
    """
    A collapsible section used inside the slot-specific property content.

    The section only knows how to show and hide its body. It does not know what
    fields are inside that body. That keeps it reusable and simple.
    """

    changed = pyqtSignal()

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        root_layout = QVBoxLayout(self)
        root_layout.setSpacing(2)
        root_layout.setContentsMargins(0, 0, 0, 4)

        self.checkbox = QCheckBox(title.upper())
        self.checkbox.setStyleSheet(SECTION_HEADER_STYLE)

        self.body = QWidget()
        self.body.setVisible(False)
        self.body.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setSpacing(2)
        self.body_layout.setContentsMargins(8, 2, 0, 2)

        self.checkbox.stateChanged.connect(self._on_toggled)

        root_layout.addWidget(self.checkbox)
        root_layout.addWidget(self.body)

    def _on_toggled(self, state: int) -> None:
        self.body.setVisible(state == Qt.Checked)
        self.adjustSize()
        if self.parent():
            self.parent().adjustSize()
        self.changed.emit()

    def is_enabled(self) -> bool:
        return self.checkbox.isChecked()

    def set_enabled(self, value: bool) -> None:
        self.checkbox.setChecked(value)


def make_row(items: list[QWidget | int]) -> QWidget:
    """
    Build a compact left-aligned row.

    Integer items are treated as stretch values. This keeps the row creation
    calls in content.py very compact and easy to read.
    """
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setSpacing(4)
    layout.setContentsMargins(0, 1, 0, 1)

    for item in items:
        if isinstance(item, QWidget):
            layout.addWidget(item)
        elif isinstance(item, int):
            layout.addStretch(item)

    return widget


def add_min_max_row(section: Section, label: str, low_widget: QWidget, high_widget: QWidget) -> None:
    row = make_row([
        make_property_label(label),
        make_min_label(),
        low_widget,
        make_max_label(),
        high_widget,
        1,
    ])
    section.body_layout.addWidget(row)


def add_boolean_row(section: Section, label: str, widget: QWidget) -> None:
    row = make_row([make_property_label(label), widget, 1])
    section.body_layout.addWidget(row)
