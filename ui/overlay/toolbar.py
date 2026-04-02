"""
ui/overlay/toolbar.py
─────────────────────────────────────────────────────────────────────────────
PURPOSE
    HudToolbar — the compact sidebar that appears on top of the game window.

    This is the floating control strip the user sees while playing.
    It contains quick-access buttons and dropdowns so the user never needs
    to alt-tab out of the game to perform common actions.

CONTENTS
    • Grip handle — drag to reposition the toolbar anywhere on screen
    • TAB dropdown — switch which stash tab is being scanned
    • SET dropdown — switch the active loadout (mod filter preset)
    • ≡ button — open the Mod Filters window
    • ⚙ button — open the Account/Settings window
    • 🔒/🔓 button — lock or unlock the alignment grid
    • 👁 button — toggle the item outline overlay on/off

TWO ORIENTATIONS
    VERTICAL   — tall narrow strip, default position: left edge of screen
    HORIZONTAL — wide thin strip, default position: top of screen

    Calling set_orientation(horizontal=True/False) rebuilds the layout.

SIGNALS
    sig_scan            — user clicked the Scan button (if present)
    sig_toggle          — user clicked the eye toggle
    sig_open_config     — user clicked the ⚙ button
    sig_open_filters    — user clicked the ≡ button
    sig_tab_changed     — user picked a different stash tab (carries tab ID string)
    sig_loadout_changed — user picked a different loadout (carries name string)
    sig_lock_toggle     — user clicked the lock/unlock button

RELATIONSHIP TO OTHER FILES
    • stash_overlay.py owns the HudToolbar and connects its signals to the
      overlay's lock/toggle/scan logic.
    • AppController connects sig_open_config and sig_open_filters to show the
      MainWindow.
    • loadout_store.py is polled every 3 seconds to keep the SET dropdown
      current without requiring an explicit update call.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing  import Optional

from PyQt5.QtCore    import Qt, QTimer, pyqtSignal
from PyQt5.QtGui     import QCursor
from PyQt5.QtWidgets import (
    QWidget, QApplication, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QComboBox, QFrame,
)

# Path to the loadouts file — polled every 3s to auto-refresh the SET dropdown
_LOADOUTS_FILE = Path(__file__).parent.parent.parent / "data" / "loadouts.json"

# Pixel size for all toolbar buttons (width = height = this value)
_BUTTON_SIZE = 26

# ── Stylesheet for the entire toolbar ─────────────────────────────────────────
# rgba() colours are semi-transparent so the game shows through slightly.
_TOOLBAR_STYLESHEET = """
QWidget {
    background: rgba(22, 22, 22, 230);
    color: #e0e0e0;
    font-family: "Segoe UI";
    font-size: 10px;
}
QPushButton {
    background: rgba(50, 50, 50, 220);
    color: #e0e0e0;
    border: 1px solid #555555;
    border-radius: 2px;
    font-size: 13px;
    padding: 0px;
}
QPushButton:hover   { background: rgba(75, 75, 75, 240); color: #ffffff; border-color: #888; }
QPushButton:pressed { background: rgba(25, 25, 25, 255); }
QPushButton#scan    { color: #ffffff; border-color: #777; font-weight: bold; }
QPushButton#lock_on  { color: #88ff88; border-color: #666; }
QPushButton#lock_off { color: #ff9999; border-color: #666; }
QPushButton#eye_on   { color: #aaaaff; border-color: #666; }
QPushButton#eye_off  { color: #666666; border-color: #444; }
QPushButton#arrow    { background: rgba(40,40,40,220); color: #cccccc;
                       font-size: 11px; border-color: #555; }
QPushButton#arrow:hover { background: rgba(70,70,70,240); color: #ffffff; }
QLabel { color: #bbbbbb; font-size: 9px; font-weight: bold; letter-spacing: 1px; }
QLabel#name_lbl {
    color: #ffffff; font-size: 10px; font-weight: bold;
    background: rgba(45, 45, 45, 240); border: 1px solid #606060;
    border-radius: 2px; padding: 2px 4px; min-width: 40px;
}
QFrame#sep_v { background: #444444; max-width:  1px; }
QFrame#sep_h { background: #444444; max-height: 1px; }
"""

# ── Compact dropdown style (shared by TAB and SET dropdowns) ──────────────────
_COMPACT_DROPDOWN_STYLE = """
QComboBox {
    background: rgba(50, 50, 50, 220);
    color: #ffffff;
    border: 1px solid #666666;
    border-radius: 2px;
    font-size: 9px;
    font-weight: bold;
    padding: 1px;
}
QComboBox:hover { background: rgba(70, 70, 70, 240); border-color: #999; }
QComboBox QAbstractItemView {
    background: #2a2a2a;
    color: #ffffff;
    border: 1px solid #777;
    font-size: 11px;
    padding: 4px;
    min-width: 180px;
    selection-background-color: #445566;
}
QComboBox::drop-down { border: none; width: 0px; }
"""


def _make_vertical_separator() -> QFrame:
    """Create a thin vertical line for use in horizontal layouts."""
    separator = QFrame()
    separator.setObjectName("sep_v")
    separator.setFrameShape(QFrame.VLine)
    separator.setFixedWidth(1)
    separator.setStyleSheet("background:#444444;")
    return separator


def _make_horizontal_separator() -> QFrame:
    """Create a thin horizontal line for use in vertical layouts."""
    separator = QFrame()
    separator.setObjectName("sep_h")
    separator.setFrameShape(QFrame.HLine)
    separator.setFixedHeight(1)
    separator.setStyleSheet("background:#444444;")
    return separator


class HudToolbar(QWidget):
    """
    Compact always-on-top sidebar / topbar HUD.

    The user interacts with this while PoE is running — it must never
    steal focus or interfere with the game.
    """

    # ── Signals — connected by stash_overlay.py and AppController ──────────────────
    sig_scan            = pyqtSignal()       # Scan button clicked
    sig_toggle          = pyqtSignal()       # Eye toggle clicked
    sig_open_config     = pyqtSignal()       # ⚙ button clicked
    sig_open_filters    = pyqtSignal()       # ≡ button clicked
    sig_tab_changed     = pyqtSignal(str)    # TAB dropdown changed; carries tab ID
    sig_loadout_changed = pyqtSignal(str)    # SET dropdown changed; carries loadout name
    sig_lock_toggle     = pyqtSignal()       # 🔒/🔓 button clicked

    def __init__(self, parent=None):
        super().__init__(parent)

        # Window: frameless, always on top, doesn't appear in taskbar
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(_TOOLBAR_STYLESHEET)

        # State
        self._drag_start_pos:  Optional[QCursor] = None
        self._stash_tabs:      list[dict]        = []
        self._loadout_names:   list[str]         = []
        self._overlay_visible: bool              = True
        self._grid_locked:     bool              = True
        self._is_horizontal:   bool              = False

        self._build_layout()
        self._refresh_loadout_dropdown()

        # Poll loadouts.json every 3 seconds so the SET dropdown stays current
        # without requiring an explicit update call after each save.
        self._loadout_refresh_timer = QTimer(self)
        self._loadout_refresh_timer.timeout.connect(self._refresh_loadout_dropdown)
        self._loadout_refresh_timer.start(3000)

    # ─────────────────────────────────────────────────────────────────────────
    # Layout builder
    # ─────────────────────────────────────────────────────────────────────────

    def _build_layout(self) -> None:
        """
        Build (or rebuild) the entire toolbar layout.

        Called once on construction and again when orientation changes.
        Clears the previous layout first so it can be safely rebuilt.
        """
        # ── Clear any existing layout ─────────────────────────────────────────
        if self.layout():
            self._clear_layout(self.layout())
            # Detach the old layout object by assigning it to a throwaway widget
            QWidget().setLayout(self.layout())

        is_horizontal = self._is_horizontal
        separator     = _make_vertical_separator if is_horizontal else _make_horizontal_separator

        # ── Root layout ───────────────────────────────────────────────────────
        if is_horizontal:
            layout = QHBoxLayout(self)
            layout.setContentsMargins(6, 4, 6, 4)
            layout.setSpacing(4)
            layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        else:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(5, 6, 5, 6)
            layout.setSpacing(3)
            layout.setAlignment(Qt.AlignTop)

        def add(widget) -> None:
            layout.addWidget(widget)

        # ── Grip handle — drag to reposition the toolbar ──────────────────────
        self._grip_label = QLabel("⠿")
        self._grip_label.setAlignment(Qt.AlignCenter)
        self._grip_label.setCursor(QCursor(Qt.SizeAllCursor))
        self._grip_label.setStyleSheet("""
            QLabel {
                background: rgba(80,80,80,180); border: 1px solid #888;
                border-radius: 3px; color: #dddddd; font-size: 14px;
            }
            QLabel:hover { background: rgba(120,120,120,220); border-color: #aaa; }
        """)
        if is_horizontal:
            self._grip_label.setFixedSize(22, _BUTTON_SIZE)
        else:
            self._grip_label.setFixedSize(_BUTTON_SIZE, 28)
        add(self._grip_label)
        add(separator())

        # ── TAB dropdown — switch which stash tab is being watched ────────────
        tab_label = QLabel("TAB")
        tab_label.setAlignment(Qt.AlignCenter)
        add(tab_label)

        self._tab_dropdown = QComboBox()
        self._tab_dropdown.setFixedSize(_BUTTON_SIZE, _BUTTON_SIZE)
        self._tab_dropdown.setToolTip("Switch stash tab")
        self._tab_dropdown.setStyleSheet(_COMPACT_DROPDOWN_STYLE)
        self._tab_dropdown.currentIndexChanged.connect(self._on_tab_dropdown_changed)
        add(self._tab_dropdown)
        add(separator())

        # ── SET dropdown — switch the active loadout ──────────────────────────
        set_label = QLabel("SET")
        set_label.setAlignment(Qt.AlignCenter)
        add(set_label)

        self._loadout_dropdown = QComboBox()
        self._loadout_dropdown.setFixedSize(_BUTTON_SIZE, _BUTTON_SIZE)
        self._loadout_dropdown.setToolTip("Switch mod loadout — click to expand")
        self._loadout_dropdown.setStyleSheet(_COMPACT_DROPDOWN_STYLE)
        self._loadout_dropdown.currentIndexChanged.connect(
            self._on_loadout_dropdown_changed
        )
        add(self._loadout_dropdown)
        add(separator())

        # ── Mod Filters button — opens the Scan & Filters tab ─────────────────
        filters_button = self._make_button("≡", "Open Mod Filters")
        filters_button.setStyleSheet("font-size:14px; font-weight:bold;")
        filters_button.clicked.connect(self.sig_open_filters)
        add(filters_button)

        # ── Config button — opens the Account/Settings tab ────────────────────
        config_button = self._make_button("⚙", "Open Account / Settings")
        config_button.clicked.connect(self.sig_open_config)
        add(config_button)
        add(separator())

        # ── Lock/unlock grid button ───────────────────────────────────────────
        lock_icon    = "🔒" if self._grid_locked else "🔓"
        lock_tooltip = "Unlock grid" if self._grid_locked else "Lock grid"
        lock_object  = "lock_on"     if self._grid_locked else "lock_off"

        self._lock_button = self._make_button(lock_icon, lock_tooltip, lock_object)
        self._lock_button.clicked.connect(self._on_lock_clicked)
        add(self._lock_button)

        # ── Eye toggle — show/hide item outlines ──────────────────────────────
        eye_object = "eye_on" if self._overlay_visible else "eye_off"
        self._eye_button = self._make_button("👁", "Toggle overlay  (F9)", eye_object)
        self._eye_button.clicked.connect(self._on_eye_clicked)
        add(self._eye_button)

        if not is_horizontal:
            layout.addStretch()

        # ── Position the toolbar on screen ────────────────────────────────────
        self.adjustSize()
        screen = QApplication.primaryScreen().geometry()

        if is_horizontal:
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16_777_215, _BUTTON_SIZE + 14)
            self.move(
                screen.center().x() - self.width() // 2,
                screen.top() + 2,
            )
        else:
            self.setMinimumSize(0, 0)
            self.setMaximumSize(_BUTTON_SIZE + 14, 16_777_215)
            self.move(
                screen.left() + 2,
                screen.center().y() - self.height() // 2,
            )

        self.show()

    def _make_button(self, text: str, tooltip: str,
                      object_name: str = "") -> QPushButton:
        """Create a fixed-size square toolbar button."""
        button = QPushButton(text)
        button.setFixedSize(_BUTTON_SIZE, _BUTTON_SIZE)
        button.setToolTip(tooltip)
        if object_name:
            button.setObjectName(object_name)
        return button

    def _clear_layout(self, layout) -> None:
        """Recursively remove all widgets from a layout."""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
            elif item.layout():
                self._clear_layout(item.layout())

    def _restyle(self, button: QPushButton) -> None:
        """
        Force Qt to re-read the button's objectName and apply the correct style.

        Qt caches stylesheet computations.  After changing a button's objectName,
        you must clear its inline stylesheet and re-apply the parent stylesheet
        to trigger a full style recalculation.
        """
        button.setStyleSheet("")
        self.setStyleSheet(_TOOLBAR_STYLESHEET)

    # ─────────────────────────────────────────────────────────────────────────
    # Public API — called by StashOverlay
    # ─────────────────────────────────────────────────────────────────────────

    def set_orientation(self, horizontal: bool) -> None:
        """
        Switch between horizontal (top bar) and vertical (side bar) layouts.

        Rebuilds the entire layout — the widget is temporarily unconstrained
        in size to prevent the old size limits from blocking the rebuild.
        """
        if horizontal == self._is_horizontal:
            return
        self._is_horizontal = horizontal
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16_777_215, 16_777_215)
        self._build_layout()

        # Repopulate dropdowns after rebuild (they were recreated from scratch)
        if self._stash_tabs:
            self.set_stash_tabs(self._stash_tabs)

    def set_stash_tabs(self, tabs: list[dict]) -> None:
        """
        Populate the TAB dropdown with the given stash tab list.

        Each entry shows up to 6 characters of the tab name (space is tight)
        with the full name available in the tooltip.
        """
        self._stash_tabs = tabs
        try:
            self._tab_dropdown.blockSignals(True)
            self._tab_dropdown.clear()
            for tab in tabs:
                self._tab_dropdown.addItem(tab["name"][:6], tab["id"])
                self._tab_dropdown.setItemData(
                    self._tab_dropdown.count() - 1,
                    tab["name"],
                    Qt.ToolTipRole,
                )
            self._tab_dropdown.blockSignals(False)
        except AttributeError:
            pass

    def set_current_tab_id(self, tab_id: str) -> None:
        """
        Programmatically select the tab with the given ID in the TAB dropdown.
        Called by StashOverlay when the user changes the tab in the config window.
        """
        try:
            for i in range(self._tab_dropdown.count()):
                if self._tab_dropdown.itemData(i) == tab_id:
                    self._tab_dropdown.blockSignals(True)
                    self._tab_dropdown.setCurrentIndex(i)
                    self._tab_dropdown.blockSignals(False)
                    return
        except AttributeError:
            pass

    def update_loadout_list(self, names: list[str]) -> None:
        """
        Refresh the SET dropdown with a new list of loadout names.
        Called by MainWindow when loadouts are added, renamed, or deleted.
        Preserves the currently selected entry if it still exists.
        """
        try:
            previously_selected = self._loadout_dropdown.currentData()
            self._loadout_dropdown.blockSignals(True)
            self._loadout_dropdown.clear()
            self._loadout_dropdown.addItem("── loadout ──", "")
            for name in sorted(names):
                self._loadout_dropdown.addItem(name, name)
            # Restore previous selection if still in the list
            index = self._loadout_dropdown.findData(previously_selected)
            self._loadout_dropdown.setCurrentIndex(max(index, 0))
            self._loadout_dropdown.blockSignals(False)
        except AttributeError:
            pass

    def set_grid_locked(self, locked: bool) -> None:
        """Update the lock button appearance to match the given locked state."""
        self._grid_locked = locked
        try:
            self._lock_button.setObjectName("lock_on" if locked else "lock_off")
            self._lock_button.setText("🔒" if locked else "🔓")
            self._restyle(self._lock_button)
        except AttributeError:
            pass

    def set_overlay_on(self, visible: bool) -> None:
        """Update the eye button appearance to match the given visibility state."""
        self._overlay_visible = visible
        try:
            self._eye_button.setObjectName("eye_on" if visible else "eye_off")
            self._restyle(self._eye_button)
        except AttributeError:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # Drag to reposition the toolbar
    # ─────────────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            child = self.childAt(event.pos())
            # Allow dragging from empty areas or the grip handle
            if child is None or child is self._grip_label:
                self._drag_start_pos = (
                    event.globalPos() - self.frameGeometry().topLeft()
                )

    def mouseMoveEvent(self, event) -> None:
        if self._drag_start_pos is not None and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_start_pos)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_start_pos = None

    # ─────────────────────────────────────────────────────────────────────────
    # Button click handlers
    # ─────────────────────────────────────────────────────────────────────────

    def _on_lock_clicked(self) -> None:
        """Toggle the grid lock state and emit sig_lock_toggle."""
        self._grid_locked = not self._grid_locked
        self._lock_button.setObjectName("lock_on" if self._grid_locked else "lock_off")
        self._lock_button.setText("🔒" if self._grid_locked else "🔓")
        self._lock_button.setToolTip(
            "Unlock grid" if self._grid_locked else "Lock grid"
        )
        self._restyle(self._lock_button)
        self.sig_lock_toggle.emit()

    def _on_eye_clicked(self) -> None:
        """Toggle overlay visibility and emit sig_toggle."""
        self._overlay_visible = not self._overlay_visible
        self._eye_button.setObjectName(
            "eye_on" if self._overlay_visible else "eye_off"
        )
        self._restyle(self._eye_button)
        self.sig_toggle.emit()

    def _on_tab_dropdown_changed(self, _index: int) -> None:
        """Emit sig_tab_changed with the selected tab's ID."""
        try:
            tab_id = self._tab_dropdown.currentData()
            if tab_id:
                self.sig_tab_changed.emit(tab_id)
        except AttributeError:
            pass

    def _on_loadout_dropdown_changed(self, _index: int) -> None:
        """Emit sig_loadout_changed with the selected loadout name."""
        name = self._loadout_dropdown.currentData()
        # Skip the "── loadout ──" placeholder (data = "")
        if name:
            self.sig_loadout_changed.emit(name)

    # ─────────────────────────────────────────────────────────────────────────
    # Loadout dropdown auto-refresh
    # ─────────────────────────────────────────────────────────────────────────

    def _refresh_loadout_dropdown(self) -> None:
        """
        Re-read loadouts.json and update the SET dropdown if the list changed.

        Called every 3 seconds by the timer.  Only rebuilds the dropdown if
        the list of names actually changed, to avoid unnecessary UI flicker.
        """
        names: list[str] = []
        if _LOADOUTS_FILE.exists():
            try:
                with open(_LOADOUTS_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                names = sorted(data.keys())
            except Exception:
                pass

        # Skip update if nothing changed
        if names == self._loadout_names:
            return

        self._loadout_names = names
        self.update_loadout_list(names)
