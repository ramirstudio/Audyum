"""Tema in stile iOS scuro: fondo nero, gruppi arrotondati, accento blu di sistema, interruttori."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

_HERE = Path(__file__).parent
_FONTS = _HERE / "fonts"
ICONS = _HERE / "icons"

C = {
    "bg": "#000000",
    "group": "#1C1C1E",
    "field": "#2C2C2E",
    "field_hover": "#3A3A3C",
    "sep": "#38383A",
    "text": "#FFFFFF",
    "secondary": "#8E8E93",
    "tertiary": "#48484A",
    "tint": "#0A84FF",
    "tint_pressed": "#0070E0",
    "icons": ICONS.as_posix(),
}

QSS = """
QWidget {{ background: {bg}; color: {text}; font-family: "Instrument Sans"; font-size: 10.5pt; }}
QLabel {{ background: transparent; }}
QLabel#wordmark {{ font-size: 26pt; font-weight: 700; }}
QLabel#section {{ color: {secondary}; font-size: 9.5pt; padding: 14px 0 2px 14px; }}
QLabel#muted, QCheckBox#muted {{ color: {secondary}; font-size: 9.5pt; }}
QLabel#footnote {{ color: {secondary}; font-size: 9pt; padding: 0 14px; }}
QLabel#rowLabel {{ font-size: 10.5pt; }}
QLabel#dropHint {{ color: {secondary}; font-size: 15pt; font-weight: 600; background: {group}; border-radius: 16px; }}

QFrame#group {{ background: {group}; border-radius: 12px; }}
QFrame#group QWidget {{ background: transparent; }}
QFrame#group QFrame#sep, QFrame#sep {{ background: {sep}; max-height: 1px; min-height: 1px; }}
QFrame#videoFrame {{ background: {group}; border-radius: 16px; }}

QPlainTextEdit, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {field}; border: none; border-radius: 9px; padding: 7px 10px;
    selection-background-color: {tint}; selection-color: {text};
}}
QFrame#group QPlainTextEdit, QFrame#group QLineEdit, QFrame#group QSpinBox,
QFrame#group QDoubleSpinBox, QFrame#group QComboBox {{ background: {field}; }}
QSpinBox:disabled, QDoubleSpinBox:disabled, QLineEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled {{
    color: {tertiary};
}}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{ width: 0; border: none; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ image: url({icons}/chevron_down.svg); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    background: {field}; border: none; border-radius: 10px; padding: 4px;
    selection-background-color: {field_hover}; outline: 0;
}}

QPushButton {{
    background: {field}; color: {tint}; border: none; border-radius: 10px;
    padding: 9px 14px; font-weight: 600;
}}
QPushButton:hover {{ background: {field_hover}; }}
QPushButton:disabled {{ color: {tertiary}; background: {group}; }}
QPushButton#primary {{
    background: {tint}; color: {text}; border-radius: 12px; padding: 13px 18px; font-size: 11pt;
}}
QPushButton#primary:hover {{ background: {tint_pressed}; }}
QPushButton#primary:disabled {{ background: {field}; color: {tertiary}; }}
QPushButton#plain {{ background: transparent; color: {tint}; padding: 9px 6px; }}
QPushButton#plain:hover {{ color: #409CFF; }}
QPushButton#plain:disabled {{ color: {tertiary}; }}
QPushButton#round {{ background: {field}; border-radius: 20px; padding: 0; }}
QPushButton#round:hover {{ background: {field_hover}; }}

QToolButton#disclosure {{ border: none; color: {tint}; padding: 10px 0 0 14px; font-weight: 600; background: transparent; }}

QCheckBox {{ spacing: 10px; background: transparent; }}
QCheckBox::indicator {{ width: 46px; height: 28px; }}
QCheckBox::indicator:unchecked {{ image: url({icons}/switch_off.svg); }}
QCheckBox::indicator:checked {{ image: url({icons}/switch_on.svg); }}
QCheckBox::indicator:checked:disabled {{ image: url({icons}/switch_on_disabled.svg); }}

QProgressBar {{ background: {field}; border: none; border-radius: 2px; max-height: 4px; }}
QProgressBar::chunk {{ background: {tint}; border-radius: 2px; }}

QSlider::groove:horizontal {{ height: 4px; background: {field_hover}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {text}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {text}; width: 18px; height: 18px; margin: -7px 0; border-radius: 9px; }}

QListWidget {{ background: transparent; border: none; outline: 0; }}
QListWidget::item {{ padding: 10px 6px; border-bottom: 1px solid {sep}; color: {text}; }}
QListWidget::item:selected {{ background: {field}; color: {tint}; border-radius: 8px; }}

QScrollArea {{ border: none; }}
QScrollBar:vertical {{ background: {bg}; width: 8px; }}
QScrollBar::handle:vertical {{ background: {field_hover}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
""".format(**C)


def apply(app: QApplication) -> None:
    for f in _FONTS.glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(f))
    app.setFont(QFont("Instrument Sans", 10))
    app.setStyleSheet(QSS)
