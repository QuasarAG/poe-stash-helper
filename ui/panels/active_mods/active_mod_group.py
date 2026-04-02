from __future__ import annotations
"""One active-mod group.

An active mod group is a container of active modifier rules that share the same
behaviour mode. The wording is intentionally explicit so the user interface
reads like matching logic rather than a blacklist or deny-list tool.
"""

from typing import List

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QCheckBox, QLabel, QSpinBox, QComboBox, QPushButton, QLineEdit

from logic.mod_scorer import ModFilter

from models import ActiveModBehaviour
from .common import ACTIVE_MOD_DRAG_MIME, BEHAVIOUR_LABELS, BEHAVIOUR_TIPS, HEADER_BORDERS, HEADER_COLORS, qss_button
from .active_mod_row import ActiveModRow


class ActiveModGroup(QWidget):
    """A group containing zero or more active mod rows.

    The group behaviour tells the scorer how the rows inside it should be
    interpreted.
    """

    changed = pyqtSignal()
    remove_requested = pyqtSignal(object)

    def __init__(self, behaviour: ActiveModBehaviour = ActiveModBehaviour.AND, slot: str = "",
                 count_min: int = 1, count_max: int = 0, parent=None):
        super().__init__(parent)
        self._behaviour = ActiveModBehaviour(behaviour)
        self._slot = slot
        self._count_min = count_min
        self._count_max = count_max
        self._rows: List[ActiveModRow] = []
        self._enabled = True
        self._inline_results: list[tuple[str, str]] = []
        self.setAcceptDrops(True)
        self._build()

    @property
    def behaviour(self) -> ActiveModBehaviour:
        return self._behaviour

    @property
    def enabled(self) -> bool:
        return self._enabled

    def get_active_filters(self) -> list[ModFilter]:
        if not self._enabled:
            return []
        return [row.filter for row in self._rows if row.enabled]

    def add_mod(self, filt: ModFilter) -> None:
        row = ActiveModRow(filt, self._slot)
        row.changed.connect(self.changed)
        row.removed.connect(self._remove_row)
        self._rows.append(row)
        self._body_layout.addWidget(row)
        self._update_empty_hint()
        self.changed.emit()

    def clear(self) -> None:
        for row in list(self._rows):
            self._remove_row(row, emit_signal=False)
        self.changed.emit()

    def set_slot(self, slot: str) -> None:
        self._slot = slot

    def count_range(self) -> tuple[int, int]:
        return (self._count_min_spinbox.value(), self._count_max_spinbox.value())

    def _build(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setSpacing(0)
        outer_layout.setContentsMargins(0, 0, 0, 4)

        header = QFrame()
        self._header = header
        self._apply_header_style()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 3, 4, 3)
        header_layout.setSpacing(4)

        self._enable_checkbox = QCheckBox()
        self._enable_checkbox.setChecked(True)
        self._enable_checkbox.setFixedWidth(18)
        self._enable_checkbox.setToolTip("Enable or disable this active mod group")
        self._enable_checkbox.toggled.connect(self._on_enable_toggled)
        header_layout.addWidget(self._enable_checkbox)

        self._behaviour_label = QLabel(self._behaviour)
        self._behaviour_label.setStyleSheet("color:#ccccee;font-weight:bold;font-size:9px;min-width:36px;")
        header_layout.addWidget(self._behaviour_label)

        self._count_label = QLabel("min:")
        self._count_label.setStyleSheet("color:#ccaa66;font-size:8px;")
        self._count_min_spinbox = QSpinBox()
        self._count_min_spinbox.setRange(0, 99)
        self._count_min_spinbox.setValue(self._count_min)
        self._count_min_spinbox.setFixedWidth(42)
        self._count_min_spinbox.setStyleSheet(
            "QSpinBox{background:#1e1e30;border:1px solid #555522;border-radius:2px;"
            "color:#ccaa66;padding:1px;font-size:8px;}"
        )
        self._count_max_label = QLabel("max:")
        self._count_max_label.setStyleSheet("color:#ccaa66;font-size:8px;")
        self._count_max_spinbox = QSpinBox()
        self._count_max_spinbox.setRange(0, 99)
        self._count_max_spinbox.setValue(self._count_max)
        self._count_max_spinbox.setFixedWidth(42)
        self._count_max_spinbox.setStyleSheet(self._count_min_spinbox.styleSheet())
        self._count_min_spinbox.valueChanged.connect(self.changed)
        self._count_max_spinbox.valueChanged.connect(self.changed)
        header_layout.addWidget(self._count_label)
        header_layout.addWidget(self._count_min_spinbox)
        header_layout.addWidget(self._count_max_label)
        header_layout.addWidget(self._count_max_spinbox)
        self._set_count_controls_visible(self._behaviour == ActiveModBehaviour.COUNT)

        header_layout.addStretch()

        self._behaviour_combo = QComboBox()
        for behaviour in BEHAVIOUR_LABELS:
            self._behaviour_combo.addItem(behaviour)
        self._behaviour_combo.setCurrentText(self._behaviour.value)
        self._behaviour_combo.setFixedWidth(68)
        self._behaviour_combo.setStyleSheet(
            "QComboBox{background:#1a1a2a;border:1px solid #444466;border-radius:3px;"
            "color:#ccccff;font-size:9px;font-weight:bold;padding:1px 4px;}"
        )
        self._behaviour_combo.setToolTip("\n".join(f"{key}: {value}" for key, value in BEHAVIOUR_TIPS.items()))
        self._behaviour_combo.currentTextChanged.connect(self._on_behaviour_changed)
        header_layout.addWidget(self._behaviour_combo)

        remove_button = QPushButton("✕")
        remove_button.setFixedSize(18, 18)
        remove_button.setToolTip("Delete this active mod group (the last one will be cleared instead)")
        remove_button.setStyleSheet(qss_button("#2a1010", "#993333", "#ff6666", "0px", "3px"))
        remove_button.clicked.connect(lambda: self.remove_requested.emit(self))
        header_layout.addWidget(remove_button)

        outer_layout.addWidget(header)

        self._body = QWidget()
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setSpacing(1)
        self._body_layout.setContentsMargins(8, 3, 4, 3)

        self._empty_hint = QLabel("  (no active mods yet — this group currently matches everything)")
        self._empty_hint.setStyleSheet("color:#443355;font-size:8px;font-style:italic;")
        self._body_layout.addWidget(self._empty_hint)

        add_bar = QHBoxLayout()
        add_bar.setSpacing(3)
        add_bar.setContentsMargins(0, 3, 0, 1)

        self._inline_search = QLineEdit()
        self._inline_search.setPlaceholderText("Search and add active mod…")
        self._inline_search.setStyleSheet(
            "QLineEdit{background:#13131e;border:1px solid #2a2a44;border-radius:3px;"
            "color:#aaaacc;padding:2px 6px;font-size:8px;}"
            "QLineEdit:focus{border-color:#5555aa;}"
        )
        self._inline_search.textChanged.connect(self._on_inline_search_changed)
        self._inline_search.returnPressed.connect(self._on_inline_add_first)

        self._inline_add_button = QPushButton("+ Add Mod")
        self._inline_add_button.setFixedWidth(64)
        self._inline_add_button.setStyleSheet(
            "QPushButton{background:#1a2a1a;border:1px solid #336633;border-radius:3px;"
            "color:#88cc88;padding:2px 4px;font-size:8px;}"
            "QPushButton:hover{background:#223322;color:#aaffaa;}"
        )
        self._inline_add_button.clicked.connect(self._on_inline_add_first)

        add_bar.addWidget(self._inline_search, 1)
        add_bar.addWidget(self._inline_add_button)
        self._body_layout.addLayout(add_bar)

        outer_layout.addWidget(self._body)

    def _apply_header_style(self) -> None:
        background = HEADER_COLORS.get(self._behaviour, "#1e1e30")
        border = HEADER_BORDERS.get(self._behaviour, "#444466")
        self._header.setStyleSheet(
            f"QFrame{{background:{background};border:1px solid {border};border-radius:4px;margin-bottom:1px;}}"
        )

    def _set_count_controls_visible(self, visible: bool) -> None:
        for widget in (self._count_label, self._count_min_spinbox, self._count_max_label, self._count_max_spinbox):
            widget.setVisible(visible)

    def _on_behaviour_changed(self, text: str) -> None:
        self._behaviour = ActiveModBehaviour(text)
        self._behaviour_label.setText(text)
        self._apply_header_style()
        self._set_count_controls_visible(self._behaviour == ActiveModBehaviour.COUNT)
        self.changed.emit()

    def _on_enable_toggled(self, checked: bool) -> None:
        self._enabled = checked
        self._body.setVisible(checked)
        self.changed.emit()

    def _on_inline_search_changed(self, text: str) -> None:
        text = text.strip().lower()
        if not text:
            self._inline_results = []
            return
        words = text.split()
        try:
            from logic.mod_query import mods_for_slot, PSEUDO_DB
            from data.mod_data import MOD_DB
            if self._slot and self._slot != "Any":
                pseudo_entries = [
                    (entry.get("label", ""), stat_id)
                    for stat_id, entry in PSEUDO_DB.items()
                    if not entry.get("slots") or self._slot in entry.get("slots", [])
                ]
                real_entries = [
                    (entry.get("label", ""), entry["stat_id"])
                    for entry in mods_for_slot(self._slot)
                    if not entry["stat_id"].startswith("pseudo.")
                ]
                combined_entries = [(label, stat_id) for label, stat_id in pseudo_entries + real_entries]
            else:
                combined_entries = (
                    [(entry.get("label", ""), stat_id) for stat_id, entry in PSEUDO_DB.items()] +
                    [(entry.get("label", ""), stat_id) for stat_id, entry in MOD_DB.items()]
                )

            def fuzzy_match(label: str) -> bool:
                lowered = label.lower()
                return all(word in lowered for word in words)

            self._inline_results = [
                (stat_id, label) for label, stat_id in combined_entries if fuzzy_match(label)
            ][:20]
        except Exception:
            self._inline_results = []

    def _on_inline_add_first(self) -> None:
        text = self._inline_search.text().strip()
        if not text:
            return
        self._on_inline_search_changed(text)
        if self._inline_results:
            stat_id, label = self._inline_results[0]
            self.add_mod(ModFilter(stat_id=stat_id, label=label))
            self._inline_search.clear()
            self._inline_results = []

    def _remove_row(self, row: ActiveModRow, emit_signal: bool = True) -> None:
        if row in self._rows:
            self._rows.remove(row)
            self._body_layout.removeWidget(row)
            row.hide()
            row.setParent(None)
            row.deleteLater()
        self._update_empty_hint()
        if emit_signal:
            self.changed.emit()

    def _update_empty_hint(self) -> None:
        self._empty_hint.setVisible(len(self._rows) == 0)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(ACTIVE_MOD_DRAG_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        if not event.mimeData().hasFormat(ACTIVE_MOD_DRAG_MIME):
            return
        payload = bytes(event.mimeData().data(ACTIVE_MOD_DRAG_MIME)).decode()
        parts = payload.split("|", 2)
        if len(parts) < 3:
            return
        stat_id, label, source_group_id = parts[0], parts[1], parts[2]

        if source_group_id == str(id(self)):
            event.acceptProposedAction()
            return

        self.add_mod(ModFilter(stat_id=stat_id, label=label))

        panel = getattr(self, "_panel_ref", None)
        if panel is None:
            panel = self.parentWidget()
            while panel and panel.__class__.__name__ != "ActiveModPanel":
                panel = panel.parentWidget()
        if panel:
            try:
                panel._remove_mod_from_group_by_id(int(source_group_id), stat_id)
            except Exception:
                pass
        event.acceptProposedAction()
