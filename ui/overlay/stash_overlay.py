"""
ui/overlay_pkg/stash_overlay.py
─────────────────────────────────────────────────────────────────────────────
PURPOSE
    StashOverlay — the coordinator that owns all four overlay pieces
    and provides a clean command API for the application controller.

    This is the "GameManager" of the overlay system.  It doesn't draw
    anything itself — it delegates to the four specialist classes:
        • DraggableGrid  (grid.py)    — alignment grid window
        • ItemCanvas     (canvas.py)  — coloured item outlines
        • HudToolbar     (toolbar.py) — floating control sidebar
        • ItemTooltip    (tooltip.py) — hover detail popup

    AppController only ever touches StashOverlay.  It never directly calls
    methods on the grid, canvas, or toolbar.

────────────────────────────────────────────────────────────────────────────
EVENT / COMMAND BOUNDARY — what this means and why it matters
────────────────────────────────────────────────────────────────────────────

    In a Unity project you'd have a pattern like:
        GameManager.TriggerScan()   ← external command
        GameManager._onScanDone()   ← internal response

    This file implements exactly that boundary for the overlay:

    COMMANDS (public methods — called by the application controller):
        apply_scan_results(items, total_filters)  — "here are the scan results"
        clear_items()                             — "clear the overlay"
        set_grid_params(gx, gy, cell, cols, rows) — "calibration changed"
        toggle_visible()                          — "F9 pressed"
        set_stash_tabs(tabs)                      — "tab list loaded"
        set_current_tab_id(tab_id)                — "stash tab changed"

    EVENTS (signals — connected by the application controller):
        hud.sig_scan            → AppController triggers a scan
        hud.sig_open_config     → AppController shows the config window
        hud.sig_open_filters    → AppController shows the filters tab
        hud.sig_tab_changed     → AppController updates the selected stash tab
        hud.sig_loadout_changed → AppController switches the active loadout
        grid.params_changed     → AppController updates calibration spinboxes

    The point of this boundary:
        The application controller describes WHAT should happen ("scan results arrived").
        StashOverlay decides HOW to handle it (which pieces to update).
        The application controller never needs to know that a canvas, grid, and tooltip exist.

────────────────────────────────────────────────────────────────────────────
MODULE-LEVEL INSTANCE REGISTRY
────────────────────────────────────────────────────────────────────────────

    Some settings (hover tooltip toggle, overlay colour changes) need to
    reach the running overlay instance without going through the application controller.
    The overlay settings tab can call get_running_instance() to do this directly.

    register_instance() is called once by the application startup flow after creating StashOverlay.
"""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore    import QObject
from PyQt5.QtWidgets import QApplication

import config as _cfg
from logic.item_parser import ParsedItem

from ui.overlay.grid    import DraggableGrid
from ui.overlay.canvas  import ItemCanvas
from ui.overlay.toolbar import HudToolbar
from ui.overlay.tooltip import ItemTooltip


