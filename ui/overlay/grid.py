"""
ui/overlay/grid.py
─────────────────────────────────────────────────────────────────────────────
PURPOSE
    The DraggableGrid — an always-on-top transparent window that draws
    a white alignment grid over the stash panel.

WHAT THIS IS
    When the user opens their Path of Exile stash, the stash panel appears
    somewhere on their screen.  This grid window overlays a white line grid
    on top of the game window so the user can align it precisely to the
    stash cell boundaries.

    Once aligned and locked, the grid's pixel coordinates are used by
    ItemCanvas to know exactly where to draw outlines for each stash cell.

TWO MODES
    UNLOCKED — the user can:
        • Drag the grid body to move it
        • Drag the right edge handle to change number of columns
        • Drag the bottom edge handle to change number of rows
        • Drag the corner handle to change cell size

    LOCKED — the grid becomes completely click-through (mouse events pass
        straight to the game underneath it).  Only white grid lines are drawn,
        no handles.

SIGNALS
    params_changed(gx, gy, cell, cols, rows)
        Emitted every time the grid moves or is resized.
        StashOverlay connects this to update the calibration spinboxes in
        the config window so they always show the current values.

RELATIONSHIP TO OTHER FILES
    • ItemCanvas (canvas.py) reads grid.item_screen_rect() to know where
      to draw each item's coloured outline.
    • ItemTooltip (tooltip.py) reads grid._gx/_gy/_cell directly to convert
      the mouse cursor position to a grid cell coordinate.
    • StashOverlay (stash_overlay.py) owns the grid instance and calls
      set_params() when the config spinboxes change.
"""

from __future__ import annotations

import config as _cfg

from PyQt5.QtCore    import Qt, QRect, QPoint, pyqtSignal
from PyQt5.QtGui     import QPainter, QColor, QPen, QFont, QBrush, QCursor
from PyQt5.QtWidgets import QWidget, QApplication


# Pixel size of the resize drag handles painted at the grid edges
_HANDLE_SIZE = 10


