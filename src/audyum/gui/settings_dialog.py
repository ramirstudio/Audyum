"""Finestra delle impostazioni: tema, sfondo (sfumatura, tinta unita, immagine) e colore d'accento.

Le modifiche si vedono subito sulla finestra principale e vengono salvate a ogni cambio.
"""

from __future__ import annotations

import dataclasses

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from audyum import ui_settings as us
from audyum.gui import theme

BG_LABELS = [
    ("reference", "Tema"),
    ("gradient", "Sfumatura personalizzata"),
    ("solid", "Tinta unita"),
    ("image", "Immagine"),
]
ACCENT_LABELS = [("gradient", "Sfumatura"), ("solid", "Tinta unita")]


class Swatch(QPushButton):
    """Pulsante tondo che mostra un colore e apre il selettore."""

    picked = Signal(str)

    def __init__(self, color: str):
        super().__init__()
        self.setFixedSize(64, 32)
        self.setCursor(Qt.PointingHandCursor)
        self.set_color(color)
        self.clicked.connect(self._choose)

    def set_color(self, color: str) -> None:
        self.color = color
        self.setStyleSheet(
            f"QPushButton {{ background: {color}; border: 1px solid rgba(255,255,255,90); border-radius: 16px; }}"
            f"QPushButton:hover {{ border: 1px solid rgba(255,255,255,200); }}")

    def _choose(self) -> None:
        c = QColorDialog.getColor(QColor(self.color), self, "Scegli il colore")
        if c.isValid():
            self.set_color(c.name().upper())
            self.picked.emit(self.color)


