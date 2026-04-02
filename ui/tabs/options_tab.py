from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore    import Qt
from ui.shared import make_scrollable

class OptionTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        content = QWidget()
        layout  = QVBoxLayout(content)
        placeholder = QLabel("Options — coming soon.")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color:#555; font-style:italic; padding:32px;")
        layout.addWidget(placeholder)
        layout.addStretch()
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(make_scrollable(content))