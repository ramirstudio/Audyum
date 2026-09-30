"""Tema scuro sfumato: fondo con bagliore caldo, campi e pulsanti a pillola con bordo sottile,
pulsante principale sfumato. Titolo in Instrument Serif, testo in Instrument Sans."""

from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QPointF, QRect, QRectF
from PySide6.QtGui import QColor, QFont, QFontDatabase, QLinearGradient, QPainter, QPixmap, QRadialGradient
from PySide6.QtWidgets import QApplication, QWidget

from audyum.ui_settings import UISettings, hex_to_rgb, lighten, mix

_HERE = Path(__file__).parent
_FONTS = _HERE / "fonts"
ICONS = _HERE / "icons"

C: dict[str, str] = {}


def luminance(c: str) -> float:
    r, g, b = (v / 255 for v in hex_to_rgb(c))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def palette(ui: UISettings) -> dict[str, str]:
    base = ui.base()
    return {
        "base": base,
        "text": "#F4EEF6",
        "secondary": "#B8ADC4",
        "tertiary": "#6E6377",
        "line": "rgba(255, 255, 255, 46)",
        "line_hover": "rgba(255, 255, 255, 110)",
        "fill": "rgba(255, 255, 255, 14)",
        "fill_hover": "rgba(255, 255, 255, 26)",
        "peach": lighten(ui.accent1, 0.25),
        "coral": ui.accent1,
        "rose": ui.accent_end(),
        "coral_hover": lighten(ui.accent1, 0.12),
        "rose_hover": lighten(ui.accent_end(), 0.12),
        "on_accent": "#FFFFFF" if luminance(mix(ui.accent1, ui.accent_end(), 0.5)) < 0.62 else "#1A1512",
        "popup": mix(base, "#FFFFFF", 0.10),
        "icons": ICONS.as_posix(),
    }


QSS_TEMPLATE = """
QWidget {{ background: transparent; color: {text}; font-family: "Instrument Sans"; font-size: 10.5pt; }}
QMainWindow, QDialog, QMessageBox, QFileDialog, QMenu, QToolTip {{ background: {base}; }}

QLabel#wordmark {{ font-family: "Instrument Serif"; font-size: 72pt; color: {peach}; }}
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
    border: none; border-radius: 22px; padding: 13px 18px; font-weight: 700; font-size: 11pt; color: {on_accent};
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {coral}, stop:1 {rose});
}}
QPushButton#primary:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {coral_hover}, stop:1 {rose_hover});
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
""" + """
QLabel#dlgTitle {{ font-family: "Instrument Serif"; font-size: 30pt; }}
"""


def make_qss(ui: UISettings) -> str:
    return QSS_TEMPLATE.format(**palette(ui))


def paint_backdrop(p: QPainter, rect: QRect, ui: UISettings, reference: QPixmap, image: QPixmap | None) -> None:
    """Disegna lo sfondo scelto: tema (immagine di riferimento), sfumatura, tinta unita o immagine."""
    w, h = rect.width(), rect.height()
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    if ui.bg_mode == "reference":
        p.drawPixmap(rect, reference)
    elif ui.bg_mode == "solid":
        p.fillRect(rect, QColor(ui.bg_solid))
    elif ui.bg_mode == "image" and image is not None and not image.isNull():
        scale = max(w / image.width(), h / image.height())
        iw, ih = image.width() * scale, image.height() * scale
        p.drawPixmap(QRectF(rect.x() + (w - iw) / 2, rect.y() + (h - ih) / 2, iw, ih), image, QRectF(image.rect()))
        p.fillRect(rect, QColor(0, 0, 0, 120))
    else:
        a = math.radians(ui.bg_angle)
        dx, dy = math.sin(a), math.cos(a)
        half = (abs(w * dx) + abs(h * dy)) / 2
        cx, cy = rect.x() + w / 2, rect.y() + h / 2
        grad = QLinearGradient(cx - dx * half, cy - dy * half, cx + dx * half, cy + dy * half)
        grad.setColorAt(0.0, QColor(ui.bg1))
        grad.setColorAt(1.0, QColor(ui.bg2))
        p.fillRect(rect, grad)
    if ui.glow and ui.bg_mode in ("gradient", "image"):
        c = QColor(ui.glow_color)
        radial = QRadialGradient(QPointF(rect.x() - w * 0.02, rect.y() + h * 1.05), w * 0.42)
        c.setAlpha(150)
        radial.setColorAt(0.0, c)
        c.setAlpha(55)
        radial.setColorAt(0.45, c)
        c.setAlpha(0)
        radial.setColorAt(1.0, c)
        p.fillRect(rect, radial)


class Backdrop:
    """Carica le immagini di sfondo una volta sola e le disegna su qualunque widget."""

    def __init__(self, ui: UISettings):
        self.reference = QPixmap(str(_HERE / "background.png"))
        self.image: QPixmap | None = None
        self.ui = ui
        self._cache: QPixmap | None = None
        self.set(ui)

    def set(self, ui: UISettings) -> None:
        if ui.bg_mode == "image" and (self.image is None or ui.bg_image != self.ui.bg_image or self.image.isNull()):
            self.image = QPixmap(ui.bg_image)
        self.ui = ui
        self._cache = None

    def paint(self, widget: QWidget, region: QRect | None = None) -> None:
        # Lo sfondo scalato si calcola una volta per dimensione della finestra; a ogni ridisegno
        # (per esempio a ogni fotogramma del video) si copia solo la parte da aggiornare.
        size = widget.size()
        if getattr(self, "_cache", None) is None or self._cache.size() != size:
            self._cache = QPixmap(size)
            cp = QPainter(self._cache)
            paint_backdrop(cp, self._cache.rect(), self.ui, self.reference, self.image)
            cp.end()
        p = QPainter(widget)
        r = region or widget.rect()
        p.drawPixmap(r, self._cache, r)
        p.end()


class GradientRoot(QWidget):
    """Fondo della finestra principale."""

    def __init__(self, backdrop: Backdrop):
        super().__init__()
        self.setObjectName("root")
        self.backdrop = backdrop

    def paintEvent(self, event) -> None:
        self.backdrop.paint(self, event.rect())


def apply(app: QApplication, ui: UISettings) -> None:
    for f in _FONTS.glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(f))
    app.setFont(QFont("Instrument Sans", 10))
    restyle(app, ui)


def restyle(app: QApplication, ui: UISettings) -> None:
    C.clear()
    C.update(palette(ui))
    app.setStyleSheet(make_qss(ui))
