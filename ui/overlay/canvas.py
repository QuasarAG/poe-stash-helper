"""
ui/overlay/canvas.py
─────────────────────────────────────────────────────────────────────────────
PURPOSE
    ItemCanvas — a full-screen transparent window that draws coloured
    rectangles on top of the game window to highlight stash items.

WHAT THIS IS
    Imagine a sheet of glass placed over your entire monitor.
    You can click right through it — your mouse goes to the game below.
    But on that glass, coloured rectangles are painted over each stash item
    to show how well it matches your filters.

    This "sheet of glass" IS the ItemCanvas.

    It is technically a Qt window, but with two special flags:
        • WindowTransparentForInput — all mouse/keyboard events pass through
          to whatever is below (the game)
        • WA_TranslucentBackground  — the window background is fully transparent;
          only what the painter draws is visible

HOW IT KNOWS WHERE TO DRAW
    ItemCanvas takes a reference to a DraggableGrid on construction.
    When it needs to draw item (3, 1) [col 3, row 1], it asks the grid:
        grid.item_screen_rect(3, 1, 2, 2)  → QRect(256, 192, 104, 104)
    That rect is where the coloured outline gets drawn.

COLOUR LOGIC
    Colours come from colors.py.  The logic per item is:
        1. "Slot only" — item matches base/properties but no mods are filtered:
           draw a white outline.  Always shown regardless of min_matching.
        2. Mod-count match — use get_mod_count_color() for gold/orange/red.
        3. Score-based (flat filter mode, no slot restrictions):
           use get_score_color() for a tier-based colour.
        4. None of the above → no outline drawn for this item.

RELATIONSHIP TO OTHER FILES
    • grid.py provides item_screen_rect() for coordinate conversion.
    • colors.py provides the colours and badge flags.
    • tooltip.py separately handles hover detection and tooltip rendering.
    • stash_overlay.py owns this canvas and calls set_items() after each scan.
"""

from __future__ import annotations

from PyQt5.QtCore    import Qt
from PyQt5.QtGui     import QPainter, QColor, QPen, QFont, QBrush, QFontMetrics
from PyQt5.QtWidgets import QWidget, QApplication

from logic.item_parser import ParsedItem
from config            import UI

from ui.overlay.grid   import DraggableGrid
from ui.overlay.colors import (
    _OUTLINE_COLORS,
    _OUTLINE_THICKNESS,
    _BADGE_FLAGS,
    get_mod_count_color,
    get_score_color,
)
from models import OutlineColorRole


