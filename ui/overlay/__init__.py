"""
ui/overlay/__init__.py
─────────────────────────────────────────────────────────────────────────────
PURPOSE
    Public API for the overlay package.

    Any code outside this package (the main window, overlay settings tab, controller, etc.) should
    import from here rather than reaching into individual submodules.

    This way, if internal file names change, only this __init__.py needs
    to be updated — none of the callers need to change.

USAGE EXAMPLES
    # In the application startup flow:
    from ui.overlay import StashOverlay, register_instance

    # In the overlay settings tab (settings toggles):
    from ui.overlay import get_running_instance, set_outline_thickness

    # For colour/badge settings:
    from ui.overlay import set_outline_thickness, set_min_matching, set_badge_flag
"""

# The main coordinator — create one of these during application startup
from ui.overlay.stash_overlay import (
    StashOverlay,
    register_instance,
    get_running_instance,
)

# Individual components — rarely needed directly outside the package,
# but exported here for type hints and testing
from ui.overlay.grid    import DraggableGrid
from ui.overlay.canvas  import ItemCanvas
from ui.overlay.toolbar import HudToolbar
from ui.overlay.tooltip import ItemTooltip

# Colour / badge setters — called by the overlay settings tab and startup flow
from ui.overlay.colors import (
    set_outline_color,
    set_outline_palette,
    set_outline_thickness,
    set_min_matching,
    set_badge_flag,
)
from models import OutlineColorRole

__all__ = [
    # Coordinator
    "StashOverlay",
    "register_instance",
    "get_running_instance",
    # Components
    "DraggableGrid",
    "ItemCanvas",
    "HudToolbar",
    "ItemTooltip",
    # Settings enums and setters
    "OutlineColorRole",
    "set_outline_color",
    "set_outline_palette",
    "set_outline_thickness",
    "set_min_matching",
    "set_badge_flag",
]