class DraggableGrid(QWidget):
    """
    Always-on-top transparent window that draws a white grid.

    In LOCKED mode: purely visual, click-through, no interaction.
    In UNLOCKED mode: draggable and resizable with visible handles.

    Emits params_changed whenever position or dimensions change so
    the calibration spinboxes in the config window stay in sync.
    """

    # Emitted with (grid_x, grid_y, cell_size, columns, rows) on every change
    params_changed = pyqtSignal(int, int, float, int, int)

    # Default starting values — used on first launch before any saved config
    _DEFAULTS = dict(gx=100, gy=140, cell=26.0, cols=24, rows=24)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Window flags: no border, always on top, treated as a tool window
        # (tool windows don't show in the taskbar)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Grid geometry — these are the values that matter
        self._gx   = self._DEFAULTS["gx"]    # screen X of grid's top-left corner
        self._gy   = self._DEFAULTS["gy"]    # screen Y of grid's top-left corner
        self._cell = self._DEFAULTS["cell"]  # width/height of one stash cell in pixels
        self._cols = self._DEFAULTS["cols"]  # number of columns
        self._rows = self._DEFAULTS["rows"]  # number of rows

        self._locked  = True    # True = click-through, no handles
        self._visible = True    # False = hide the whole window

        # Drag operation state — only used when unlocked
        self._current_drag_op    = ""      # "move", "col", "row", or "cell"
        self._drag_offset        = QPoint()
        self._drag_origin        = QPoint()
        self._drag_start_gx      = 0
        self._drag_start_gy      = 0
        self._drag_start_cell    = 0.0
        self._drag_start_cols    = 0
        self._drag_start_rows    = 0

        self._load_saved_position()
        self._sync_window_geometry()
        self.show()

    # ─────────────────────────────────────────────────────────────────────────
    # Geometry calculations
    # ─────────────────────────────────────────────────────────────────────────

    def _grid_pixel_width(self) -> int:
        """Total width of the grid in pixels (cell_size × columns)."""
        return int(self._cell * self._cols)

    def _grid_pixel_height(self) -> int:
        """Total height of the grid in pixels (cell_size × rows)."""
        return int(self._cell * self._rows)

    def _drag_padding(self) -> int:
        """
        Extra pixels added around the grid when unlocked.
        This padding gives the user room to grab the resize handles
        which stick out slightly beyond the grid boundary.
        Zero when locked — no padding needed for a click-through window.
        """
        return 0 if self._locked else 18

    def _sync_window_geometry(self) -> None:
        """
        Resize and reposition the Qt window to match the current grid values.

        The window is slightly larger than the grid when unlocked, to include
        the resize handles.  When locked, the window exactly matches the grid.
        """
        pad = self._drag_padding()
        self.setGeometry(
            self._gx - pad,
            self._gy - pad,
            self._grid_pixel_width()  + pad * 2 + _HANDLE_SIZE,
            self._grid_pixel_height() + pad * 2 + _HANDLE_SIZE,
        )
        # When locked: Qt passes all mouse events straight to windows below
        self.setAttribute(Qt.WA_TransparentForMouseEvents, self._locked)

    def _local_grid_origin_x(self) -> int:
        """
        X position of the grid's top-left corner within this window's
        local coordinate system.  Equals the padding amount.
        """
        return self._drag_padding()

    def _local_grid_origin_y(self) -> int:
        """Y position of the grid's top-left corner in local coordinates."""
        return self._drag_padding()

    # ─────────────────────────────────────────────────────────────────────────
    # Public API — called by StashOverlay and main_window
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def params(self) -> tuple:
        """Return current grid parameters as (gx, gy, cell, cols, rows)."""
        return (
            int(self._gx),
            int(self._gy),
            float(self._cell),
            int(self._cols),
            int(self._rows),
        )

    def item_screen_rect(self, item_x: int, item_y: int,
                          item_w: int, item_h: int) -> QRect:
        """
        Convert a stash-cell position to an absolute screen pixel rectangle.

        Used by ItemCanvas to know exactly where to draw each item's outline.

        Args:
            item_x, item_y: Stash grid coordinates of the item's top-left cell.
            item_w, item_h: Width and height of the item in grid cells.

        Returns:
            A QRect in screen pixel coordinates.

        Example:
            A 2×2 item at grid position (3, 1) with 52px cells:
            → QRect(100 + 3*52, 140 + 1*52, 2*52, 2*52)
            → QRect(256, 192, 104, 104)
        """
        return QRect(
            int(self._gx + item_x * self._cell),
            int(self._gy + item_y * self._cell),
            int(item_w * self._cell),
            int(item_h * self._cell),
        )

    def set_params(self, gx: int, gy: int, cell: float,
                    cols: int, rows: int) -> None:
        """
        Update all grid parameters at once.

        Called when the user types values in the calibration spinboxes.
        Values are clamped to stay on the screen the grid is currently on
        (important for multi-monitor setups — prevents the grid from
        jumping to the wrong screen if a spinbox value is wrong).
        """
        # Find which screen the grid currently sits on
        current_pos = QPoint(int(self._gx), int(self._gy))
        screen = QApplication.screenAt(current_pos) or QApplication.primaryScreen()
        screen_rect = screen.geometry()

        # Apply new values with clamping — only update if the incoming value is valid
        if int(gx) >= 1:
            self._gx = max(screen_rect.left() + 1,
                           min(int(gx), screen_rect.right() - 1))
        if int(gy) >= 1:
            self._gy = max(screen_rect.top() + 1,
                           min(int(gy), screen_rect.bottom() - 1))
        if float(cell) >= 1.0:
            self._cell = float(cell)
        if int(cols) >= 1:
            self._cols = int(cols)
        if int(rows) >= 1:
            self._rows = int(rows)

        self._sync_window_geometry()

        # On some graphics drivers, setGeometry() on a translucent Tool window
        # unexpectedly hides it.  Re-show it if that happened.
        if not self.isVisible():
            self.show()
        self.raise_()
        self.update()

    def set_locked(self, locked: bool) -> None:
        """
        Lock or unlock the grid.

        Locked   → click-through, no handles, normal arrow cursor.
        Unlocked → draggable, resize handles visible, resize cursor.
        """
        self._locked = locked
        self._sync_window_geometry()
        cursor_shape = Qt.ArrowCursor if locked else Qt.SizeAllCursor
        self.setCursor(QCursor(cursor_shape))
        self.update()

    def set_visible(self, visible: bool) -> None:
        """Show or hide the grid window."""
        self._visible = visible
        if visible:
            self.show()
        else:
            self.hide()

    @property
    def is_locked(self) -> bool:
        """True if the grid is currently locked (click-through mode)."""
        return self._locked

    # ─────────────────────────────────────────────────────────────────────────
    # Config persistence
    # ─────────────────────────────────────────────────────────────────────────

    def _load_saved_position(self) -> None:
        """Load previously saved grid position and dimensions from config."""
        saved = _cfg.get("stash_grid") or {}
        screen = QApplication.primaryScreen().geometry()
        screen_w = screen.width()
        screen_h = screen.height()

        raw_gx = int(saved.get("grid_screen_x", self._DEFAULTS["gx"]))
        raw_gy = int(saved.get("grid_screen_y", self._DEFAULTS["gy"]))

        # Clamp to screen bounds.  Reject obviously corrupted values (> 4× screen size).
        self._gx = (
            max(0, min(raw_gx, screen_w - 10))
            if 0 <= raw_gx <= screen_w * 4
            else self._DEFAULTS["gx"]
        )
        self._gy = (
            max(0, min(raw_gy, screen_h - 10))
            if 0 <= raw_gy <= screen_h * 4
            else self._DEFAULTS["gy"]
        )

        self._cell = float(saved.get("cell_size", self._DEFAULTS["cell"]))
        self._cols = max(1, int(saved.get("cols",      self._DEFAULTS["cols"])))
        self._rows = max(1, int(saved.get("rows",      self._DEFAULTS["rows"])))

    def save_position(self) -> None:
        """Save current grid position and dimensions to config."""
        saved = _cfg.get("stash_grid") or {}
        saved.update({
            "grid_screen_x": self._gx,
            "grid_screen_y": self._gy,
            "cell_size":     self._cell,
            "cols":          self._cols,
            "rows":          self._rows,
        })
        _cfg.set_key("stash_grid", saved)

    # ─────────────────────────────────────────────────────────────────────────
    # Painting
    # ─────────────────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        """
        Draw the grid lines and, when unlocked, the drag handles.

        Coordinate system reminder:
            self._lox()/_loy() are the LOCAL coordinates of the grid origin
            (top-left corner of the grid WITHIN this window).  They equal the
            padding amount, which is 0 when locked and 18px when unlocked.
        """
        if not self._visible:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        origin_x = self._local_grid_origin_x()
        origin_y = self._local_grid_origin_y()
        grid_w   = self._grid_pixel_width()
        grid_h   = self._grid_pixel_height()

        # ── Grid lines — white, semi-transparent ─────────────────────────────
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
        painter.setBrush(Qt.NoBrush)

        for row in range(self._rows + 1):
            y = int(origin_y + row * self._cell)
            painter.drawLine(origin_x, y, origin_x + grid_w, y)

        for col in range(self._cols + 1):
            x = int(origin_x + col * self._cell)
            painter.drawLine(x, origin_y, x, origin_y + grid_h)

        # ── Unlocked mode: border, hint text, and resize handles ─────────────
        if not self._locked:
            # Yellow border around the entire grid
            painter.setPen(QPen(QColor(255, 220, 50, 70), 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(origin_x, origin_y, grid_w, grid_h)

            # "drag · lock when done" hint text above the grid
            painter.setFont(QFont("Consolas", 8))
            painter.setPen(QColor(255, 220, 50, 110))
            painter.drawText(origin_x + 2, origin_y - 3, "drag  ·  lock when done")

            # Right-edge handle — drag to change number of columns (blue)
            col_handle = QRect(
                origin_x + grid_w,
                int(origin_y + grid_h / 2) - _HANDLE_SIZE,
                _HANDLE_SIZE,
                _HANDLE_SIZE * 2,
            )
            painter.setBrush(QBrush(QColor(100, 180, 255, 160)))
            painter.setPen(Qt.NoPen)
            painter.drawRect(col_handle)
            painter.setPen(QColor(255, 255, 255, 200))
            painter.setFont(QFont("Consolas", 7))
            painter.drawText(col_handle, Qt.AlignCenter, "||")

            # Bottom-edge handle — drag to change number of rows (blue)
            row_handle = QRect(
                int(origin_x + grid_w / 2) - _HANDLE_SIZE,
                origin_y + grid_h,
                _HANDLE_SIZE * 2,
                _HANDLE_SIZE,
            )
            painter.setBrush(QBrush(QColor(100, 180, 255, 160)))
            painter.setPen(Qt.NoPen)
            painter.drawRect(row_handle)
            painter.setPen(QColor(255, 255, 255, 200))
            painter.drawText(row_handle, Qt.AlignCenter, "=")

            # Corner handle — drag to change cell size (amber)
            cell_handle = QRect(
                origin_x + grid_w,
                origin_y + grid_h,
                _HANDLE_SIZE,
                _HANDLE_SIZE,
            )
            painter.setBrush(QBrush(QColor(255, 180, 50, 200)))
            painter.setPen(Qt.NoPen)
            painter.drawRect(cell_handle)
            painter.setPen(QColor(255, 255, 255, 230))
            painter.drawText(cell_handle, Qt.AlignCenter, "+")

        painter.end()

    # ─────────────────────────────────────────────────────────────────────────
    # Mouse interaction (only active when unlocked)
    # ─────────────────────────────────────────────────────────────────────────

    def _get_hit_zone(self, local_pos: QPoint) -> str:
        """
        Determine which drag zone the mouse is currently over.

        Returns one of:
            "cell"  — corner handle (resizes cell size)
            "col"   — right edge handle (resizes column count)
            "row"   — bottom edge handle (resizes row count)
            "move"  — grid body (moves the whole grid)
            ""      — outside the grid
        """
        ox = self._local_grid_origin_x()
        oy = self._local_grid_origin_y()
        gw = self._grid_pixel_width()
        gh = self._grid_pixel_height()

        if QRect(ox + gw, oy + gh, _HANDLE_SIZE, _HANDLE_SIZE).contains(local_pos):
            return "cell"
        if QRect(ox + gw, oy, _HANDLE_SIZE, gh).contains(local_pos):
            return "col"
        if QRect(ox, oy + gh, gw, _HANDLE_SIZE).contains(local_pos):
            return "row"
        if QRect(ox, oy, gw, gh).contains(local_pos):
            return "move"
        return ""

    def mousePressEvent(self, event) -> None:
        if self._locked or event.button() != Qt.LeftButton:
            return
        zone = self._get_hit_zone(event.pos())
        if not zone:
            return

        # Record where the drag started, so we can compute deltas in mouseMoveEvent
        self._current_drag_op  = zone
        self._drag_origin      = event.globalPos()
        self._drag_offset      = event.globalPos() - QPoint(self._gx, self._gy)
        self._drag_start_gx    = self._gx
        self._drag_start_gy    = self._gy
        self._drag_start_cell  = self._cell
        self._drag_start_cols  = self._cols
        self._drag_start_rows  = self._rows

        cursor_shapes = {
            "move": Qt.SizeAllCursor,
            "col":  Qt.SizeHorCursor,
            "row":  Qt.SizeVerCursor,
            "cell": Qt.SizeFDiagCursor,
        }
        self.setCursor(QCursor(cursor_shapes.get(zone, Qt.SizeAllCursor)))

    def mouseMoveEvent(self, event) -> None:
        if self._locked:
            return

        if not self._current_drag_op:
            # Not dragging — just update cursor based on hover zone
            zone = self._get_hit_zone(event.pos())
            cursor_shapes = {
                "move": Qt.SizeAllCursor,
                "col":  Qt.SizeHorCursor,
                "row":  Qt.SizeVerCursor,
                "cell": Qt.SizeFDiagCursor,
                "":     Qt.SizeAllCursor,
            }
            self.setCursor(QCursor(cursor_shapes[zone]))
            return

        if event.buttons() != Qt.LeftButton:
            return

        delta = event.globalPos() - self._drag_origin

        if self._current_drag_op == "move":
            new_pos = event.globalPos() - self._drag_offset
            screen  = QApplication.primaryScreen().geometry()
            # Prevent snapping to (0, 0) — enforce minimum 1px from screen origin
            self._gx = max(1, min(new_pos.x(), screen.width()  - 1))
            self._gy = max(1, min(new_pos.y(), screen.height() - 1))

        elif self._current_drag_op == "col":
            # Dragging the right handle: total width changes, recalculate column count
            total_width = self._drag_start_cols * self._drag_start_cell + delta.x()
            self._cols  = max(1, round(total_width / self._cell))

        elif self._current_drag_op == "row":
            # Dragging the bottom handle: total height changes, recalculate row count
            total_height = self._drag_start_rows * self._drag_start_cell + delta.y()
            self._rows   = max(1, round(total_height / self._cell))

        elif self._current_drag_op == "cell":
            # Divide by 8 for finer control — 1px drag = 0.125px cell size change
            change     = (delta.x() + delta.y()) / 8.0
            self._cell = max(1.0, round(self._drag_start_cell + change, 2))

        self._sync_window_geometry()
        self.params_changed.emit(*self.params)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._current_drag_op:
            self._current_drag_op = ""
            self.setCursor(QCursor(Qt.SizeAllCursor))
            self.save_position()
            self.params_changed.emit(*self.params)