class ItemCanvas(QWidget):
    """
    Full-screen transparent click-through canvas.

    Draws coloured outlines and badges over stash items after each scan.
    Receives no mouse events — all input passes through to the game below.
    """

    def __init__(self, grid: DraggableGrid, parent=None):
        super().__init__(parent)

        # We need the grid to convert item grid-coordinates to screen pixels
        self.grid = grid

        # The items currently displayed — set by StashOverlay after each scan
        self.items: list[ParsedItem] = []

        # Total number of active mod filters (for colour logic)
        self._total_filters: int = 0

        # Whether items should be drawn at all (toggled by eye button)
        self._visible: bool = True

        # Window setup: frameless, always on top, transparent to mouse input
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowTransparentForInput   # ← mouse clicks pass through to game
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)

        # Cover the entire primary screen
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        # Font for score/count text badges drawn on items
        self._score_font = QFont("Consolas", UI.get("score_font_size", 9))

        # When the grid moves or resizes, redraw all item outlines
        self.grid.params_changed.connect(lambda *_: self.update())

        self.show()

    # ─────────────────────────────────────────────────────────────────────────
    # Public API — called by StashOverlay
    # ─────────────────────────────────────────────────────────────────────────

    def set_items(self, items: list[ParsedItem], total_filters: int = 0) -> None:
        """
        Replace the current item list and trigger a repaint.

        Args:
            items:         List of ParsedItem objects from the last scan.
                           Each item has .x, .y, .w, .h (grid coordinates),
                           .matched_mods (list of matched mod labels), and .score.
            total_filters: Total number of active mod filters for the current slot.
                           Used to determine which colour tier to use.
        """
        self.items          = items
        self._total_filters = total_filters
        self.update()   # triggers paintEvent

    def set_visible(self, visible: bool) -> None:
        """Show or hide all outlines (does not hide the window itself)."""
        self._visible = visible
        self.update()

    # ─────────────────────────────────────────────────────────────────────────
    # Painting
    # ─────────────────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        """
        Draw coloured outlines for every item in self.items.

        Qt calls this automatically whenever update() is called.
        We iterate through all items and draw each one individually.
        """
        if not self._visible or not self.items:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        outline_thickness = _OUTLINE_THICKNESS

        for item in self.items:
            self._draw_single_item(painter, item, outline_thickness)

        painter.end()

    def _draw_single_item(self, painter: QPainter,
                           item: ParsedItem, outline_thickness: int) -> None:
        """
        Draw the coloured outline (and any badges) for one item.

        Colour priority:
            1. Slot-only match (white) — item matched base/properties,
               but no mod filters are set for this slot.
            2. Mod-count match — gold / orange / red based on how many
               required mods the item has.
            3. Score-based colour — used in flat (no-slot) filter mode.
            4. No colour → skip this item, draw nothing.
        """
        matched_count = len(item.matched_mods) if item.matched_mods else 0
        item_total    = getattr(item, "total_filters", 0)

        # ── Determine the outline colour ──────────────────────────────────────
        # "Slot only" means: the item matches the slot/base/property filter,
        # but no mod filters exist for this slot, so there's nothing to score.
        is_slot_only = (item_total == 0 and item.score == 1)

        if is_slot_only:
            # Always white, always shown — not gated by min_matching
            outline_color = QColor(_OUTLINE_COLORS[OutlineColorRole.SLOT_ONLY])
            display_total = 0

        else:
            display_total = item_total
            outline_color = get_mod_count_color(matched_count, display_total)

        # Fallback to score-based colour (flat filter mode — no slot restrictions)
        if outline_color is None and not is_slot_only and display_total == 0:
            if item.score and item.score > 0:
                outline_color = get_score_color(item.score)

        # No colour determined — skip this item
        if outline_color is None:
            return

        # ── Convert grid coordinates to screen pixel rectangle ─────────────
        screen_rect = self.grid.item_screen_rect(item.x, item.y, item.w, item.h)

        # ── Draw the coloured outline rectangle ───────────────────────────
        # adjusted(1, 1, -1, -1) shrinks the rect by 1px on each side so the
        # outline is drawn INSIDE the cell border rather than overlapping adjacent cells
        painter.setPen(QPen(outline_color, outline_thickness))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(screen_rect.adjusted(1, 1, -1, -1))

    def _draw_text_badge(self, painter: QPainter,
                          x: int, y: int, text: str,
                          color: QColor, font: QFont, anchor: str) -> None:
        """
        Draw a small text label with a dark background.

        Args:
            x, y:   Pixel position (meaning depends on anchor).
            text:   The text to display (e.g. "3/4").
            color:  Text colour.
            font:   Font to use.
            anchor: "br" = bottom-right aligned to (x, y),
                    anything else = top-left aligned.
        """
        painter.setFont(font)
        font_metrics = QFontMetrics(font)
        text_width   = font_metrics.horizontalAdvance(text)
        text_height  = font_metrics.height()
        padding      = 3

        if anchor == "br":
            rect_x = x - text_width - padding * 2
            rect_y = y - text_height - padding
        else:
            rect_x = x
            rect_y = y

        # Dark background pill
        painter.setBrush(QBrush(QColor(0, 0, 0, 170)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(
            rect_x, rect_y,
            text_width + padding * 2, text_height + padding,
            4, 4
        )

        # Text on top
        painter.setPen(color)
        painter.drawText(rect_x + padding, rect_y + text_height - 1, text)
