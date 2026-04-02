from __future__ import annotations
"""
Manual auto-packing layout widget for property sections.

The original project already used a custom geometry-based layout here.
That approach is still reasonable, so this refactor keeps the behaviour but
moves it into its own file. This makes the main content builder much shorter.
"""

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QSizePolicy, QWidget


class AutoSectionLayout(QWidget):
    """
    Position sections in one or two columns depending on available width.

    The widget sets child geometry manually because the sections have dynamic
    heights when they expand and collapse.
    """

    def __init__(self, sections: list, threshold: int = 520, parent=None):
        super().__init__(parent)
        self._sections = sections
        self._threshold = threshold
        self._reflowing = False
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        for section in sections:
            section.setParent(self)
            section.show()
            section.changed.connect(self._on_section_changed)

    def _on_section_changed(self) -> None:
        QTimer.singleShot(0, self._reflow)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._reflowing:
            self._reflow()

    @staticmethod
    def _section_height(section) -> int:
        size_hint = section.sizeHint()
        height = size_hint.height()
        if height < 0:
            height = section.minimumSizeHint().height()
        return max(height, 22)

    def _reflow(self) -> None:
        if self._reflowing:
            return

        self._reflowing = True
        try:
            available_width = max(self.width(), 40)
            column_gap = 12
            row_gap = 4

            if available_width >= self._threshold and len(self._sections) > 1:
                column_width = (available_width - column_gap) // 2
                midpoint = (len(self._sections) + 1) // 2
                left_sections = self._sections[:midpoint]
                right_sections = self._sections[midpoint:]

                left_y = right_y = 0
                for section in left_sections:
                    height = self._section_height(section)
                    section.setGeometry(0, left_y, column_width, height)
                    left_y += height + row_gap

                for section in right_sections:
                    height = self._section_height(section)
                    section.setGeometry(column_width + column_gap, right_y, column_width, height)
                    right_y += height + row_gap

                total_height = max(left_y, right_y)
            else:
                current_y = 0
                for section in self._sections:
                    height = self._section_height(section)
                    section.setGeometry(0, current_y, available_width, height)
                    current_y += height + row_gap
                total_height = current_y

            new_height = max(total_height, 4)
            if self.height() != new_height:
                self.setFixedHeight(new_height)
            self.updateGeometry()
        finally:
            self._reflowing = False
