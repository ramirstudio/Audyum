"""Tema: antracite caldo, un solo accento ossido. Titoli in Instrument Serif, testo in Instrument Sans."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

_FONTS = Path(__file__).parent / "fonts"

C = {
    "bg": "#161412",
    "field": "#221f1b",
    "line": "#36302a",
    "text": "#ebe3d5",
    "muted": "#968c7d",
    "faint": "#5c544a",
    "accent": "#d65f38",
    "accent_hover": "#e3724c",
    "accent_text": "#180d08",
    "selected": "#3b2a21",
    "video": "#0d0c0b",
}

QSS = """
QWidget {{ background: {bg}; color: {text}; font-family: "Instrument Sans"; font-size: 10.5pt; }}
QLabel#wordmark {{ font-family: "Instrument Serif"; font-size: 32pt; }}
QLabel#section {{ font-family: "Instrument Serif"; font-size: 17pt; padding-top: 14px; }}
QLabel#muted, QCheckBox#muted {{ color: {muted}; font-size: 9.5pt; }}
QLabel#dropHint {{ color: {muted}; font-family: "Instrument Serif"; font-size: 22pt; background: {video}; }}
QFrame#videoFrame {{ background: {video}; border: 1px solid {line}; }}
QPlainTextEdit, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QListWidget {{
    background: {field}; border: 1px solid {line}; border-radius: 3px; padding: 5px 7px;
    selection-background-color: {accent}; selection-color: {accent_text};
}}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{ width: 0; border: none; }}
QPlainTextEdit:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border-color: {accent}; }}
QComboBox QAbstractItemView {{ background: {field}; border: 1px solid {line}; selection-background-color: {selected}; }}
QListWidget::item {{ padding: 6px 4px; }}
QListWidget::item:selected {{ background: {selected}; color: {text}; }}
QPushButton {{ background: {field}; border: 1px solid {line}; border-radius: 3px; padding: 7px 14px; }}
QPushButton:hover {{ border-color: {muted}; }}
QPushButton:disabled {{ color: {faint}; border-color: {line}; }}
QPushButton#primary {{ background: {accent}; color: {accent_text}; border: none; font-weight: 600; padding: 10px 18px; }}
QPushButton#primary:hover {{ background: {accent_hover}; }}
QPushButton#primary:disabled {{ background: {line}; color: {faint}; }}
QToolButton#disclosure {{ border: none; color: {muted}; padding: 8px 0; text-align: left; }}
QToolButton#disclosure:hover {{ color: {text}; }}
QProgressBar {{ background: {field}; border: none; max-height: 4px; }}
QProgressBar::chunk {{ background: {accent}; }}
QSlider::groove:horizontal {{ height: 3px; background: {line}; }}
QSlider::sub-page:horizontal {{ background: {accent}; }}
QSlider::handle:horizontal {{ background: {text}; width: 11px; margin: -4px 0; border-radius: 5px; }}
QScrollArea {{ border: none; }}
QScrollBar:vertical {{ background: {bg}; width: 8px; }}
QScrollBar::handle:vertical {{ background: {line}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
""".format(**C)


def apply(app: QApplication) -> None:
    for f in _FONTS.glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(f))
    app.setFont(QFont("Instrument Sans", 10))
    app.setStyleSheet(QSS)
