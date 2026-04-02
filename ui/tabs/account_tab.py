"""
ui/tabs/account_tab.py
─────────────────────────────────────────────────────────────────────────────
PURPOSE
    Builds and manages the "Account" tab in the MainWindow.

    This tab lets the user:
      • Enter their OAuth Client ID and User-Agent string.
      • Click "Login" to go through GGG's official OAuth 2.1 PKCE flow in the browser.
      • Select which league and stash tab to scan.
      • Click "Load Tabs" to fetch the tab list from GGG's API.

LAYOUT (top to bottom)
    ┌──────────────────────────────────────┐
    │  OAuth 2.1 Authentication            │  ← GroupBox
    │    Client ID  [text field]           │
    │    User-Agent [text field]           │
    │    [Login with GGG OAuth]            │
    │    Status: Not connected             │
    ├──────────────────────────────────────┤
    │  League & Stash                      │  ← GroupBox
    │    League: [dropdown]                │
    │    Stash tab: [dropdown] [Load tabs] │
    └──────────────────────────────────────┘

BACK-END
    Network work now lives in dedicated workers/services/repositories.
    This file focuses on widget creation, layout, and signal wiring.

SIGNALS EMITTED (for MainWindow to connect)
    token_acquired(str)    — OAuth token obtained successfully
    stashes_loaded(list)   — stash tab summaries returned from GGG API
    stash_tab_selected(str)— user changed the stash tab dropdown selection
"""

from __future__ import annotations

import config as _config

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QGroupBox, QMessageBox,
)
from PyQt5.QtCore import pyqtSignal, pyqtSlot

from ui.shared import LEAGUES, TAB_TYPE_BADGE, make_scrollable
from repositories.config_repository import (
    save_client_id,
    save_user_agent,
    get_saved_league,
    get_saved_stash_id,
)
from services.oauth_login_service import perform_oauth_login
from models import coerce_stash_tab_summary
from workers.stash_list_worker import StashListWorker


