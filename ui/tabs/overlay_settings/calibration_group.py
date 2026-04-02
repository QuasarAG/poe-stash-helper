"""Calibration controls for the overlay settings tab."""

from __future__ import annotations

import config as _config

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class CalibrationGroup(QGroupBox):
    """
    Owns the stash-grid calibration controls.

    This group is responsible for the five spinboxes that define where the
    stash grid is drawn on screen.
    """

    params_changed = pyqtSignal(int, int, float, int, int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Stash Grid Calibration  (all values in screen pixels)", parent)
        self._build_ui()
        self.restore_from_config()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self._grid_x_spinbox = self._create_spinbox_row(
            layout,
            "Grid X  (screen px, left edge):",
            minimum=0,
            maximum=5000,
            tooltip="Absolute X pixel position of the stash grid's left edge on screen",
        )
        self._grid_y_spinbox = self._create_spinbox_row(
            layout,
            "Grid Y  (screen px, top edge):",
            minimum=0,
            maximum=5000,
            tooltip="Absolute Y pixel position of the stash grid's top edge on screen",
        )
        self._cell_size_spinbox = self._create_spinbox_row(
            layout,
            "Cell size  (px, decimals OK):",
            minimum=1.0,
            maximum=300.0,
            tooltip="Width/height of one stash cell in pixels — decimals for fine-tuning",
            is_float=True,
        )
        self._columns_spinbox = self._create_spinbox_row(
            layout,
            "Columns:",
            minimum=1,
            maximum=24,
            tooltip="Number of grid columns (12 for normal tabs, 24 for quad tabs)",
        )
        self._rows_spinbox = self._create_spinbox_row(
            layout,
            "Rows:",
            minimum=1,
            maximum=24,
            tooltip="Number of grid rows (12 for normal tabs, 24 for quad tabs)",
        )

        tip_label = QLabel(
            "Tip: Unlock the grid from the sidebar, drag and resize it over your stash,\n"
            "then lock it.  These values update automatically as you drag."
        )
        tip_label.setStyleSheet("color:#666; font-size:10px;")
        layout.addWidget(tip_label)

    def _create_spinbox_row(
        self,
        parent_layout: QVBoxLayout,
        label_text: str,
        minimum,
        maximum,
        tooltip: str = "",
        is_float: bool = False,
    ):
        row = QHBoxLayout()

        label = QLabel(label_text)
        label.setMinimumWidth(160)
        row.addWidget(label)

        if is_float:
            spinbox = QDoubleSpinBox()
            spinbox.setRange(float(minimum), float(maximum))
            spinbox.setDecimals(2)
            spinbox.setSingleStep(0.5)
        else:
            spinbox = QSpinBox()
            spinbox.setRange(int(minimum), int(maximum))

        spinbox.setMinimumWidth(80)
        if tooltip:
            spinbox.setToolTip(tooltip)
        spinbox.valueChanged.connect(self._emit_if_valid)

        row.addWidget(spinbox)
        row.addStretch()
        parent_layout.addLayout(row)
        return spinbox

    def restore_from_config(self) -> None:
        """Load saved grid values from config into the spinboxes."""
        grid = _config.get("stash_grid") or {}
        updates = [
            (self._grid_x_spinbox, grid.get("grid_screen_x", 100)),
            (self._grid_y_spinbox, grid.get("grid_screen_y", 140)),
            (self._cell_size_spinbox, float(grid.get("cell_size", 52.0))),
            (self._columns_spinbox, grid.get("cols", 12)),
            (self._rows_spinbox, grid.get("rows", 12)),
        ]
        for spinbox, value in updates:
            spinbox.blockSignals(True)
            spinbox.setValue(value)
            spinbox.blockSignals(False)

    def update_display(self, grid_x: int, grid_y: int, cell_size: float, columns: int, rows: int) -> None:
        """Update the spinboxes from the live overlay without causing a feedback loop."""
        updates = [
            (self._grid_x_spinbox, int(grid_x)),
            (self._grid_y_spinbox, int(grid_y)),
            (self._cell_size_spinbox, float(cell_size)),
            (self._columns_spinbox, int(columns)),
            (self._rows_spinbox, int(rows)),
        ]
        for spinbox, value in updates:
            spinbox.blockSignals(True)
            spinbox.setValue(value)
            spinbox.blockSignals(False)

    def save_to_config(self) -> None:
        """Persist the current calibration values."""
        _config.set_key(
            "stash_grid",
            {
                "grid_screen_x": int(self._grid_x_spinbox.value()),
                "grid_screen_y": int(self._grid_y_spinbox.value()),
                "cell_size": float(self._cell_size_spinbox.value()),
                "cols": int(self._columns_spinbox.value()),
                "rows": int(self._rows_spinbox.value()),
            },
        )

    def _emit_if_valid(self) -> None:
        grid_x = int(self._grid_x_spinbox.value())
        grid_y = int(self._grid_y_spinbox.value())
        cell_size = float(self._cell_size_spinbox.value())
        columns = int(self._columns_spinbox.value())
        rows = int(self._rows_spinbox.value())

        if cell_size < 1.0 or columns < 1 or rows < 1:
            return

        self.params_changed.emit(grid_x, grid_y, cell_size, columns, rows)
