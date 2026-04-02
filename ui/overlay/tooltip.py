"""
ui/overlay/tooltip.py
─────────────────────────────────────────────────────────────────────────────
PURPOSE
    ItemTooltip — a floating popup that appears when the user hovers their
    mouse over a highlighted stash item.

    It shows:
        • The item's display name
        • Each matched mod with its tier (✔ Maximum Life [T1])
        • The overall match score as a percentage

WHY POLLING INSTEAD OF MOUSE EVENTS?
    The ItemCanvas window has WindowTransparentForInput set, which means it
    receives NO mouse events — all mouse input passes through to the game.
    We cannot use standard Qt mouse-hover events.

    Instead, we use a QTimer that fires every 80ms and checks the cursor's
    current screen position.  We then manually calculate which grid cell the
    cursor is over and look up which item is there.

    This polling approach has a tiny overhead (running every 80ms) but is
    invisible to the user and is the only reliable way to detect "hover"
    on a click-through window.

POSITIONING
    The tooltip appears to the right and slightly below the cursor.
    If it would go off the right edge of the screen, it flips to the left.
    If it would go off the bottom, it flips upward.

RELATIONSHIP TO OTHER FILES
    • grid.py provides the grid coordinates needed to convert cursor position
      to a grid cell.
    • stash_overlay.py owns the tooltip and calls set_items() and start()/stop().
    • the overlay settings tab's hover tooltip checkbox calls start()/stop() at runtime.
"""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore    import Qt, QTimer
from PyQt5.QtGui     import QPainter, QColor, QPen, QFont, QBrush, QFontMetrics, QCursor
from PyQt5.QtWidgets import QWidget, QApplication

from logic.item_parser import ParsedItem
from logic.mod_scorer  import score_tier

from ui.overlay.grid import DraggableGrid


