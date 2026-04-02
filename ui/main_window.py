"""
ui/main_window.py
─────────────────────────────────────────────────────────────────────────────
PURPOSE
    The root configuration window for PoE Stash Helper.

    This file's ONLY job is to:
        1. Create the QTabWidget and add the individual tab widgets.
        2. Create the bottom action bar (Scan button, tab selector, status label).
        3. Wire signals between tabs so they can communicate.
        4. Expose a clean public API for the application controller to call.

    Each tab's content is defined in its own file — this file should stay
    short.  If you find yourself adding a lot of logic here, it probably
    belongs in one of the tab files or in a dedicated service/worker instead.

TAB STRUCTURE
    ┌─────────────────────────────────────────────────────┐
    │  Account  │  Scan & Filters  │  Overlay  │  Config  │
    ├─────────────────────────────────────────────────────┤
    │  [tab content — each tab is its own widget class]   │
    ├─────────────────────────────────────────────────────┤
    │  [Scan Stash]  [stash dropdown]  Status: Ready  ░░░ │  ← bottom bar
    └─────────────────────────────────────────────────────┘

TAB FILES
    ui/tabs/account_tab.py      → "Account" tab
    ui/tabs/scan_filters_tab.py → "Scan & Filters" tab
    ui/tabs/overlay_settings/           → "Overlay" tab
    ui/tabs/config_tab.py       → "Config" tab (placeholder)

SIGNALS EMITTED (for AppController to connect)
    filters_changed(list)                — new list of ModFilter on scan
    slot_filters_changed(dict)           — {slot: [ModFilter]} on scan
    base_selection_changed(dict)         — {slot: [base_name]} on scan
    item_property_changed(dict)          — property filter dict on scan
    loadout_list_changed(list)           — [loadout_name, ...] whenever loadouts change
    refresh_stash(str, str)              — (league, stash_id) triggers a stash scan
    stash_tab_changed(str)               — stash tab id changed, no auto-scan
    grid_params_changed(int,int,float,int,int) — calibration spinbox changed
    sidebar_orientation_changed(bool)    — True = horizontal

PUBLIC METHODS (called by AppController)
    set_token(token)               — mark OAuth as authenticated
    set_status(message)            — update the status bar label
    populate_stash_tabs(tabs)      — fill both stash dropdowns from tab list
    update_grid_display(...)       — update calibration spinboxes from drag
    get_item_properties()          — {slot: filter_dict} from properties panel
    get_all_base_selections()      — {slot: [base_name]} from item base panel
    set_sidebar_horizontal(bool)   — update orientation radio buttons
"""

from __future__ import annotations

import threading

import config

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget,
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot

from logic.mod_scorer import ModFilter

from ui.shared import DARK_THEME_STYLESHEET, TAB_TYPE_BADGE, ITEM_SLOTS
from models import coerce_stash_tab_summary
from ui.tabs.account_tab import AccountTab
from ui.tabs.scan_filters_tab import ScanFiltersTab
from ui.tabs.overlay_settings import OverlayTab
from ui.tabs.options_tab import OptionTab
from ui.tabs.config_tab import ConfigTab

from services.scan_payload_service import build_scan_payload
from ui.widgets.scan_action_bar import ScanActionBar
from models import coerce_stash_tab_summary


