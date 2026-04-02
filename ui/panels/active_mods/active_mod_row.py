from __future__ import annotations
"""Single editable active-mod condition row.

This widget used to live inside one very large file together with the group and
panel classes. It is now split out so the reader can understand one level of the
user interface at a time.
"""

import copy
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QMimeData, QByteArray
from PyQt5.QtGui import QColor, QFont, QDrag, QPainter, QCursor, QFontMetrics, QBrush, QPen, QPixmap
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QSizePolicy, QCheckBox, QComboBox, QLineEdit, QPushButton

from logic.mod_scorer import ModFilter
from logic.mod_query import num_tiers, tier_range, is_pseudo

from .common import ACTIVE_MOD_DRAG_MIME, qss_button


class ActiveModRow(QWidget):
    """One condition row inside an active-mod group.

    Layout:
        [drag handle] [enabled checkbox] [label] [tier or influence picker]
        [min] [max] [remove button]
    """

    changed = pyqtSignal()
    removed = pyqtSignal(object)

    def __init__(self, filt: ModFilter, slot: str = "", parent=None):
        super().__init__(parent)
        self._filt = filt
        self._slot = slot
        self._drag_start: Optional[QPoint] = None
        self._build()

    @property
    def enabled(self) -> bool:
        return self._chk.isChecked()

    @property
    def filter(self) -> ModFilter:
        """Return a copy of the current filter using the live widget values."""
        filt_copy = copy.copy(self._filt)
        filt_copy.label = self._label.toolTip() or self._filt.label

        if self._filt.stat_id == "meta.has_influence":
            if self._influence_cb is not None:
                filt_copy.meta_influence_value = self._influence_cb.currentData() or ""
            filt_copy.min = None
            filt_copy.max = None
            return filt_copy

        if self._min_edit is not None:
            filt_copy.min = self._get_float(self._min_edit)
        if self._max_edit is not None:
            filt_copy.max = self._get_float(self._max_edit)

        if self._tier_cb is not None:
            tier_data = self._tier_cb.currentData()
            filt_copy.min_tier = tier_data if tier_data is not None else -1
            if filt_copy.min_tier > 0:
                tier_values = tier_range(filt_copy.stat_id, filt_copy.min_tier, self._slot)
                if tier_values:
                    filt_copy.min = float(tier_values[0])
                    filt_copy.max = None
        return filt_copy

    def _build(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 1, 0, 1)
        layout.setSpacing(3)

        self._drag_handle = QLabel("⠿")
        self._drag_handle.setFixedWidth(12)
        self._drag_handle.setStyleSheet("color:#444466; font-size:13px;")
        self._drag_handle.setCursor(QCursor(Qt.SizeAllCursor))
        self._drag_handle.setToolTip("Drag to reorder or move to another active mod group")
        layout.addWidget(self._drag_handle)

        self._chk = QCheckBox()
        self._chk.setChecked(True)
        self._chk.setFixedWidth(16)
        self._chk.toggled.connect(self.changed)
        layout.addWidget(self._chk)

        label_text = self._filt.label
        pseudo = is_pseudo(self._filt.stat_id)
        is_meta = self._filt.stat_id.startswith("meta.")
        if pseudo:
            display_text = f"pseudo  {label_text}"
        elif is_meta:
            display_text = f"meta  {label_text}"
        else:
            display_text = label_text

        self._label = QLabel(display_text)
        self._label.setMinimumWidth(120)
        self._label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._label.setToolTip(self._filt.label)
        if pseudo:
            self._label.setStyleSheet("color:#cc99ff; font-size:9px; font-style:italic;")
        elif is_meta:
            self._label.setStyleSheet("color:#66dddd; font-size:9px; font-style:italic;")
        else:
            self._label.setStyleSheet("color:#ccccee; font-size:9px;")
        layout.addWidget(self._label, 1)

        if self._filt.stat_id == "meta.has_influence":
            self._build_influence_selector(layout)
        else:
            self._build_tier_and_range_controls(layout)

        remove_button = QPushButton("✕")
        remove_button.setFixedSize(18, 18)
        remove_button.setStyleSheet(qss_button("#2a1a1a", "#884444", "#cc6666", "0px 2px", "3px"))
        remove_button.clicked.connect(lambda: self.removed.emit(self))
        layout.addWidget(remove_button)

    def _build_influence_selector(self, layout: QHBoxLayout) -> None:
        self._influence_cb = QComboBox()
        self._influence_cb.setFixedWidth(150)
        self._influence_cb.setStyleSheet(
            "QComboBox{background:#1a2a2a;border:1px solid #226655;border-radius:3px;"
            "color:#66dddd;padding:1px 4px;font-size:8px;}"
            "QComboBox QAbstractItemView{background:#1a1a2e;color:#e0e0e0;font-size:9px;}"
        )
        influence_labels = {
            "any": "Any Influence",
            "shaper": "Shaper",
            "elder": "Elder",
            "crusader": "Crusader",
            "redeemer": "Redeemer",
            "warlord": "Warlord",
            "hunter": "Hunter",
            "searing_exarch": "Searing Exarch",
            "eater_of_worlds": "Eater of Worlds",
        }
        self._influence_cb.addItem("— choose influence —", "")
        for key, display in influence_labels.items():
            self._influence_cb.addItem(display, key)
        saved = getattr(self._filt, "meta_influence_value", "") or ""
        index = self._influence_cb.findData(saved)
        if index >= 0:
            self._influence_cb.setCurrentIndex(index)
        self._influence_cb.currentIndexChanged.connect(self._on_influence_changed)
        layout.addWidget(self._influence_cb)
        self._tier_cb = None
        self._min_edit = None
        self._max_edit = None

    def _build_tier_and_range_controls(self, layout: QHBoxLayout) -> None:
        self._influence_cb = None
        self._tier_cb = QComboBox()
        self._tier_cb.setFixedWidth(110)
        self._tier_cb.setStyleSheet(
            "QComboBox{background:#1e1e30;color:#e0e0e0;border:1px solid #3a3a58;"
            "border-radius:2px;padding:1px 3px;font-size:8px;}"
            "QComboBox QAbstractItemView{background:#1a1a2e;color:#e0e0e0;font-size:9px;}"
        )
        self._tier_cb.addItem("Custom", -1)
        self._tier_cb.addItem("Any", 0)
        tier_count = num_tiers(self._filt.stat_id, self._slot)
        for tier_index in range(1, tier_count + 1):
            tier_values = tier_range(self._filt.stat_id, tier_index, self._slot)
            low, high = tier_values if tier_values else (0, 0)
            self._tier_cb.addItem(f"T{tier_index}  ({low:.0f}–{high:.0f})", tier_index)
        saved_tier = getattr(self._filt, "min_tier", 0) or 0
        index = self._tier_cb.findData(saved_tier)
        if index >= 0:
            self._tier_cb.setCurrentIndex(index)
        self._tier_cb.currentIndexChanged.connect(self._on_tier_changed)
        layout.addWidget(self._tier_cb)

        self._min_edit = QLineEdit()
        self._max_edit = QLineEdit()
        for editor, placeholder in ((self._min_edit, "min"), (self._max_edit, "max")):
            editor.setFixedWidth(46)
            editor.setPlaceholderText(placeholder)
            editor.setStyleSheet(
                "QLineEdit{background:#1a1a2e;border:1px solid #33335a;border-radius:2px;"
                "color:#aaaacc;padding:1px 3px;font-size:8px;}"
            )
            editor.textChanged.connect(self.changed)
            layout.addWidget(editor)

        if self._filt.min is not None:
            self._min_edit.setText(str(self._filt.min))
        if self._filt.max is not None:
            self._max_edit.setText(str(self._filt.max))
        self._on_tier_changed()

    def _on_influence_changed(self) -> None:
        if self._influence_cb is not None:
            self._filt.meta_influence_value = self._influence_cb.currentData() or ""
        self.changed.emit()

    def _on_tier_changed(self) -> None:
        if self._tier_cb is None or self._min_edit is None or self._max_edit is None:
            return
        tier_data = self._tier_cb.currentData()
        is_custom = tier_data == -1
        for editor in (self._min_edit, self._max_edit):
            editor.setReadOnly(not is_custom)
            editor.setStyleSheet(
                "QLineEdit{background:#1a1a2e;border:1px solid "
                + ("#4444aa" if is_custom else "#1e1e3a")
                + ";border-radius:2px;color:"
                + ("#aaaaff" if is_custom else "#444466")
                + ";padding:1px 3px;font-size:8px;}"
            )
            if not is_custom:
                editor.clear()
        self.changed.emit()

    @staticmethod
    def _get_float(editor: Optional[QLineEdit]) -> Optional[float]:
        if editor is None:
            return None
        text = editor.text().strip()
        try:
            return float(text)
        except ValueError:
            return None

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            handle_rect = self._drag_handle.rect().translated(self._drag_handle.mapTo(self, QPoint(0, 0)))
            if handle_rect.contains(event.pos()):
                self._drag_start = event.pos()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_start is None:
            return
        if (event.pos() - self._drag_start).manhattanLength() <= 6:
            return

        drag = QDrag(self)
        mime = QMimeData()

        parent_group = self.parentWidget()
        if parent_group is not None:
            parent_group = parent_group.parentWidget()
        group_id = id(parent_group) if parent_group is not None else 0

        payload = f"{self._filt.stat_id}|{self._filt.label}|{group_id}"
        mime.setData(ACTIVE_MOD_DRAG_MIME, QByteArray(payload.encode()))
        drag.setMimeData(mime)

        label_text = self._filt.label[:40] + ("…" if len(self._filt.label) > 40 else "")
        font = QFont("Segoe UI", 9)
        metrics = QFontMetrics(font)
        pixmap_width = metrics.horizontalAdvance(label_text) + 20
        pixmap_height = metrics.height() + 10
        pixmap = QPixmap(pixmap_width, pixmap_height)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(30, 20, 50, 210)))
        painter.setPen(QPen(QColor(140, 100, 220, 220), 1))
        painter.drawRoundedRect(0, 0, pixmap_width - 1, pixmap_height - 1, 4, 4)
        painter.setFont(font)
        painter.setPen(QColor(200, 170, 255))
        painter.drawText(10, pixmap_height - 6, label_text)
        painter.end()
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap_width // 2, pixmap_height // 2))

        drag.exec_(Qt.MoveAction)
        self._drag_start = None

    def mouseReleaseEvent(self, event) -> None:
        self._drag_start = None
