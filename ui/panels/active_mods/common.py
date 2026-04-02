from __future__ import annotations

"""Small shared values used by the active-mod panel widgets."""

from models import ActiveModBehaviour

ACTIVE_MOD_DRAG_MIME = "application/x-poe-stash-helper-active-mod"

BEHAVIOUR_LABELS = [behaviour.value for behaviour in ActiveModBehaviour]
BEHAVIOUR_TIPS = {
    ActiveModBehaviour.AND: "ALL selected mods must be present with their value conditions",
    ActiveModBehaviour.NOT: "NONE of these mods may appear on the item",
    ActiveModBehaviour.IF: "Conditions apply only IF the mod is present (optional match)",
    ActiveModBehaviour.COUNT: "At least N of these conditions must match (set N in the header)",
}
HEADER_COLORS = {
    ActiveModBehaviour.AND: "#1e2e4e",
    ActiveModBehaviour.NOT: "#3a1a1a",
    ActiveModBehaviour.IF: "#1a2e1a",
    ActiveModBehaviour.COUNT: "#2a2010",
}
HEADER_BORDERS = {
    ActiveModBehaviour.AND: "#3355aa",
    ActiveModBehaviour.NOT: "#aa3333",
    ActiveModBehaviour.IF: "#335533",
    ActiveModBehaviour.COUNT: "#aa8822",
}


def qss_button(background: str, border: str, foreground: str, padding: str, radius: str) -> str:
    return (
        "QPushButton{" +
        f"background:{background};border:1px solid {border};border-radius:{radius};" +
        f"color:{foreground};padding:{padding};" +
        "}" +
        # Qt stylesheets do not support the CSS `filter` property.
        # Use a slightly lighter border/background cue on hover instead.
        f"QPushButton:hover{{border:1px solid {foreground};}}"
    )