class AccountTab(QWidget):
    """
    The Account tab widget.

    Emits signals so MainWindow can react to login and stash-load events
    without this widget needing to know about the rest of the window.
    """

    # ── Signals ───────────────────────────────────────────────────────────────

    # Emitted when OAuth login succeeds — carries the access token string
    token_acquired = pyqtSignal(str)

    # Emitted when the stash tab list is successfully fetched from GGG API.
    # The list contains StashTabSummary objects.
    stashes_loaded = pyqtSignal(list)

    # Emitted when the user changes the stash tab dropdown — carries the stash tab ID string
    stash_tab_selected = pyqtSignal(str)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        # The OAuth access token — stored here so _on_load_stashes_clicked can use it
        self._current_token: str = ""

        # Background worker for fetching the stash list — stored to prevent garbage collection
        self._stash_fetch_worker: StashListWorker | None = None

        self._build_layout()
        self._restore_saved_values()

    # ─────────────────────────────────────────────────────────────────────────
    # Build the widget layout
    # ─────────────────────────────────────────────────────────────────────────

    def _build_layout(self) -> None:
        """Create all widgets and arrange them in the tab."""
        content_widget = QWidget()
        main_layout    = QVBoxLayout(content_widget)

        main_layout.addWidget(self._build_oauth_group())
        main_layout.addWidget(self._build_league_stash_group())
        main_layout.addStretch()  # push everything to the top

        # Wrap in a scroll area so the tab scrolls if the window is small
        scroll = make_scrollable(content_widget)
        wrapper_layout = QVBoxLayout(self)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(scroll)

    def _build_oauth_group(self) -> QGroupBox:
        """
        Build the OAuth 2.1 Authentication group box.

        Contains the Client ID field, User-Agent field, Login button,
        status label field.
        """
        group_box  = QGroupBox("OAuth 2.1 Authentication")
        group_layout = QVBoxLayout(group_box)

        # ── Client ID field ───────────────────────────────────────────────────
        client_id_row = QHBoxLayout()
        client_id_row.addWidget(QLabel("Client ID:"))

        self._client_id_field = QLineEdit()
        self._client_id_field.setPlaceholderText(
            "your_client_id from developer.pathofexile.com"
        )
        self._client_id_field.setText(_config.OAUTH.get("client_id", ""))
        self._client_id_field.textChanged.connect(
            lambda text: save_client_id(text)
        )
        client_id_row.addWidget(self._client_id_field, stretch=1)
        group_layout.addLayout(client_id_row)

        # ── User-Agent field ──────────────────────────────────────────────────
        user_agent_row = QHBoxLayout()
        user_agent_row.addWidget(QLabel("User-Agent:"))

        self._user_agent_field = QLineEdit()
        self._user_agent_field.setPlaceholderText(
            "AppName/1.0 (contact: you@email.com)"
        )
        self._user_agent_field.setText(_config.API.get("user_agent", ""))
        self._user_agent_field.textChanged.connect(
            lambda text: save_user_agent(text)
        )
        user_agent_row.addWidget(self._user_agent_field, stretch=1)
        group_layout.addLayout(user_agent_row)

        # ── Login button ──────────────────────────────────────────────────────
        self._login_button = QPushButton("Login with GGG OAuth")
        self._login_button.setStyleSheet(
            "background:#2a4a2a; color:#88ff88; border:1px solid #448844;"
            " border-radius:3px; padding:6px 16px;"
            " font-weight:bold; font-size:11px;"
        )
        self._login_button.clicked.connect(self._on_login_clicked)
        group_layout.addWidget(self._login_button)

        # ── Auth status label ─────────────────────────────────────────────────
        # Shows "Not connected", "Authenticated", or error messages
        self._auth_status_label = QLabel("Not connected")
        self._auth_status_label.setStyleSheet("color:#ff8888;")
        group_layout.addWidget(self._auth_status_label)

        # ── Registration hint ─────────────────────────────────────────────────
        hint_label = QLabel(
            "Register your app at pathofexile.com/developer/docs\n"
            "→ client_id and User-Agent must match exactly."
        )
        hint_label.setStyleSheet("color:#666; font-size:9px;")
        hint_label.setWordWrap(True)
        group_layout.addWidget(hint_label)

        return group_box

    def _build_league_stash_group(self) -> QGroupBox:
        """
        Build the League & Stash group box.

        Contains the league dropdown, stash tab dropdown, and Load Tabs button.
        """
        group_box    = QGroupBox("League & Stash")
        group_layout = QVBoxLayout(group_box)

        # ── League dropdown ───────────────────────────────────────────────────
        league_row = QHBoxLayout()
        league_row.addWidget(QLabel("League:"))

        self._league_dropdown = QComboBox()
        self._league_dropdown.setEditable(True)   # allow typing a custom league name
        for league_name in LEAGUES:
            self._league_dropdown.addItem(league_name)
        league_row.addWidget(self._league_dropdown, stretch=1)
        group_layout.addLayout(league_row)

        # ── Stash tab dropdown + Load button ──────────────────────────────────
        stash_row = QHBoxLayout()
        stash_row.addWidget(QLabel("Stash tab:"))

        self._stash_dropdown = QComboBox()
        self._stash_dropdown.currentIndexChanged.connect(
            self._on_stash_selection_changed
        )
        stash_row.addWidget(self._stash_dropdown, stretch=1)

        self._load_tabs_button = QPushButton("Load tabs")
        self._load_tabs_button.clicked.connect(self._on_load_stashes_clicked)
        stash_row.addWidget(self._load_tabs_button)
        group_layout.addLayout(stash_row)

        return group_box

    # ─────────────────────────────────────────────────────────────────────────
    # Restore saved values from config on startup
    # ─────────────────────────────────────────────────────────────────────────

    def _restore_saved_values(self) -> None:
        """
        Load previously saved values from config.json and fill the widgets.
        Called once at startup so the user doesn't have to re-enter everything.
        """
        # League — find and select the saved league in the dropdown
        saved_league = get_saved_league()
        index = self._league_dropdown.findText(saved_league)
        if index >= 0:
            self._league_dropdown.setCurrentIndex(index)
        else:
            self._league_dropdown.setCurrentText(saved_league)

    # ─────────────────────────────────────────────────────────────────────────
    # Public interface — called by MainWindow
    # ─────────────────────────────────────────────────────────────────────────

    def get_selected_league(self) -> str:
        """Return the currently selected league name."""
        return self._league_dropdown.currentText()

    def get_selected_stash_id(self) -> str:
        """Return the stash tab ID currently selected in the dropdown."""
        return self._stash_dropdown.currentData() or ""

    def set_token(self, token: str) -> None:
        """
        Called by MainWindow when an OAuth token is obtained externally
        (e.g. loaded from cache on startup).
        Updates the status label to show the user they are authenticated.
        """
        self._current_token = token
        self._auth_status_label.setText("Authenticated")
        self._auth_status_label.setStyleSheet("color:#88ff88;")

    def populate_stash_tab_list(self, tabs: list) -> None:
        """
        Fill the stash tab dropdown with the provided list of tabs.

        Called either after a successful "Load tabs" fetch, or when the
        scan filter tab also receives the list (to keep both dropdowns in sync).

        The saved stash ID from config is restored as the current selection
        so the user's previous choice is preserved.

        Args:
            tabs: list of StashTabSummary objects or older dict-like payloads
        """
        saved_stash_id = get_saved_stash_id()

        self._stash_dropdown.blockSignals(True)
        self._stash_dropdown.clear()

        for tab in tabs:
            stash_tab = coerce_stash_tab_summary(tab)
            badge = TAB_TYPE_BADGE.get(stash_tab.type, f" [{stash_tab.type_value}]")
            self._stash_dropdown.addItem(f"{stash_tab.name}{badge}", stash_tab.id)

        # Restore the previously selected stash tab if it still exists in the list
        for i in range(self._stash_dropdown.count()):
            if self._stash_dropdown.itemData(i) == saved_stash_id:
                self._stash_dropdown.setCurrentIndex(i)
                break

        self._stash_dropdown.blockSignals(False)

        # Show success message
        if tabs:
            self._auth_status_label.setText(
                f"Connected  •  {len(tabs)} tabs loaded"
            )
            self._auth_status_label.setStyleSheet("color:#88ff88;")

        self._load_tabs_button.setEnabled(True)

    # ─────────────────────────────────────────────────────────────────────────
    # Slot handlers — called when widgets fire events
    # ─────────────────────────────────────────────────────────────────────────

    def _on_login_clicked(self) -> None:
        """Handle the "Login with GGG OAuth" button click."""
        try:
            token = perform_oauth_login()
            self._current_token = token
            self._auth_status_label.setText("Authenticated")
            self._auth_status_label.setStyleSheet("color:#88ff88;")
            self.token_acquired.emit(token)
        except Exception as error:
            QMessageBox.critical(self, "Login Failed", f"Could not complete OAuth login. {error}")
            self._auth_status_label.setText("Auth failed")
            self._auth_status_label.setStyleSheet("color:#ff8888;")

    def _on_load_stashes_clicked(self) -> None:
        """
        Handle the "Load tabs" button click.
        Starts a background fetch of the stash tab list from GGG's API.
        """
        token = self._current_token
        if not token:
            QMessageBox.warning(
                self,
                "Not Authenticated",
                "Please login with GGG OAuth first."
            )
            return

        league = self._league_dropdown.currentText()
        self._load_tabs_button.setEnabled(False)   # prevent double-click

        # Run the API call in a background thread
        self._stash_fetch_worker = StashListWorker(
            token=token,
            league=league,
        )
        self._stash_fetch_worker.stash_list_ready.connect(self._on_stashes_fetched)
        self._stash_fetch_worker.error.connect(self._on_stash_fetch_failed)
        self._stash_fetch_worker.start()

    @pyqtSlot(list)
    def _on_stashes_fetched(self, stashes: list) -> None:
        """Called on the main thread when the background fetch succeeds."""
        self.populate_stash_tab_list(stashes)
        # Notify MainWindow so it can also populate the scan filter tab's dropdown
        self.stashes_loaded.emit(stashes)

    @pyqtSlot(str)
    def _on_stash_fetch_failed(self, error_message: str) -> None:
        """Called on the main thread when the background fetch fails."""
        QMessageBox.critical(self, "Could Not Load Stash Tabs", error_message)
        self._load_tabs_button.setEnabled(True)

    def _on_stash_selection_changed(self, _index: int) -> None:
        """Called when the user changes the stash tab dropdown selection."""
        stash_id = self._stash_dropdown.currentData() or ""
        if stash_id:
            self.stash_tab_selected.emit(stash_id)
