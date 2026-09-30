"""Tema scuro sfumato: fondo con bagliore caldo, campi e pulsanti a pillola con bordo sottile,
pulsante principale sfumato. Titolo in Instrument Serif, testo in Instrument Sans."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

_HERE = Path(__file__).parent
_FONTS = _HERE / "fonts"
ICONS = _HERE / "icons"

C = {
    "base": "#0B0612",
    "text": "#F4EEF6",
    "secondary": "#B8ADC4",
    "tertiary": "#6E6377",
    "line": "rgba(255, 255, 255, 46)",
    "line_hover": "rgba(255, 255, 255, 110)",
    "fill": "rgba(255, 255, 255, 14)",
    "fill_hover": "rgba(255, 255, 255, 26)",
    "peach": "#F2A68C",
    "coral": "#EE8A6C",
    "rose": "#D9577A",
    "popup": "#2A2036",
    "icons": ICONS.as_posix(),
}

QSS = """
QWidget {{ background: transparent; color: {text}; font-family: "Instrument Sans"; font-size: 10.5pt; }}
QMainWindow, QDialog, QMessageBox, QFileDialog, QMenu, QToolTip {{ background: {base}; }}

QLabel#wordmark {{ font-family: "Instrument Serif"; font-size: 44pt; color: {peach}; }}
QLabel#section {{ font-size: 11pt; font-weight: 700; padding-top: 18px; }}
QLabel#muted, QLabel#footnote {{ color: {secondary}; font-size: 9.5pt; }}
QLabel#rowLabel {{ font-size: 10.5pt; }}
QLabel#dropHint {{ color: {secondary}; font-family: "Instrument Serif"; font-size: 22pt; }}

QFrame#videoFrame {{ background: rgba(0, 0, 0, 70); border: 1px solid {line}; border-radius: 16px; }}
QFrame#group {{ background: transparent; border: none; }}
QFrame#sep {{ background: transparent; max-height: 0px; min-height: 0px; }}

QPlainTextEdit, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {fill}; border: 1px solid {line}; border-radius: 18px; padding: 8px 16px;
    selection-background-color: {coral}; selection-color: {base};
}}
QPlainTextEdit {{ border-radius: 18px; padding: 10px 14px; }}
QPlainTextEdit:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1px solid {coral};
}}
QSpinBox:disabled, QDoubleSpinBox:disabled, QLineEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled {{
    color: {tertiary};
}}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{ width: 0; border: none; }}
QComboBox::drop-down {{ border: none; width: 34px; }}
QComboBox::down-arrow {{ image: url({icons}/chevron_down.svg); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    background: {popup}; border: 1px solid {line}; border-radius: 12px; padding: 4px; outline: 0;
    selection-background-color: {fill_hover};
}}

QPushButton {{
    background: transparent; color: {text}; border: 1px solid {line}; border-radius: 18px;
    padding: 9px 18px;
}}
QPushButton:hover {{ border-color: {line_hover}; background: {fill}; }}
QPushButton:disabled {{ color: {tertiary}; border-color: rgba(255, 255, 255, 20); }}
QPushButton#primary {{
    border: none; border-radius: 22px; padding: 13px 18px; font-weight: 700; font-size: 11pt; color: #FFFFFF;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {coral}, stop:1 {rose});
}}
QPushButton#primary:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F39A7E, stop:1 #E0668A);
}}
QPushButton#primary:disabled {{ background: {fill}; color: {tertiary}; }}
QPushButton#plain {{ border: none; color: {secondary}; padding: 8px 4px; }}
QPushButton#plain:hover {{ color: {text}; background: transparent; }}
QPushButton#plain:disabled {{ color: {tertiary}; }}
QPushButton#round {{ background: {fill_hover}; border: none; border-radius: 22px; padding: 0; }}
QPushButton#round:hover {{ background: rgba(255, 255, 255, 40); }}

QToolButton#disclosure {{ border: none; color: {secondary}; padding: 12px 0 0 0; background: transparent; }}
QToolButton#disclosure:hover {{ color: {text}; }}

QCheckBox {{ spacing: 10px; }}
QCheckBox::indicator {{ width: 42px; height: 24px; }}
QCheckBox::indicator:unchecked {{ image: url({icons}/switch_off.svg); }}
QCheckBox::indicator:checked {{ image: url({icons}/switch_on.svg); }}
QCheckBox::indicator:checked:disabled {{ image: url({icons}/switch_on_disabled.svg); }}

QProgressBar {{ background: rgba(255, 255, 255, 26); border: none; border-radius: 2px; max-height: 4px; }}
QProgressBar::chunk {{
    border-radius: 2px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {coral}, stop:1 {rose});
}}

QSlider::groove:horizontal {{ height: 3px; background: rgba(255, 255, 255, 40); border-radius: 1px; }}
QSlider::sub-page:horizontal {{ background: {coral}; border-radius: 1px; }}
QSlider::handle:horizontal {{ background: {coral}; width: 12px; height: 12px; margin: -5px 0; border-radius: 6px; }}

QListWidget {{ border: 1px solid {line}; border-radius: 14px; padding: 6px; outline: 0; }}
QListWidget::item {{ padding: 9px 10px; border-radius: 8px; color: {text}; }}
QListWidget::item:selected {{ background: {fill_hover}; color: {text}; }}
QListWidget::item:hover {{ background: {fill}; }}

QScrollArea {{ border: none; }}
QScrollBar:vertical {{ background: transparent; width: 8px; }}
QScrollBar::handle:vertical {{ background: rgba(255, 255, 255, 40); border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
""".format(**C)


class GradientRoot(QWidget):
    """Fondo della finestra: la sfumatura del riferimento (background.png), stirata sulla finestra."""

    def __init__(self):
        super().__init__()
        self.setObjectName("root")
        self._bg = QPixmap(str(_HERE / "background.png"))

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawPixmap(self.rect(), self._bg)
        p.end()


def apply(app: QApplication) -> None:
    for f in _FONTS.glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(f))
    app.setFont(QFont("Instrument Sans", 10))
    app.setStyleSheet(QSS)
