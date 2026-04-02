from __future__ import annotations

"""
controllers/app_controller.py
─────────────────────────────────────────────────────────────────────────────
This file is now the main Qt application controller.

WHY THIS FILE EXISTS
    The old main.py had many different responsibilities mixed together:
        - app startup
        - tray icon setup
        - hotkeys
        - PoE window watching
        - stash tab loading
        - scanning
        - overlay updates
        - configuration window coordination

    That works for a prototype, but it becomes difficult for a beginner to
    navigate because one file starts to feel like "the whole game engine".

    This controller keeps the same behaviour, but moves it into a file whose
    name explains its purpose: it controls the application.

MENTAL MODEL FOR A BEGINNER
    View:
        MainWindow, overlay widgets, tray menu visuals

    Controller:
        AppController
        It reacts to user actions and tells services / workers / views what to do.

    Worker:
        StashScanWorker, StashListWorker
        They do slower tasks away from the main UI thread.
"""

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from typing import Optional

from PyQt5.QtCore import Qt, QObject, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QCursor, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QMenu, QSystemTrayIcon

import config
from api.clients.oauth_client import load_cached_token
from api import get_api_manager
from services.stats_service import load_from_disk_if_available as preload_mods_from_disk
from logic.item_parser import ParsedItem
from models import OutlineColorRole, ScanRequest, ScanResult, coerce_stash_tab_summary
from logic.mod_scorer import ModFilter
from logic.window_finder import is_poe_minimized
from ui.main_window import MainWindow
from ui.overlay import (
    StashOverlay,
    register_instance,
    set_badge_flag,
    set_min_matching,
    set_outline_palette,
    set_outline_thickness,
)
from ui.sound import play_ding
from workers.stash_scan_worker import StashScanWorker
from workers.stash_list_worker import StashListWorker


class PoeWatcher(QObject):
    """
    Small helper that polls whether the Path of Exile window is minimized.

    This still uses polling because the existing project already has a working
    window-detection function. The polling interval is modest and easy to reason
    about, which is often better than over-engineering a beginner project.
    """

    poe_minimized = pyqtSignal()
    poe_restored = pyqtSignal()

    _POLL_MS = 500

    def __init__(self, parent=None):
        super().__init__(parent)
        self._was_minimized: Optional[bool] = None
        self._timer = QTimer(self)
        self._timer.setInterval(self._POLL_MS)
        self._timer.timeout.connect(self._poll)
        self._timer.start()

    def _poll(self) -> None:
        minimized = is_poe_minimized()
        if minimized == self._was_minimized:
            return

        self._was_minimized = minimized
        if minimized:
            self.poe_minimized.emit()
        else:
            self.poe_restored.emit()


# ─────────────────────────────────────────────────────────────────────────────
# Always-on-top helpers
# ─────────────────────────────────────────────────────────────────────────────
# These functions are intentionally kept near the controller because they are
# window-behaviour helpers, not pure business logic.


def _set_always_on_top_win32(widget, on_top: bool) -> bool:
    """Use the native Windows API when available to reduce flicker."""
    try:
        import ctypes

        HWND_TOPMOST = -1
        HWND_NOTOPMOST = 0
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOACTIVATE = 0x0010

        hwnd = int(widget.winId())
        insert_after = HWND_TOPMOST if on_top else HWND_NOTOPMOST
        ctypes.windll.user32.SetWindowPos(
            hwnd,
            insert_after,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
        )
        return True
    except Exception:
        return False


def set_always_on_top(widget, on_top: bool) -> None:
    """
    Cross-platform-ish fallback for keeping the config window above other windows.

    We try the Windows-specific path first because this project is clearly built
    around the Windows Path of Exile client. If that fails, we fall back to the
    standard Qt window flag approach.
    """
    if _set_always_on_top_win32(widget, on_top):
        return

    flags = widget.windowFlags()
    if on_top:
        flags |= Qt.WindowStaysOnTopHint
    else:
        flags &= ~Qt.WindowStaysOnTopHint

    was_visible = widget.isVisible()
    widget.setWindowFlags(flags)
    if was_visible:
        widget.show()