class SettingsDialog(QDialog):
    changed = Signal(object)

    def __init__(self, ui: us.UISettings, backdrop: theme.Backdrop, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Impostazioni")
        self.setMinimumWidth(500)
        self.ui = ui
        self.backdrop = backdrop
        self._building = True

        col = QVBoxLayout(self)
        col.setContentsMargins(32, 24, 32, 28)
        col.setSpacing(8)
        title = QLabel("Impostazioni")
        title.setObjectName("dlgTitle")
        col.addWidget(title)

        col.addWidget(self._section("Tema"))
        self.preset = QComboBox()
        for key, name in us.PRESET_NAMES.items():
            self.preset.addItem(name, key)
        self.preset.addItem("Personalizzato", "custom")
        self.preset.activated.connect(self._on_preset)
        col.addWidget(self.preset)

        col.addWidget(self._section("Sfondo"))
        self.bg_mode = QComboBox()
        for key, name in BG_LABELS:
            self.bg_mode.addItem(name, key)
        self.bg_mode.activated.connect(lambda _: self._edit(bg_mode=self.bg_mode.currentData()))
        col.addWidget(self.bg_mode)

        self.bg1 = Swatch(ui.bg1)
        self.bg2 = Swatch(ui.bg2)
        self.bg1.picked.connect(lambda c: self._edit(bg1=c))
        self.bg2.picked.connect(lambda c: self._edit(bg2=c))
        self.angle = QSlider(Qt.Horizontal)
        self.angle.setRange(0, 359)
        self.angle.valueChanged.connect(lambda v: self._edit(bg_angle=v))
        self.glow = QCheckBox()
        self.glow.toggled.connect(lambda on: self._edit(glow=on))
        self.glow_color = Swatch(ui.glow_color)
        self.glow_color.picked.connect(lambda c: self._edit(glow_color=c))
        self.solid = Swatch(ui.bg_solid)
        self.solid.picked.connect(lambda c: self._edit(bg_solid=c))
        self.image_btn = QPushButton("Scegli immagine…")
        self.image_btn.clicked.connect(self._choose_image)
        self.image_lbl = QLabel("")
        self.image_lbl.setObjectName("muted")

        self.row_grad_a = self._row("Colore in alto", self.bg1)
        self.row_grad_b = self._row("Colore in basso", self.bg2)
        self.row_angle = self._row("Direzione", self.angle)
        self.row_glow = self._row("Bagliore in basso a sinistra", self.glow)
        self.row_glow_color = self._row("Colore del bagliore", self.glow_color)
        self.row_solid = self._row("Colore", self.solid)
        self.row_image = self._row("Immagine", self.image_btn)
        for r in (self.row_grad_a, self.row_grad_b, self.row_angle, self.row_solid, self.row_image,
                  self.row_glow, self.row_glow_color):
            col.addWidget(r)
        col.addWidget(self.image_lbl)

        col.addWidget(self._section("Colore d'accento"))
        self.accent_mode = QComboBox()
        for key, name in ACCENT_LABELS:
            self.accent_mode.addItem(name, key)
        self.accent_mode.activated.connect(lambda _: self._edit(accent_mode=self.accent_mode.currentData()))
        col.addWidget(self.accent_mode)
        self.accent1 = Swatch(ui.accent1)
        self.accent2 = Swatch(ui.accent2)
        self.accent1.picked.connect(lambda c: self._edit(accent1=c))
        self.accent2.picked.connect(lambda c: self._edit(accent2=c))
        self.row_acc1 = self._row("Colore", self.accent1)
        self.row_acc2 = self._row("Secondo colore", self.accent2)
        col.addWidget(self.row_acc1)
        col.addWidget(self.row_acc2)
        col.addWidget(self._hint("L'accento colora il titolo, il pulsante Genera audio, le barre e i campi attivi."))

        col.addSpacing(16)
        buttons = QHBoxLayout()
        reset = QPushButton("Ripristina il tema iniziale")
        reset.setObjectName("plain")
        reset.clicked.connect(lambda: self._apply_all(us.PRESETS["tramonto"]))
        done = QPushButton("Fatto")
        done.setObjectName("primary")
        done.setMinimumWidth(140)
        done.clicked.connect(self.accept)
        buttons.addWidget(reset)
        buttons.addStretch(1)
        buttons.addWidget(done)
        col.addLayout(buttons)

        self._sync()

    # ---- costruzione ---------------------------------------------------------------------

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("section")
        return lbl

    def _hint(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("footnote")
        lbl.setWordWrap(True)
        return lbl

    def _row(self, label: str, widget: QWidget) -> QWidget:
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 2, 0, 2)
        text = QLabel(label)
        text.setObjectName("rowLabel")
        lay.addWidget(text, 1)
        lay.addWidget(widget)
        return box

    def paintEvent(self, event) -> None:
        self.backdrop.paint(self)

    # ---- logica --------------------------------------------------------------------------

    def _sync(self) -> None:
        """Riporta le impostazioni nei controlli e mostra solo le righe che servono."""
        self._building = True
        ui = self.ui
        self.preset.setCurrentIndex(self.preset.findData(ui.preset if ui.preset in us.PRESETS else "custom"))
        self.bg_mode.setCurrentIndex(self.bg_mode.findData(ui.bg_mode))
        self.accent_mode.setCurrentIndex(self.accent_mode.findData(ui.accent_mode))
        for sw, c in ((self.bg1, ui.bg1), (self.bg2, ui.bg2), (self.glow_color, ui.glow_color),
                      (self.solid, ui.bg_solid), (self.accent1, ui.accent1), (self.accent2, ui.accent2)):
            sw.set_color(c)
        self.angle.setValue(ui.bg_angle)
        self.glow.setChecked(ui.glow)
        self.image_lbl.setText(ui.bg_image if ui.bg_image else "")
        mode = ui.bg_mode
        self.row_grad_a.setVisible(mode == "gradient")
        self.row_grad_b.setVisible(mode == "gradient")
        self.row_angle.setVisible(mode == "gradient")
        self.row_solid.setVisible(mode == "solid")
        self.row_image.setVisible(mode == "image")
        self.image_lbl.setVisible(mode == "image" and bool(ui.bg_image))
        self.row_glow.setVisible(mode in ("gradient", "image"))
        self.row_glow_color.setVisible(mode in ("gradient", "image") and ui.glow)
        self.row_acc2.setVisible(ui.accent_mode == "gradient")
        self._building = False

    def _publish(self) -> None:
        self.ui = self.ui.validated()
        self._sync()
        self.changed.emit(self.ui)
        self.update()

    def _edit(self, **fields) -> None:
        if self._building:
            return
        self.ui = dataclasses.replace(self.ui, preset="custom", **fields)
        self._publish()

    def _on_preset(self, _index: int) -> None:
        key = self.preset.currentData()
        if key in us.PRESETS:
            self._apply_all(us.PRESETS[key])

    def _apply_all(self, ui: us.UISettings) -> None:
        self.ui = dataclasses.replace(ui)
        self._publish()

    def _choose_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Scegli l'immagine di sfondo", "",
                                              "Immagini (*.png *.jpg *.jpeg *.webp *.bmp)")
        if path:
            self._edit(bg_mode="image", bg_image=path)