class ItemTooltip(QWidget):
    """
    Floating "Why highlighted?" tooltip that follows the mouse over the stash grid.

    Starts hidden.  Call start() to begin polling and stop() to pause it.
    The tooltip auto-hides when the cursor leaves the grid or moves to an
    item with no match data.
    """

    # How often to check the cursor position (milliseconds).
    # 80ms = ~12 checks per second — fast enough to feel responsive.
    _POLL_INTERVAL_MS = 80

    # How far right and below the cursor the tooltip appears (pixels)
    _OFFSET_X = 14
    _OFFSET_Y = 10

    def __init__(self, grid: DraggableGrid, parent=None):
        super().__init__(parent)

        # We need the grid to map cursor position → grid cell → item
        self._grid = grid

        # The items from the last scan — set by StashOverlay.set_items()
        self._items: list[ParsedItem] = []

        # The item shown in the PREVIOUS poll cycle.
        # Tracking this avoids rebuilding the tooltip content every 80ms
        # when the cursor hasn't moved to a different item.
        self._last_shown_item: Optional[ParsedItem] = None

        # Window flags: frameless, always on top, does not steal focus from the game
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus   # ← crucial — don't steal focus from PoE
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.hide()

        # Polling timer — fires _poll() every _POLL_INTERVAL_MS milliseconds
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(self._POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._poll)

        # Fonts used in the tooltip content
        self._font_item_name  = QFont("Segoe UI", 10)
        self._font_item_name.setBold(True)
        self._font_mod_line   = QFont("Segoe UI", 9)
        self._font_score_line = QFont("Segoe UI", 9)
        self._font_score_line.setBold(True)

        # Internal render data — built by _build_content(), read by paintEvent()
        self._render_lines:   list[tuple] = []   # (text, QColor, QFont)
        self._render_heights: list[int]   = []
        self._padding_x:      int = 0
        self._padding_y:      int = 0
        self._line_gap:       int = 0

    # ─────────────────────────────────────────────────────────────────────────
    # Public API — called by StashOverlay
    # ─────────────────────────────────────────────────────────────────────────

    def set_items(self, items: list[ParsedItem]) -> None:
        """
        Replace the current item list.

        Called by StashOverlay after each scan.  Also resets the "last shown"
        item so the tooltip rebuilds immediately if the cursor is already over
        an item.
        """
        self._items           = items
        self._last_shown_item = None

    def start(self) -> None:
        """Begin the cursor-polling loop.  Shows the tooltip when hovering."""
        self._poll_timer.start()

    def stop(self) -> None:
        """Stop the cursor-polling loop and hide the tooltip."""
        self._poll_timer.stop()
        self.hide()

    # ─────────────────────────────────────────────────────────────────────────
    # Polling and hit detection
    # ─────────────────────────────────────────────────────────────────────────

    def _poll(self) -> None:
        """
        Called every _POLL_INTERVAL_MS milliseconds.

        Checks whether the cursor is over a highlighted item and either
        shows, updates, or hides the tooltip accordingly.
        """
        if not self._items:
            self.hide()
            return

        cursor_pos = QCursor.pos()   # global screen coordinates
        hovered_item = self._find_item_at(cursor_pos)

        if hovered_item is None:
            # Cursor is not over any highlighted item — hide the tooltip
            if self.isVisible():
                self.hide()
            self._last_shown_item = None
            return

        # Only rebuild the tooltip content if we moved to a different item
        if hovered_item is not self._last_shown_item:
            self._last_shown_item = hovered_item
            self._build_content(hovered_item)

        # Position the tooltip near the cursor, flipping if near screen edge
        self._position_near_cursor(cursor_pos)

        if not self.isVisible():
            self.show()
            self.raise_()

    def _find_item_at(self, cursor_screen_pos) -> Optional[ParsedItem]:
        """
        Return the stash item whose grid cell contains the cursor, or None.

        Converts the cursor's screen coordinates to a grid cell (col, row),
        then searches the item list for any item that occupies that cell.

        Only returns items that have match data worth showing (matched mods
        or a non-zero score) — items with no display data are skipped.
        """
        grid_origin_x = self._grid._gx
        grid_origin_y = self._grid._gy
        cell_size     = self._grid._cell
        grid_cols     = self._grid._cols
        grid_rows     = self._grid._rows

        # Convert absolute screen coordinates to position relative to grid origin
        relative_x = cursor_screen_pos.x() - grid_origin_x
        relative_y = cursor_screen_pos.y() - grid_origin_y

        # Cursor is to the left of or above the grid
        if relative_x < 0 or relative_y < 0:
            return None

        # Convert to grid cell coordinates
        col = int(relative_x // cell_size)
        row = int(relative_y // cell_size)

        # Cursor is past the right or bottom edge of the grid
        if col >= grid_cols or row >= grid_rows:
            return None

        # Find which item (if any) occupies this cell
        for item in self._items:
            item_occupies_cell = (
                item.x <= col < item.x + item.w and
                item.y <= row < item.y + item.h
            )
            if item_occupies_cell:
                # Only show the tooltip if there's something useful to display
                has_display_data = (
                    bool(item.matched_mods) or
                    bool(getattr(item, "score", None))
                )
                if has_display_data:
                    return item

        return None

    def _position_near_cursor(self, cursor_pos) -> None:
        """
        Move the tooltip window near the cursor, staying on screen.

        Tries to place it to the right and below the cursor.
        Flips left if it would go off the right edge.
        Flips up if it would go off the bottom edge.
        """
        screen = QApplication.screenAt(cursor_pos) or QApplication.primaryScreen()
        screen_rect = screen.geometry()

        x = cursor_pos.x() + self._OFFSET_X
        y = cursor_pos.y() + self._OFFSET_Y

        if x + self.width() > screen_rect.right():
            x = cursor_pos.x() - self.width() - self._OFFSET_X

        if y + self.height() > screen_rect.bottom():
            y = cursor_pos.y() - self.height() - self._OFFSET_Y

        self.move(x, y)

    # ─────────────────────────────────────────────────────────────────────────
    # Content building
    # ─────────────────────────────────────────────────────────────────────────

    def _build_content(self, item: ParsedItem) -> None:
        """
        Build the list of text lines to display for the given item.

        Each line is a tuple: (text, QColor, QFont).
        After building the lines, we measure their widths and heights
        so we can resize the tooltip window to fit exactly.
        """
        lines: list[tuple[str, QColor, QFont]] = []

        # ── Line 1: Item name ─────────────────────────────────────────────
        lines.append((
            item.display_name,
            QColor(255, 220, 100),   # warm yellow — stands out as the header
            self._font_item_name,
        ))

        # ── Lines 2–N: Matched mods ───────────────────────────────────────
        # Colour each mod line by its tier:
        #   T1 = gold (best), T2 = green, T3 = amber, else = grey
        has_mod_lines = False
        for mod_label in (item.matched_mods or []):
            if "[T1]" in mod_label:
                mod_color = QColor(255, 215, 0)    # gold — top tier
            elif "[T2]" in mod_label:
                mod_color = QColor(130, 220, 130)  # green
            elif "[T3]" in mod_label:
                mod_color = QColor(200, 180, 80)   # amber
            else:
                mod_color = QColor(180, 180, 180)  # grey — low tier or unknown

            lines.append((
                f"  ✔  {mod_label}",
                mod_color,
                self._font_mod_line,
            ))
            has_mod_lines = True

        # ── Last line: Score percentage ───────────────────────────────────
        score = getattr(item, "score", None)
        if score is not None and score > 0 and has_mod_lines:
            score_percent = int(score * 100)
            tier = score_tier(score)

            tier_color_map = {
                "tier1": QColor(255, 215,   0),   # gold
                "tier2": QColor(100, 220, 100),   # green
                "tier3": QColor(220, 160,  50),   # orange
                "tier4": QColor(220,  80,  80),   # red
            }
            score_color = tier_color_map.get(tier, QColor(200, 200, 200))

            lines.append((
                f"  Score:  {score_percent}%",
                score_color,
                self._font_score_line,
            ))

        # Nothing to show — hide immediately
        if not lines:
            self.hide()
            return

        # ── Measure each line and resize the tooltip to fit ───────────────
        padding_x = 10
        padding_y = 8
        line_gap  = 4

        line_widths  = []
        line_heights = []
        for text, _, font in lines:
            metrics = QFontMetrics(font)
            line_widths.append(metrics.horizontalAdvance(text))
            line_heights.append(metrics.height())

        total_width  = max(line_widths)  + padding_x * 2
        total_height = sum(line_heights) + line_gap * (len(lines) - 1) + padding_y * 2

        self.setFixedSize(total_width, total_height)

        # Store for use in paintEvent()
        self._render_lines   = lines
        self._render_heights = line_heights
        self._padding_x      = padding_x
        self._padding_y      = padding_y
        self._line_gap       = line_gap

        self.update()   # trigger a repaint with the new content

    # ─────────────────────────────────────────────────────────────────────────
    # Painting
    # ─────────────────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        """
        Draw the tooltip background and text lines.

        Qt calls this whenever update() is called or the window is exposed.
        We draw a dark semi-transparent rounded rectangle as the background,
        then paint each text line on top of it.
        """
        if not self._render_lines:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Dark semi-transparent background with a subtle border
        painter.setBrush(QBrush(QColor(15, 15, 20, 220)))
        painter.setPen(QPen(QColor(80, 80, 100, 200), 1))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 6, 6)

        # Paint each text line
        y = self._padding_y
        for i, (text, color, font) in enumerate(self._render_lines):
            line_height = self._render_heights[i]
            painter.setFont(font)
            painter.setPen(color)
            # -2 is a baseline adjustment so text sits correctly within the line height
            painter.drawText(self._padding_x, y + line_height - 2, text)
            y += line_height + self._line_gap

        painter.end()
