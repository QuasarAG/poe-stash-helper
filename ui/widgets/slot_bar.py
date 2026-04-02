from __future__ import annotations

"""Widget that owns the wrapping equipment-slot bar.

This extracts the slot-bar user interface out of `ScanFiltersTab` so the tab
can focus more on application behaviour and less on low-level widget layout.
"""

from PyQt5.QtCore import Qt, QSize, QPoint, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QMenu,
)

_SLOT_BUTTON_ACTIVE_STYLE = (
    "background:#2c3c5c; color:#cce0ff; border-top:2px solid #5588dd;"
    " border-left:1px solid #445577; border-right:1px solid #445577;"
    " border-bottom:none; border-radius:3px 3px 0 0;"
    " padding:3px 10px; font-size:10px; font-weight:bold;"
)
_SLOT_BUTTON_INACTIVE_STYLE = (
    "background:#1a1a2e; color:#6677aa; border:1px solid #2a2a44;"
    " border-radius:3px 3px 0 0; padding:3px 10px; font-size:10px;"
)


class _SlotFlowWidget(QWidget):
    """Lay out child widgets left-to-right and wrap to new rows when needed."""

    def __init__(self, widgets: list[QWidget], spacing: int = 4, parent: QWidget = None):
        super().__init__(parent)
        self._widgets = widgets
        self._spacing = spacing
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        for widget in widgets:
            widget.setParent(self)
        self._relayout()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()
        if self.parent():
            self.parent().updateGeometry()

    def _relayout(self) -> None:
        available_width = max(self.width(), 200)
        spacing = self._spacing
        x = y = 0
        row_height = 0

        for widget in self._widgets:
            hint = widget.sizeHint()
            width = hint.width()
            height = hint.height()

            if x + width > available_width and x > 0:
                x = 0
                y += row_height + spacing
                row_height = 0

            widget.setGeometry(x, y, width, height)
            widget.show()
            x += width + spacing
            row_height = max(row_height, height)

        total_height = (y + row_height) if self._widgets else 0
        self.setMinimumHeight(total_height + 4)
        self.setFixedHeight(total_height + 4)

    def sizeHint(self) -> QSize:
        return QSize(200, self.height() or 30)


class SlotBar(QWidget):
    """Wrapping bar of slot buttons plus the permanent add-slot button."""

    slot_clicked = pyqtSignal(str)
    slot_remove_requested = pyqtSignal(str)
    add_slot_requested = pyqtSignal()
    add_slot_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._slot_button_widgets: dict[str, QWidget] = {}
        self._build()

    def _build(self) -> None:
        self.setStyleSheet(
            "QWidget { background:#161626; border:1px solid #2a2a3e; border-radius:3px; }"
        )
        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(3)
        self._layout.setContentsMargins(4, 3, 4, 3)

        self._add_slot_button = QPushButton("＋ Add Slot")
        self._add_slot_button.setToolTip("Add an equipment slot with its own mod list")
        self._add_slot_button.setStyleSheet(
            "background:#1e2a1e; color:#88cc88; border:1px solid #446644;"
            " border-radius:3px; padding:3px 10px; font-size:10px; font-weight:bold;"
        )
        self._add_slot_button.clicked.connect(self.add_slot_requested.emit)
        self._add_slot_button.setVisible(False)

        initial_row = QHBoxLayout()
        initial_row.setSpacing(4)
        initial_row.setContentsMargins(0, 0, 0, 0)
        initial_row.addWidget(self._add_slot_button)
        initial_row.addStretch()
        self._layout.addLayout(initial_row)

    def set_add_slot_button_visible(self, visible: bool) -> None:
        self._add_slot_button.setVisible(visible)

    def rebuild(self, active_slot: str, slot_names: list[str]) -> None:
        """Rebuild the wrapping slot buttons from scratch."""
        self._add_slot_button.setParent(self)

        while self._layout.count() > 0:
            item = self._layout.takeAt(0)
            if item is None:
                break
            widget = item.widget()
            if widget and widget is not self._add_slot_button:
                widget.deleteLater()

        self._slot_button_widgets = {}
        all_flow_widgets: list[QWidget] = []

        for slot_name in list(slot_names or []):
            container = self._make_slot_button_container(
                slot_name=slot_name,
                is_active=(slot_name == active_slot),
            )
            self._slot_button_widgets[slot_name] = container
            all_flow_widgets.append(container)

        all_flow_widgets.append(self._add_slot_button)
        flow_widget = _SlotFlowWidget(all_flow_widgets, spacing=4)
        self._layout.addWidget(flow_widget)
        self._layout.addStretch()
        self._add_slot_button.show()

    def set_active_slot(self, active_slot: str) -> None:
        """Update button styles so only one slot looks active."""
        for slot_name, container in self._slot_button_widgets.items():
            button = container.findChild(QPushButton)
            if not button:
                continue
            is_active = slot_name == active_slot
            button.setStyleSheet(
                _SLOT_BUTTON_ACTIVE_STYLE if is_active else _SLOT_BUTTON_INACTIVE_STYLE
            )
            button.setChecked(is_active)

    def show_add_slot_menu(self, available_slots: list[str]) -> None:
        """Show the add-slot menu under the permanent add-slot button."""
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background:#1a1a2e; color:#ccccff; border:1px solid #445577; }"
            "QMenu::item { padding:5px 20px; font-size:10px; }"
            "QMenu::item:selected { background:#2a3a5a; color:#ffffff; }"
        )

        if not available_slots:
            menu.addAction("(all slots already added)").setEnabled(False)
        else:
            for slot_name in available_slots:
                menu.addAction(
                    slot_name,
                    lambda checked=False, s=slot_name: self.add_slot_selected.emit(s),
                )

        menu.exec_(self._add_slot_button.mapToGlobal(QPoint(0, self._add_slot_button.height())))

    def _make_slot_button_container(self, slot_name: str, is_active: bool) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        slot_button = QPushButton(slot_name)
        slot_button.setCheckable(True)
        slot_button.setChecked(is_active)
        slot_button.setStyleSheet(
            _SLOT_BUTTON_ACTIVE_STYLE if is_active else _SLOT_BUTTON_INACTIVE_STYLE
        )
        slot_button.setToolTip(
            "Any — mods common to all item types" if slot_name == "Any" else f"View/edit mods for: {slot_name}"
        )
        slot_button.clicked.connect(lambda checked=False, s=slot_name: self.slot_clicked.emit(s))
        row.addWidget(slot_button)

        remove_button = QPushButton("×")
        remove_button.setFixedSize(16, 26)
        remove_button.setToolTip(f"Remove slot '{slot_name}'")
        remove_button.setStyleSheet(
            "QPushButton { background:#1a1a2e; color:#666699; border:none;"
            "  font-size:11px; font-weight:bold; }"
            "QPushButton:hover { background:#3a1a1a; color:#ff7777; }"
        )
        remove_button.clicked.connect(
            lambda checked=False, s=slot_name: self.slot_remove_requested.emit(s)
        )
        row.addWidget(remove_button)

        return container