class StashOverlay(QObject):
    """
    Coordinator for all overlay components.

    Owns the grid, canvas, toolbar, and tooltip.
    Provides a command API for AppController to call.

    Think of it as a scene root in Unity that wires all child components
    together and responds to external commands.
    """

    def __init__(self):
        super().__init__()

        # ── Create the four overlay components ────────────────────────────────
        # Order matters: grid must exist before canvas and tooltip (they reference it)

        self.grid    = DraggableGrid()
        self.canvas  = ItemCanvas(self.grid)
        self.hud     = HudToolbar()
        self.tooltip = ItemTooltip(self.grid)

        # Whether all overlay components are currently visible
        self._all_visible: bool = True

        # ── Wire internal signals ─────────────────────────────────────────────
        # These are connections WITHIN the overlay system.
        # (External connections — to AppController — are made by AppController itself.)

        self.hud.sig_toggle.connect(self._on_eye_toggled)
        self.hud.sig_lock_toggle.connect(self._on_lock_toggled)

        # ── Apply saved hover-tooltip setting ─────────────────────────────────
        ui_config = _cfg.get("ui") or {}
        if ui_config.get("hover_tooltip", True):
            self.tooltip.start()
        # If hover_tooltip is False, tooltip stays stopped until enabled in settings

    # ─────────────────────────────────────────────────────────────────────────
    # COMMAND API — called by AppController (the event/command boundary)
    # ─────────────────────────────────────────────────────────────────────────

    def apply_scan_results(self, items: list[ParsedItem],
                            total_filters: int = 0) -> None:
        """
        COMMAND: Display the results of a completed stash scan.

        Passes the item list to both the canvas (to draw outlines) and the
        tooltip (to know what to display on hover).

        Args:
            items:         Scored ParsedItem list from ScanWorker.
            total_filters: Number of active mod filters (drives colour logic).
        """
        self.canvas.set_items(items, total_filters=total_filters)
        self.tooltip.set_items(items)

    # Alias kept so AppController can call overlay.set_items() without changes.
    # Both names do exactly the same thing — prefer apply_scan_results() in new code.
    set_items = apply_scan_results

    def clear_items(self) -> None:
        """
        COMMAND: Remove all item outlines and tooltip data.

        Called when the user clears their filters or switches stash tabs.
        """
        self.canvas.set_items([])
        self.tooltip.set_items([])

    def set_grid_params(self, gx: int, gy: int, cell: float,
                         cols: int, rows: int) -> None:
        """
        COMMAND: Update the grid position and dimensions.

        Called when the calibration spinboxes change in the config window.
        Redraws the canvas so item outlines move to match the new grid.
        """
        self.grid.set_params(gx, gy, cell, cols, rows)
        self.canvas.update()

    def toggle_visible(self) -> None:
        """
        COMMAND: Toggle the entire overlay on or off.

        Called by the F9 hotkey in the application controller.
        Toggles the grid, canvas, and tooltip together.
        Also updates the eye button appearance in the toolbar.
        """
        self._all_visible = not self._all_visible
        self.grid.set_visible(self._all_visible)
        self.canvas.set_visible(self._all_visible)
        self.hud.set_overlay_on(self._all_visible)

        if self._all_visible:
            self.tooltip.start()
        else:
            self.tooltip.stop()

    def set_stash_tabs(self, tabs: list[dict]) -> None:
        """
        COMMAND: Populate the TAB dropdown in the toolbar with the given tabs.

        Args:
            tabs: list of dicts like [{"name": "...", "id": "..."}, ...]
        """
        self.hud.set_stash_tabs(tabs)

    def set_current_tab_id(self, tab_id: str) -> None:
        """
        COMMAND: Select a specific tab in the toolbar's TAB dropdown.

        Called when the user changes the stash tab in the config window,
        so the toolbar stays in sync.
        """
        self.hud.set_current_tab_id(tab_id)

    # ─────────────────────────────────────────────────────────────────────────
    # Internal event handlers — triggered by toolbar signals
    # ─────────────────────────────────────────────────────────────────────────

    def _on_eye_toggled(self) -> None:
        """
        The toolbar's eye button was clicked.

        Toggles the grid and canvas together (tooltip follows).
        The toolbar button appearance is already updated by HudToolbar itself.
        """
        self._all_visible = not self._all_visible
        self.grid.set_visible(self._all_visible)
        self.canvas.set_visible(self._all_visible)

        if self._all_visible:
            self.tooltip.start()
        else:
            self.tooltip.stop()

    def _on_lock_toggled(self) -> None:
        """
        The toolbar's lock button was clicked.

        Toggles the grid between locked (click-through) and unlocked (draggable).
        Updates the toolbar button appearance to match.
        Redraws the canvas so outlines stay aligned after any grid move.
        """
        new_locked_state = not self.grid.is_locked
        self.grid.set_locked(new_locked_state)
        self.hud.set_grid_locked(new_locked_state)
        self.canvas.update()


# ─────────────────────────────────────────────────────────────────────────────
# Module-level instance registry
# ─────────────────────────────────────────────────────────────────────────────
# Stores a reference to the single running StashOverlay instance.
# This lets the overlay settings tab reach the live overlay without going through the application controller.
#
# Only one StashOverlay should ever exist — this acts as a lightweight singleton.

_running_instance: Optional[StashOverlay] = None


def register_instance(instance: StashOverlay) -> None:
    """
    Register the single running StashOverlay instance.

    Called once by the application startup flow immediately after creating the overlay:
        overlay = StashOverlay()
        register_instance(overlay)
    """
    global _running_instance
    _running_instance = instance


def get_running_instance() -> Optional[StashOverlay]:
    """
    Return the running StashOverlay instance, or None if not yet created.

    Used by the overlay settings tab to apply live settings (hover tooltip toggle,
    colour changes) directly to the running overlay.
    """
    return _running_instance
