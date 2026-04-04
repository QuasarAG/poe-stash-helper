from __future__ import annotations

"""Widget that owns the wrapping equipment-slot bar.

This extracts the slot-bar user interface out of `ScanFiltersTab` so the tab
can focus more on application behaviour and less on low-level widget layout.
"""

from PyQt5.QtCore import QSize, QPoint, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QMenu,
)

ROW_HEIGHT = 26
FLOW_SPACING = 4

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

    def __init__(self, widgets: list[QWidget], spacing: int = FLOW_SPACING, parent: QWidget = None):
        super().__init__(parent)
        self._widgets = widgets
        self._spacing = spacing
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        for widget in widgets:
            widget.setParent(self)

        self._relayout()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()
        if self.parent():
            self.parent().updateGeometry()

    def _relayout(self) -> None:
        """Position visible widgets and compute exact wrapped height."""
        available_width = max(self.width(), 200)
        spacing = self._spacing

        x = 0
        y = 0
        row_height = 0

        visible_widgets = [widget for widget in self._widgets if not widget.isHidden()]

        for widget in visible_widgets:
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

        total_height = (y + row_height) if visible_widgets else 0
        self.setMinimumHeight(total_height)
        self.setMaximumHeight(total_height)

    def sizeHint(self) -> QSize:
        return QSize(200, self.maximumHeight() or ROW_HEIGHT)


class SlotBar(QWidget):
    """Wrapping bar of slot buttons plus the permanent add-slot button."""

    slot_clicked = pyqtSignal(str)
    slot_remove_requested = pyqtSignal(str)
    add_slot_requested = pyqtSignal()
    add_slot_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._slot_button_widgets: dict[str, QWidget] = {}
        self._add_slot_button_should_be_visible: bool = False
        self._flow_widget: _SlotFlowWidget | None = None
        self._build()

    def _build(self) -> None:
        self.setObjectName("slotBar")
        self.setStyleSheet(
            "#slotBar { background:#161626; border:1px solid #2a2a3e; border-radius:3px; }"
        )

        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(3)
        self._layout.setContentsMargins(4, 3, 4, 3)

        # Important: the outer bar should shrink/grow to match the wrapped flow.
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._add_slot_button = QPushButton("＋ Add Slot")
        self._add_slot_button.setToolTip("Add an equipment slot with its own mod list")
        self._add_slot_button.setStyleSheet(
            "background:#1e2a1e; color:#88cc88; border:1px solid #446644;"
            " border-radius:3px; padding:3px 10px; font-size:10px; font-weight:bold;"
        )
        self._add_slot_button.setFixedHeight(ROW_HEIGHT)
        self._add_slot_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._add_slot_button.clicked.connect(self.add_slot_requested.emit)
        self._add_slot_button.setVisible(self._add_slot_button_should_be_visible)

        self._flow_widget = _SlotFlowWidget([], spacing=FLOW_SPACING, parent=self)
        self._layout.addWidget(self._flow_widget)

        self._sync_height_to_flow()

    def _sync_height_to_flow(self) -> None:
        """Force the outer slot bar to exactly match the wrapped flow height."""
        if self._flow_widget is None:
            flow_height = 0
        else:
            flow_height = self._flow_widget.sizeHint().height()

        margins = self._layout.contentsMargins()
        total_height = margins.top() + flow_height + margins.bottom()

        self.setMinimumHeight(total_height)
        self.setMaximumHeight(total_height)
        self.updateGeometry()

    def set_add_slot_button_visible(self, visible: bool) -> None:
        self._add_slot_button_should_be_visible = visible
        self._add_slot_button.setVisible(visible)

        if self._flow_widget is not None:
            self._flow_widget._relayout()

        self._sync_height_to_flow()

    def rebuild(self, active_slot: str, slot_names: list[str]) -> None:
        """Rebuild the wrapping slot buttons from scratch."""
        old_flow_widget = self._flow_widget

        self._slot_button_widgets = {}
        all_flow_widgets: list[QWidget] = []

        # Keep add-slot inside the same wrapped flow as the slot chips.
        self._add_slot_button.setParent(self)
        self._add_slot_button.setVisible(self._add_slot_button_should_be_visible)
        if self._add_slot_button_should_be_visible:
            all_flow_widgets.append(self._add_slot_button)

        for slot_name in list(slot_names or []):
            container = self._make_slot_button_container(
                slot_name=slot_name,
                is_active=(slot_name == active_slot),
            )
            self._slot_button_widgets[slot_name] = container
            all_flow_widgets.append(container)

        new_flow_widget = _SlotFlowWidget(all_flow_widgets, spacing=FLOW_SPACING, parent=self)

        if old_flow_widget is not None:
            self._layout.replaceWidget(old_flow_widget, new_flow_widget)
            old_flow_widget.deleteLater()
        else:
            self._layout.addWidget(new_flow_widget)

        self._flow_widget = new_flow_widget
        self._sync_height_to_flow()

    def set_active_slot(self, active_slot: str) -> None:
        """Update button styles so only one slot looks active."""
        for slot_name, container in self._slot_button_widgets.items():
            button = container.findChild(QPushButton, f"slot_button_{slot_name}")
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
        """Create one slot chip: main slot button + small remove button."""
        container = QWidget()
        container.setStyleSheet("background:transparent; border:none;")
        container.setFixedHeight(ROW_HEIGHT)
        container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        slot_button = QPushButton(slot_name)
        slot_button.setObjectName(f"slot_button_{slot_name}")
        slot_button.setCheckable(True)
        slot_button.setChecked(is_active)
        slot_button.setFixedHeight(ROW_HEIGHT)
        slot_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        slot_button.setStyleSheet(
            _SLOT_BUTTON_ACTIVE_STYLE if is_active else _SLOT_BUTTON_INACTIVE_STYLE
        )
        slot_button.setToolTip(
            "Any — mods common to all item types"
            if slot_name == "Any"
            else f"View/edit mods for: {slot_name}"
        )
        slot_button.clicked.connect(
            lambda checked=False, s=slot_name: self.slot_clicked.emit(s)
        )
        row.addWidget(slot_button)

        remove_button = QPushButton("×")
        remove_button.setFixedSize(16, ROW_HEIGHT)
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

        # Match the container width exactly to the visible contents.
        total_width = slot_button.sizeHint().width() + remove_button.width()
        container.setFixedWidth(total_width)

        return container