class MainWindow(QWidget):
    """
    The main configuration window.

    Assembles all tab widgets and wires their signals together.
    Exposes a minimal API for AppController.
    """

    # ── Signals for AppController ──────────────────────────────────────────────

    filters_changed             = pyqtSignal(list)           # [ModFilter]
    slot_filters_changed        = pyqtSignal(dict)           # {slot: [ModFilter]}
    base_selection_changed      = pyqtSignal(dict)           # {slot: [base_name]}
    item_property_changed       = pyqtSignal(dict)           # property filter dict
    loadout_list_changed        = pyqtSignal(list)           # [loadout_name, ...]
    refresh_stash               = pyqtSignal(str, str)       # (league, stash_id)
    stash_tab_changed           = pyqtSignal(str)            # stash tab id, no auto-scan
    grid_params_changed         = pyqtSignal(int, int, float, int, int)
    sidebar_orientation_changed = pyqtSignal(bool)           # True = horizontal

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("PoE Stash Helper")
        self.setMinimumSize(480, 400)
        self.resize(1060, 700)
        self._apply_dark_theme()
        self._build_ui()
        self._load_from_config()

    # ─────────────────────────────────────────────────────────────────────────
    # Theme
    # ─────────────────────────────────────────────────────────────────────────

    def _apply_dark_theme(self) -> None:
        """Apply the app-wide dark theme stylesheet defined in ui/shared/theme.py."""
        self.setStyleSheet(DARK_THEME_STYLESHEET)

    # ─────────────────────────────────────────────────────────────────────────
    # Root layout: tab widget + bottom action bar
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """
        Build the window root layout:
            • Tab widget (Account | Scan & Filters | Overlay | Config)
            • Bottom bar (Scan button | stash dropdown | status label)
        """
        # The bottom action bar is its own widget now.
        #
        # Reason:
        #   MainWindow should describe the page structure, not manually build
        #   every control row inline. The small bar widget keeps the root window
        #   easier to read.
        self._scan_action_bar = ScanActionBar()
        self._scan_action_bar.scan_clicked.connect(self._on_scan_clicked)
        self._scan_action_bar.stash_selection_changed.connect(
            self._on_scan_stash_dropdown_changed
        )



        # ── Instantiate all tab widgets ───────────────────────────────────────
        self._account_tab        = AccountTab()
        self._scan_filters_tab = ScanFiltersTab()
        self._overlay_tab        = OverlayTab()
        self._option_tab         = OptionTab()
        self._config_tab         = ConfigTab()

        # ── Tab widget ────────────────────────────────────────────────────────
        self._tab_widget = QTabWidget()
        self._tab_widget.addTab(self._account_tab,        "Account")
        self._tab_widget.addTab(self._scan_filters_tab, "Scan & Filters")
        self._tab_widget.addTab(self._overlay_tab,        "Overlay")
        self._tab_widget.addTab(self._option_tab,         "Option")
        self._tab_widget.addTab(self._config_tab,         "Config")
        self._tab_widget.currentChanged.connect(self._on_main_tab_switched)

        # ── Root layout ───────────────────────────────────────────────────────
        root_layout = QVBoxLayout(self)
        root_layout.addWidget(self._tab_widget)
        root_layout.addWidget(self._scan_action_bar)

        # ── Wire inter-tab signals ────────────────────────────────────────────
        self._wire_signals()

        # Set initial button visibility
        self._on_main_tab_switched(0)

    def _wire_signals(self) -> None:
        """
        Connect signals between tab widgets.
        All cross-tab communication is wired here in one place.
        """
        # Account tab
        self._account_tab.token_acquired.connect(self._on_token_acquired)
        self._account_tab.stashes_loaded.connect(self._on_stashes_loaded_from_account)
        self._account_tab.stash_tab_selected.connect(self._on_account_stash_selected)

        # Overlay tab
        self._overlay_tab.grid_params_changed.connect(self.grid_params_changed)
        self._overlay_tab.sidebar_orientation_changed.connect(
            self.sidebar_orientation_changed
        )

        # Loadout / filter tab
        self._scan_filters_tab.loadout_selection_changed.connect(
            self._refresh_scan_button_visibility
        )
        self._scan_filters_tab.slot_activated.connect(self._on_slot_activated)

        # Load mod data silently in the background at startup
        threading.Thread(target=self._background_load_mods, daemon=True).start()

    def _background_load_mods(self) -> None:
        """Background thread: load all mod data from disk/RePoE cache."""
        from services.stats_service import load_all_stats
        load_all_stats()
        from PyQt5.QtCore import QMetaObject
        QMetaObject.invokeMethod(
            self, "_on_background_mods_loaded", Qt.QueuedConnection
        )

    @pyqtSlot()
    def _on_background_mods_loaded(self) -> None:
        """Main-thread callback after background mod load finishes."""
        from services.stats_service import cache_size as mod_cache_size
        self._scan_action_bar.set_status(f"{mod_cache_size()} mods available.")
        try:
            self._scan_filters_tab.refresh_mod_search_results()
        except AttributeError:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # Load / save config on startup and before scan
    # ─────────────────────────────────────────────────────────────────────────

    def _load_from_config(self) -> None:
        """Restore saved config values into UI widgets on startup."""
        saved_filters = config._runtime.get("mod_filters", [])
        if saved_filters:
            active_mod_panel = self._scan_filters_tab.get_active_mod_panel()
            for filter_dict in saved_filters:
                active_mod_panel.add_mod(ModFilter.from_dict(filter_dict))

    def _save_to_config(self) -> None:
        """Persist current UI state to config (called just before scanning)."""
        config.set_key("league",         self._account_tab.get_selected_league())
        config.set_key("selected_stash", self._get_active_stash_id())
        config.set_key("mod_filters", [
            f.to_dict()
            for f in self._scan_filters_tab.get_active_mod_panel().get_filters()
        ])
        self._overlay_tab.save_calibration_to_config()

    # ─────────────────────────────────────────────────────────────────────────
    # Scan button visibility
    # ─────────────────────────────────────────────────────────────────────────

    def _refresh_scan_button_visibility(self) -> None:
        """
        Show Scan button and stash dropdown only when the Scan & Filters tab
        is active AND the current loadout has at least one slot.
        """
        on_scan_tab = (self._tab_widget.currentIndex() == 1)
        has_slots   = self._scan_filters_tab.has_slots()

        self._scan_action_bar.set_scan_controls_visible(on_scan_tab and has_slots)

        # The loadout tab owns its own slot-bar widgets, so ask it directly to
        # show or hide the small button instead of reaching into a private field.
        self._scan_filters_tab.set_add_slot_button_visible(
            self._scan_filters_tab.has_real_loadout()
        )

    def _on_main_tab_switched(self, index: int) -> None:
        """Show the Scan button only on the Scan & Filters tab."""
        has_slots = self._scan_filters_tab.has_slots()
        self._scan_action_bar.set_scan_controls_visible(index == 1 and has_slots)

    # ─────────────────────────────────────────────────────────────────────────
    # Scan logic
    # ─────────────────────────────────────────────────────────────────────────

    def _on_scan_clicked(self) -> None:
        """Save current UI state, build the scan payload, and emit refresh_stash."""
        self._save_to_config()

        league = self._account_tab.get_selected_league()
        stash_id = self._get_active_stash_id()

        scan_payload = build_scan_payload(self._scan_filters_tab)
        self.filters_changed.emit(scan_payload.flat_filters)
        self.slot_filters_changed.emit(scan_payload.slot_filters)
        self.base_selection_changed.emit(self.get_all_base_selections())
        self.refresh_stash.emit(league, stash_id)

    def _get_active_stash_id(self) -> str:
        """Return the stash tab ID to scan (scan bar preferred, Account tab as fallback)."""
        stash_id = self._scan_action_bar.stash_dropdown.currentData() or ""
        if not stash_id:
            stash_id = self._account_tab.get_selected_stash_id()
        return stash_id

    # ─────────────────────────────────────────────────────────────────────────
    # Stash tab dropdown synchronisation
    # ─────────────────────────────────────────────────────────────────────────

    def populate_stash_tabs(self, tabs: list) -> None:
        """
        Fill both stash tab dropdowns (Account tab + scan bar) from a tab list.

        Never changes the current selection — always restores the saved stash ID.

        Args:
            tabs: list of dicts like [{"name": "...", "id": "...", "type": "..."}, ...]
        """
        # Account tab dropdown
        self._account_tab.populate_stash_tab_list(tabs)

        # Scan-bar dropdown
        saved_id = config.get("selected_stash") or ""
        dropdown = self._scan_action_bar.stash_dropdown
        dropdown.blockSignals(True)
        dropdown.clear()

        for tab in tabs:
            stash_tab = coerce_stash_tab_summary(tab)
            badge = TAB_TYPE_BADGE.get(stash_tab.type, f" [{stash_tab.type_value}]")
            dropdown.addItem(f"{stash_tab.name}{badge}", stash_tab.id)
            dropdown.setItemData(
                dropdown.count() - 1,
                stash_tab,
                role=0x0101,   # Qt.UserRole + 1 — stores the full tab summary for later checks
            )

        # Restore saved selection if it still exists in the list
        for i in range(dropdown.count()):
            if dropdown.itemData(i) == saved_id:
                dropdown.setCurrentIndex(i)
                break

        dropdown.blockSignals(False)

    def _on_scan_stash_dropdown_changed(self, _index: int) -> None:
        """
        Keep the Account tab dropdown in sync when the scan-bar dropdown changes.
        Emits stash_tab_changed so the application controller tracks the selection without rescanning.
        """
        stash_id = self._scan_action_bar.stash_dropdown.currentData() or ""
        if not stash_id:
            return
        account_dd = self._account_tab._stash_dropdown
        for i in range(account_dd.count()):
            if account_dd.itemData(i) == stash_id:
                account_dd.blockSignals(True)
                account_dd.setCurrentIndex(i)
                account_dd.blockSignals(False)
                break
        self.stash_tab_changed.emit(stash_id)

    # ─────────────────────────────────────────────────────────────────────────
    # Signal handlers
    # ─────────────────────────────────────────────────────────────────────────

    def _on_token_acquired(self, token: str) -> None:
        self._scan_action_bar.set_status(
            "Authenticated — click 'Load tabs' to fetch your stash list."
        )

    @pyqtSlot(list)
    def _on_stashes_loaded_from_account(self, stashes: list) -> None:
        """Account tab fetched the stash list — populate both dropdowns."""
        self.populate_stash_tabs([coerce_stash_tab_summary(s) for s in stashes])

    def _on_account_stash_selected(self, stash_id: str) -> None:
        """Account tab dropdown changed — sync the scan-bar dropdown."""
        self.select_stash_tab(stash_id)
        self.stash_tab_changed.emit(stash_id)

    def select_stash_tab(self, stash_id: str) -> None:
        """Select a stash tab in the bottom scan bar without re-emitting signals."""
        dropdown = self._scan_action_bar.stash_dropdown
        for index in range(dropdown.count()):
            if dropdown.itemData(index) == stash_id:
                dropdown.blockSignals(True)
                dropdown.setCurrentIndex(index)
                dropdown.blockSignals(False)
                break

    def _on_slot_activated(self, slot_name: str) -> None:
        """A slot was activated — refresh Scan button visibility."""
        self._refresh_scan_button_visibility()

    # ─────────────────────────────────────────────────────────────────────────
    # Public API — called by AppController
    # ─────────────────────────────────────────────────────────────────────────

    def set_token(self, token: str) -> None:
        """Called during application startup when a cached OAuth token is available."""
        self._account_tab.set_token(token)

    def set_status(self, message: str) -> None:
        """Update the bottom-bar status label."""
        self._scan_action_bar.set_status(message)

    def get_account_name(self) -> str:
        return self._account_tab.get_account_name()

    def get_item_properties(self) -> dict:
        return self._scan_filters_tab.get_item_property_filters()

    def get_all_base_selections(self) -> dict:
        return self._scan_filters_tab.get_all_base_selections()

    def update_grid_display(self, grid_x, grid_y, cell_size, columns, rows) -> None:
        """Update calibration spinboxes when the grid is dragged on screen."""
        self._overlay_tab.update_grid_display(grid_x, grid_y, cell_size, columns, rows)

    def set_sidebar_horizontal(self, is_horizontal: bool) -> None:
        self._overlay_tab.set_sidebar_horizontal(is_horizontal)

    # ─────────────────────────────────────────────────────────────────────────
    # Font size application — called by OverlayTab when sliders move
    # ─────────────────────────────────────────────────────────────────────────

    def _apply_font_sizes(self) -> None:
        """
        Apply font-size overrides from the Overlay tab sliders to the whole window.

        Uses a QSS marker comment to append size rules after the dark theme,
        so theme colours are preserved while font sizes change.
        """
        from PyQt5.QtCore import Qt as _Qt

        font_sizes     = config.get("font_sizes") or {}
        general_offset = font_sizes.get("general", 0)

        def scaled(key: str, default: int) -> int:
            return max(6, font_sizes.get(key, default) + general_offset)

        base_pt   = max(6, 10 + general_offset)
        header_pt = scaled("header", 12)
        button_pt = scaled("button", 10)
        props_pt  = scaled("props",  10)
        mods_pt   = scaled("mods",   10)

        # Set base font object so Qt's non-QSS code picks it up too
        base_font = self.font()
        base_font.setPointSize(base_pt)
        self.setFont(base_font)

        tab_pad_v  = max(4,  header_pt // 3)
        tab_pad_h  = max(10, header_pt)
        btn_pad_v  = max(2,  button_pt // 4)
        btn_pad_h  = max(6,  button_pt)
        btn_min_h  = max(20, button_pt * 2 + 4)

        size_qss = f"""
            QWidget        {{ font-size: {base_pt}px; }}
            QLabel         {{ font-size: {base_pt}px; }}
            QLineEdit      {{ font-size: {base_pt}px; }}
            QSpinBox       {{ font-size: {base_pt}px; }}
            QDoubleSpinBox {{ font-size: {base_pt}px; }}
            QCheckBox      {{ font-size: {base_pt}px; }}
            QRadioButton   {{ font-size: {base_pt}px; }}
            QGroupBox      {{ font-size: {base_pt}px; }}
            QGroupBox::title {{ font-size: {header_pt}px; font-weight: bold; }}
            QPushButton    {{ font-size: {button_pt}px;
                              padding: {btn_pad_v}px {btn_pad_h}px;
                              min-height: {btn_min_h}px; }}
            QComboBox      {{ font-size: {button_pt}px; }}
            QTabBar::tab   {{ font-size: {header_pt}px;
                              padding: {tab_pad_v}px {tab_pad_h}px; }}
            QTableWidget   {{ font-size: {mods_pt}px; }}
            QTableWidget::item {{ padding: 1px 3px; }}
            QScrollBar     {{ width: 10px; }}
        """
        marker   = "/* font-size-overrides */"
        base_qss = self.styleSheet().split(marker)[0]
        self.setStyleSheet(base_qss + marker + size_qss)

        # Prevent tab text from being elided (clipped with "...") at large sizes
        try:
            self._tab_widget.tabBar().setElideMode(_Qt.ElideNone)
        except AttributeError:
            pass

        try:
            self._scan_filters_tab.apply_font_sizes(
                mods_pt=mods_pt,
                props_pt=props_pt,
                button_pt=button_pt,
            )
        except AttributeError:
            pass


    @property
    def loadout_tab(self):
        """Compatibility-friendly name kept for controller code.

        Internally the widget is now called ``_scan_filters_tab`` because that
        describes what it really is: the tab that owns loadouts, slots, and
        scan filters. The public property keeps outside code simple.
        """
        return self._scan_filters_tab
