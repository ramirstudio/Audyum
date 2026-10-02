from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import av
import numpy as np
import pytest

from audyum.engines.base import Engine
from audyum.media import FrameSpec


def make_video(path: Path, seconds: float, fps: int = 25, codec: str = "mpeg4", size=(96, 64)) -> Path:
    with av.open(str(path), "w") as out:
        st = out.add_stream(codec, rate=Fraction(fps))
        st.width, st.height, st.pix_fmt = size[0], size[1], "yuv420p"
        for i in range(int(round(seconds * fps))):
            img = np.full((size[1], size[0], 3), (i * 7) % 255, dtype=np.uint8)
            for p in st.encode(av.VideoFrame.from_ndarray(img, format="rgb24")):
                out.mux(p)
        for p in st.encode(None):
            out.mux(p)
    return path


def make_asym_video(path: Path, seconds: float = 2.0, fps: int = 25, size=(96, 64)) -> Path:
    """Metà sinistra rossa, metà destra blu, riquadro verde in alto a sinistra: l'orientamento si riconosce."""
    w, h = size
    img = np.zeros((h, w, 3), np.uint8)
    img[:, : w // 2] = (230, 20, 20)
    img[:, w // 2 :] = (20, 20, 230)
    img[: h // 4, : w // 2] = (20, 230, 20)
    with av.open(str(path), "w") as out:
        st = out.add_stream("mpeg4", rate=Fraction(fps))
        st.width, st.height, st.pix_fmt = w, h, "yuv420p"
        for _ in range(int(seconds * fps)):
            for p in st.encode(av.VideoFrame.from_ndarray(img, format="rgb24")):
                out.mux(p)
        for p in st.encode(None):
            out.mux(p)
    return path


def set_mp4_rotation(path: Path, degrees: int) -> None:
    """Sostituisce la matrice identità del contenitore mp4 con una rotazione (come fanno i telefoni)."""
    import math
    import struct

    fix = lambda v: struct.pack(">i", int(round(v * 65536)))  # noqa: E731
    ident = b"".join(fix(v) for v in (1, 0, 0, 0, 1, 0, 0, 0)) + struct.pack(">i", 0x40000000)
    a = math.radians(degrees)
    rot = b"".join(fix(v) for v in (math.cos(a), -math.sin(a), 0, math.sin(a), math.cos(a), 0, 0, 0)) \
        + struct.pack(">i", 0x40000000)
    data = path.read_bytes()
    i = data.rfind(ident)  # la matrice della traccia (tkhd) segue quella del filmato (mvhd): ffmpeg le compone
    assert i > 0
    path.write_bytes(data[:i] + rot + data[i + len(ident):])


class ToneEngine(Engine):
    """Motore finto: un tono diverso per ogni seme, lungo esattamente quanto la finestra."""

    id = "test:tone"
    label = "tono di prova"
    sample_rate = 16000
    frame_specs = [FrameSpec(8.0, 32, "squash"), FrameSpec(25.0, 24, "crop")]

    def __init__(self):
        self._loaded = False
        self.calls: list[tuple[int, int, float]] = []

    @property
    def loaded(self):
        return self._loaded

    def ensure_weights(self, progress, cancel=None):
        pass

    def load(self, progress):
        self._loaded = True

    def generate(self, frames, duration, params, seeds, on_progress=None, cancel=None):
        self.calls.append((len(frames[0]), len(frames[1]), duration))
        n = int(round(duration * self.sample_rate))
        t = np.arange(n) / self.sample_rate
        return [(0.3 * np.sin(2 * np.pi * (200 + s % 300) * t)).astype(np.float32)[None] for s in seeds]


@pytest.fixture
def tone_engine():
    return ToneEngine()