class AppController(QObject):
    """
    Main controller for the entire desktop application.

    RESPONSIBILITIES
        - create the main windows
        - restore saved session data
        - connect signals between the UI and the overlay
        - launch background workers
        - keep track of the currently selected stash, league, and filters

    NON-RESPONSIBILITIES
        - It should not contain the detailed UI code for each tab.
        - It should not parse raw item text itself.
        - It should not know how the database builder scripts work internally.
    """

    def __init__(self, qt_app: QApplication):
        super().__init__()
        self.qt_app = qt_app

        # Runtime state shared across several UI actions.
        self.token: Optional[str] = None
        self.filters: list[ModFilter] = []
        self.slot_filters: dict = {}
        self.base_selections: dict = {}
        self.item_props: dict = {}
        self.account_name: str = config.get("account_name", "") or ""
        self.league = "Mirage"
        self.stash_id = ""

        self._worker: Optional[ScanWorker] = None
        self._tab_loader: Optional[StashListWorker] = None
        self._scan_counter = 0
        self._cursor_msg = None

        config.load_config()
        get_api_manager().refresh_runtime_settings()

        # Build and show the main windows first.
        self.overlay = StashOverlay()
        register_instance(self.overlay)

        self.main_window = MainWindow()
        preload_mods_from_disk()
        self.main_window.show()

        # Watch the game window so overlay visibility feels natural.
        self._poe_watcher = PoeWatcher(self)
        self._poe_watcher.poe_minimized.connect(self._on_poe_minimized)
        self._poe_watcher.poe_restored.connect(self._on_poe_restored)
        set_always_on_top(self.main_window, True)

        self._wire_ui_signals()
        self._setup_tray()
        self._setup_hotkeys()
        self._restore_saved_session()
        self._restore_cached_token()

    # ─────────────────────────────────────────────────────────────────────
    # Setup helpers
    # ─────────────────────────────────────────────────────────────────────

    def _wire_ui_signals(self) -> None:
        """Connect view signals to controller methods in one central place."""
        self.main_window.filters_changed.connect(self._on_filters_changed)
        self.main_window.refresh_stash.connect(self._on_refresh_stash)
        self.main_window.grid_params_changed.connect(self._on_calibration_params_changed)
        self.main_window.stash_tab_changed.connect(self._on_stash_tab_changed)
        self.main_window.slot_filters_changed.connect(self._on_slot_filters_changed)
        self.main_window.loadout_list_changed.connect(self._on_loadout_list_changed)
        self.main_window.base_selection_changed.connect(self._on_base_selection_changed)
        self.main_window.item_property_changed.connect(self._on_item_property_changed)
        self.main_window.sidebar_orientation_changed.connect(
            self.overlay.hud.set_orientation
        )

        hud = self.overlay.hud
        hud.sig_scan.connect(self._do_scan)
        hud.sig_open_config.connect(self._show_config)
        hud.sig_open_filters.connect(self._show_filters)
        hud.sig_tab_changed.connect(self._on_hud_tab_changed)
        hud.sig_loadout_changed.connect(self._on_hud_loadout_changed)
        self.overlay.grid.params_changed.connect(self._on_grid_params_changed)

    def _restore_saved_session(self) -> None:
        """Load previously saved user state from config.json into runtime state."""
        self.league = config.get("league", "Mirage")
        self.stash_id = config.get("selected_stash", "")
        self.filters = [ModFilter.from_dict(entry) for entry in config.get("mod_filters", [])]
        self.account_name = config.get("account_name", "") or ""

        sidebar_horizontal = config.get("sidebar_horizontal", False)
        if sidebar_horizontal:
            self.overlay.hud.set_orientation(True)
            self.main_window.set_sidebar_horizontal(True)

        saved_colors = config.get("overlay_colors") or {}
        set_outline_palette(
            saved_colors.get(OutlineColorRole.ALL.value, "#00ff44"),
            saved_colors.get(OutlineColorRole.MINUS1.value, "#ff8800"),
            saved_colors.get(OutlineColorRole.MINUS2.value, "#ff2222"),
            saved_colors.get(OutlineColorRole.SLOT_ONLY.value, "#ffffff"),
            saved_colors.get(OutlineColorRole.ALL_GOLD.value, "#ffd700"),
        )
        set_outline_thickness(int(saved_colors.get("thickness", 3)))
        set_min_matching(int(saved_colors.get("min_matching", 1)))

        saved_badges = config.get("overlay_badges") or {}
        set_badge_flag("mod_count", saved_badges.get("mod_count", True))

    def _restore_cached_token(self) -> None:
        """If a previous OAuth token exists, restore it and warm up the stash UI."""
        cached_token = load_cached_token()
        if not cached_token:
            return

        self.token = cached_token["access_token"]
        self.main_window.set_token(self.token)

        # Delay slightly so the UI has time to finish drawing before the first
        # background network task starts.
        QTimer.singleShot(800, self._load_stash_tabs_for_hud)

    # ─────────────────────────────────────────────────────────────────────
    # Tray icon
    # ─────────────────────────────────────────────────────────────────────

    def _setup_tray(self) -> None:
        self.tray = QSystemTrayIcon(self._make_icon(), self.qt_app)
        menu = QMenu()

        actions = [
            ("Settings", self.main_window.show),
            ("Refresh (F10)", self._do_scan),
            ("Toggle Overlay", self.overlay.toggle_visible),
            None,
            ("Quit", self.qt_app.quit),
        ]

        for action in actions:
            if action is None:
                menu.addSeparator()
                continue
            label, callback = action
            qt_action = menu.addAction(label)
            qt_action.triggered.connect(callback)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: self.main_window.show()
            if reason == QSystemTrayIcon.DoubleClick
            else None
        )
        self.tray.show()

    def _make_icon(self) -> QIcon:
        """Create a tiny in-memory tray icon so the project has no icon-file dependency."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#00ff88"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, 4, 24, 24)
        painter.end()

        return QIcon(pixmap)

    # ─────────────────────────────────────────────────────────────────────
    # Hotkeys
    # ─────────────────────────────────────────────────────────────────────

    def _setup_hotkeys(self) -> None:
        """Register optional global hotkeys. Failure here is non-fatal."""
        try:
            import keyboard

            ui_config = config.get("ui") or {}
            hotkey_toggle_overlay = ui_config.get("hotkey_toggle_overlay", "F9")
            hotkey_refresh = ui_config.get("hotkey_refresh", "F10")

            keyboard.add_hotkey(hotkey_toggle_overlay, self.overlay.toggle_visible)
            keyboard.add_hotkey(hotkey_refresh, self._scan_and_show)
        except Exception as error:
            print(f"[Hotkeys] Could not register: {error}")

    def _scan_and_show(self) -> None:
        if not self.overlay._all_visible:
            self.overlay.toggle_visible()
        self._do_scan()

    # ─────────────────────────────────────────────────────────────────────
    # Small view helpers
    # ─────────────────────────────────────────────────────────────────────

    def _raise_config(self, tab_index: int = 0) -> None:
        # tab_index is kept for future extension even though the window does not
        # currently switch tabs here.
        _ = tab_index
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def _show_config(self) -> None:
        self._raise_config(0)

    def _show_filters(self) -> None:
        self._raise_config(1)

    # ─────────────────────────────────────────────────────────────────────
    # Stash tab loading
    # ─────────────────────────────────────────────────────────────────────

    def _load_stash_tabs_for_hud(self) -> None:
        if not self.token:
            return

        self._tab_loader = StashListWorker(self.token, self.league)
        self._tab_loader.stash_list_ready.connect(self._on_hud_tabs_loaded)
        self._tab_loader.error.connect(self.main_window.set_status)
        self._tab_loader.start()

    @pyqtSlot(list)
    def _on_hud_tabs_loaded(self, tabs: list) -> None:
        stash_summaries = [coerce_stash_tab_summary(tab) for tab in tabs]
        formatted_tabs = [tab.to_dict() for tab in stash_summaries]

        self.overlay.set_stash_tabs(formatted_tabs)
        self.main_window.populate_stash_tabs(stash_summaries)

        if not self.stash_id and stash_summaries:
            self.stash_id = stash_summaries[0].id
            config.set_key("selected_stash", self.stash_id)

        if self.stash_id:
            self.overlay.set_current_tab_id(self.stash_id)

    # ─────────────────────────────────────────────────────────────────────
    # Signal handlers coming from the views
    # ─────────────────────────────────────────────────────────────────────

    @pyqtSlot(list)
    def _on_filters_changed(self, filters: list[ModFilter]) -> None:
        self.filters = filters

    @pyqtSlot(str, str)
    def _on_refresh_stash(self, league: str, stash_id: str) -> None:
        self.league = league
        self.stash_id = stash_id

        if not self.token:
            try:
                self.token = get_api_manager().oauth_client.authenticate()
                self.main_window.set_token(self.token)
            except Exception as error:
                self.main_window.set_status(f"Authentication failed. {error}")
                return

        self._load_stash_tabs_for_hud()
        self._do_scan()

    @pyqtSlot(str)
    def _on_stash_tab_changed(self, stash_id: str) -> None:
        self.stash_id = stash_id
        config.set_key("selected_stash", stash_id)
        self.overlay.set_current_tab_id(stash_id)
        self.overlay.clear_items()

    @pyqtSlot(str)
    def _on_hud_tab_changed(self, stash_id: str) -> None:
        self.stash_id = stash_id
        config.set_key("selected_stash", stash_id)
        self.overlay.clear_items()
        self.main_window.select_stash_tab(stash_id)

    @pyqtSlot(str)
    def _on_hud_loadout_changed(self, name: str) -> None:
        self.main_window.switch_loadout(name)

    @pyqtSlot(dict)
    def _on_slot_filters_changed(self, slot_dict: dict) -> None:
        self.slot_filters = slot_dict

    @pyqtSlot(list)
    def _on_loadout_list_changed(self, names: list) -> None:
        self.overlay.hud.update_loadout_list(names)

    def _on_base_selection_changed(self, base_selections: dict) -> None:
        self.base_selections = base_selections

    @pyqtSlot(dict)
    def _on_item_property_changed(self, props: dict) -> None:
        self.item_props = props

    def _score_and_update_overlay(self, items: list[ParsedItem]) -> None:
        """Apply the final combined filter logic and push the visible items to the overlay."""
        from logic.unified_filter import apply_unified_filter

        visible_items = apply_unified_filter(
            items,
            self.slot_filters,
            self.base_selections,
            self.item_props,
        )
        total_filter_count = sum(len(filters) for filters in self.slot_filters.values()) if self.slot_filters else 0
        self.overlay.set_items(visible_items, total_filters=total_filter_count)

    def _on_calibration_params_changed(self, grid_x, grid_y, cell_size, columns, rows) -> None:
        self.overlay.set_grid_params(grid_x, grid_y, cell_size, columns, rows)

    @pyqtSlot(int, int, float, int, int)
    def _on_grid_params_changed(self, grid_x, grid_y, cell_size, columns, rows) -> None:
        self.main_window.update_grid_display(grid_x, grid_y, cell_size, columns, rows)

    # ─────────────────────────────────────────────────────────────────────
    # Small floating message near the cursor
    # ─────────────────────────────────────────────────────────────────────

    def _show_cursor_message(self, text: str, duration_ms: int = 2500) -> None:
        """Show a short non-blocking helper message near the mouse cursor."""
        message = QLabel(text)
        message.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        message.setAttribute(Qt.WA_TranslucentBackground)
        message.setStyleSheet(
            "QLabel{background:rgba(30,15,15,220);color:#ffaa66;"
            "border:1px solid #884422;border-radius:6px;"
            "padding:8px 14px;font-size:11px;font-weight:bold;}"
        )
        message.adjustSize()
        cursor_position = QCursor.pos()
        message.move(cursor_position.x() + 12, cursor_position.y() + 12)
        message.show()
        message.raise_()
        QTimer.singleShot(duration_ms, message.close)
        self._cursor_msg = message

    # ─────────────────────────────────────────────────────────────────────
    # Game window visibility handling
    # ─────────────────────────────────────────────────────────────────────

    @pyqtSlot()
    def _on_poe_minimized(self) -> None:
        self.overlay.grid.hide()
        self.overlay.canvas.hide()
        self.overlay.tooltip.stop()
        set_always_on_top(self.main_window, False)
        print("[PoeWatcher] PoE minimised — overlay hidden, config unpinned")

    @pyqtSlot()
    def _on_poe_restored(self) -> None:
        if self.overlay._all_visible:
            self.overlay.grid.show()
            self.overlay.canvas.show()
            self.overlay.tooltip.start()
        set_always_on_top(self.main_window, True)
        self.main_window.raise_()
        print("[PoeWatcher] PoE restored — overlay shown, config re-pinned")

    # ─────────────────────────────────────────────────────────────────────
    # Scan orchestration
    # ─────────────────────────────────────────────────────────────────────

    def _do_scan(self) -> None:
        """Start one scan if the application is in a valid state."""
        if not self.token:
            self.main_window.set_status("Not authenticated — please login via OAuth first.")
            return

        if not self.stash_id:
            self.main_window.set_status("No stash tab selected — load tabs first.")
            return

        if self._worker and self._worker.isRunning():
            self.main_window.set_status("Scan already in progress…")
            return

        if not self.slot_filters and not self.base_selections and not self.item_props:
            self._show_cursor_message(
                "Set up a filter first — add a loadout slot and at least one mod."
            )
            return

        self._scan_counter += 1
        scan_id = self._scan_counter

        request = ScanRequest(
            access_token=self.token,
            account_name=self.account_name,
            league=self.league,
            stash_id=self.stash_id,
            filters=self.filters,
            scan_id=scan_id,
        )
        self._worker = StashScanWorker(request)
        self._worker.items_ready.connect(self._on_items_ready)
        self._worker.status.connect(self.main_window.set_status)
        self._worker.error.connect(self.main_window.set_status)
        self._worker.error_detail.connect(
            lambda traceback_text: print(f"[ScanWorker traceback]\n{traceback_text}")
        )
        self._worker.start()

    @pyqtSlot(object)
    def _on_items_ready(self, result: ScanResult) -> None:
        """Accept worker results only if they belong to the newest requested scan.

        Why this matters:
            Suppose scan #4 is slow and scan #5 is fast.
            If #4 finishes after #5, we do not want the older result to overwrite
            the newer overlay display.
        """
        items = result.items
        scan_id = result.scan_id
        if scan_id != self._scan_counter:
            print(f"[Scan] Discarding stale result #{scan_id}")
            return

        self._score_and_update_overlay(items)
        scored_count = sum(1 for item in items if item.score and item.score > 0)
        self.main_window.set_status(
            f"Done — {len(items)} items scanned | {scored_count} matched"
        )
        play_ding()
