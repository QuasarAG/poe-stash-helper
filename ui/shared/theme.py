"""Application-wide Qt style values.

Keeping the stylesheet in its own module makes the ownership obvious:
this file is about look and feel only, not behaviour.
"""

from __future__ import annotations

DARK_THEME_STYLESHEET = """
    QWidget              { background:#1a1a2e; color:#e0e0e0;
                           font-family:Segoe UI; font-size:12px; }
    QGroupBox            { border:1px solid #444; border-radius:6px;
                           margin-top:10px; padding-top:8px; color:#aaa; }
    QGroupBox::title     { subcontrol-origin:margin; left:10px; top:0px; }
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox
                         { background:#2a2a3e; border:1px solid #555;
                           border-radius:4px; padding:4px; color:#e0e0e0; }
    QPushButton          { background:#3a3a5e; border:1px solid #666;
                           border-radius:4px; padding:5px 12px; color:#e0e0e0; }
    QPushButton:hover    { background:#4a4a7e; }
    QPushButton:pressed  { background:#2a2a4e; }
    QPushButton#accent   { background:#445599; font-weight:bold; font-size:13px; }
    QPushButton#accent:hover { background:#5566bb; }
    QPushButton#danger   { background:#663333; }
    QPushButton#danger:hover { background:#884444; }
    QTableWidget         { background:#161626; gridline-color:#2a2a3e; }
    QHeaderView::section { background:#2a2a3e; padding:4px;
                           border:none; color:#bbb; }
    QTabBar::tab         { background:#2a2a3e; padding:6px 18px; }
    QTabBar::tab:selected{ background:#3a3a5e;
                           border-bottom:2px solid #7070ff; }
    QSplitter::handle    { background:#333; width:5px; }
    QProgressBar         { background:#2a2a3e; border-radius:4px; }
    QProgressBar::chunk  { background:#5555cc; border-radius:4px; }
"""
