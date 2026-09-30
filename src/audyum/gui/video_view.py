"""Anteprima video con angoli arrotondati.

QVideoWidget è una finestra nativa e non si lascia ritagliare: qui i fotogrammi arrivano da un
QVideoSink e vengono disegnati a mano, adattati al riquadro e ritagliati con un rettangolo arrotondato.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen
from PySide6.QtMultimedia import QVideoFrame, QVideoSink
from PySide6.QtWidgets import QSizePolicy, QWidget


class VideoView(QWidget):
    def __init__(self, radius: float = 18.0, hint: str = ""):
        super().__init__()
        self.radius = radius
        self.hint = hint
        self.sink = QVideoSink(self)
        self.sink.videoFrameChanged.connect(self._on_frame)
        self._image: QImage | None = None
        self._frame: QVideoFrame | None = None  # ultimo fotogramma arrivato, convertito solo quando si disegna
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(320, 200)

    def _on_frame(self, frame: QVideoFrame) -> None:
        # Qt accorpa gli update(): se arrivano più fotogrammi prima di un ridisegno se ne converte uno solo.
        if frame.isValid():
            self._frame = frame
            self.update()

    def set_image(self, image: QImage | None) -> None:
        self._frame = None
        self._image = image
        self.update()

    def clear(self) -> None:
        self.set_image(None)

    def _target(self) -> QRectF:
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        if self._image is None or self._image.isNull():
            return r
        iw, ih = self._image.width(), self._image.height()
        scale = min(r.width() / iw, r.height() / ih)
        w, h = iw * scale, ih * scale
        return QRectF(r.x() + (r.width() - w) / 2, r.y() + (r.height() - h) / 2, w, h)

    def paintEvent(self, event) -> None:
        if self._frame is not None:
            try:
                img = self._frame.toImage()
                if not img.isNull():
                    self._image = img
            except Exception:  # noqa: BLE001 - un fotogramma illeggibile non deve chiudere l'app
                pass
            self._frame = None
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        target = self._target()
        path = QPainterPath()
        path.addRoundedRect(target, self.radius, self.radius)
        if self._image is None or self._image.isNull():
            p.fillPath(path, QColor(0, 0, 0, 70))
            p.setPen(QPen(QColor(255, 255, 255, 46), 1))
            p.drawPath(path)
            if self.hint:
                p.setPen(QColor("#B8ADC4"))
                p.setFont(QFont("Instrument Serif", 22))
                p.drawText(target, Qt.AlignCenter, self.hint)
        else:
            p.setClipPath(path)
            p.drawImage(target, self._image)
        p.end()
