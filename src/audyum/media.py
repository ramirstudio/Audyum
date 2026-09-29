"""Lettura del video, campionamento dei fotogrammi per il modello e scrittura dell'audio (PyAV)."""

from __future__ import annotations

import dataclasses
import threading
from fractions import Fraction
from pathlib import Path
from typing import Callable, Literal, Optional

import av
import numpy as np

# Codec video che possono stare in un .mp4 senza ricodifica; per gli altri si usa .mkv.
_MP4_VIDEO_CODECS = {"h264", "hevc", "av1", "mpeg4", "vp9"}


class Cancelled(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class FrameSpec:
    """Come un motore vuole i fotogrammi: frequenza, lato in pixel e tipo di ridimensionamento."""

    fps: float
    size: int
    mode: Literal["squash", "crop"]  # squash: size x size deformando; crop: lato corto a size e ritaglio centrale


@dataclasses.dataclass(frozen=True)
class VideoInfo:
    path: Path
    duration: float
    fps: float
    width: int
    height: int
    codec: str
    has_audio: bool


@dataclasses.dataclass
class SampledVideo:
    streams: list[np.ndarray]  # uno per FrameSpec, uint8 (N, size, size, 3)
    specs: list[FrameSpec]
    duration: float  # durata coperta da tutti gli stream campionati
    video_duration: float  # dal primo all'ultimo fotogramma decodificato, più un fotogramma
    start_time: float  # tempo del primo fotogramma nel file, per allineare l'audio in uscita

    def window(self, start: float, duration: float) -> list[np.ndarray]:
        out = []
        for arr, spec in zip(self.streams, self.specs):
            i0 = int(round(start * spec.fps))
            out.append(arr[i0 : i0 + int(spec.fps * duration)])
        return out


def probe(path: Path | str) -> VideoInfo:
    path = Path(path)
    with av.open(str(path)) as c:
        if not c.streams.video:
            raise ValueError("Il file non contiene una traccia video.")
        s = c.streams.video[0]
        fps = float(s.guessed_rate or s.average_rate or 25)
        if s.duration is not None and s.time_base is not None:
            duration = float(s.duration * s.time_base)
        elif c.duration is not None:
            duration = c.duration / av.time_base
        else:
            duration = float(s.frames / fps) if s.frames else 0.0
        return VideoInfo(
            path=path,
            duration=duration,
            fps=fps,
            width=s.codec_context.width,
            height=s.codec_context.height,
            codec=s.codec_context.name,
            has_audio=bool(c.streams.audio),
        )


def _resize(frame: av.VideoFrame, spec: FrameSpec) -> np.ndarray:
    if spec.mode == "squash":
        return frame.reformat(width=spec.size, height=spec.size, format="rgb24", interpolation="BICUBIC").to_ndarray()
    w, h = frame.width, frame.height
    scale = spec.size / min(w, h)
    nw, nh = max(spec.size, round(w * scale)), max(spec.size, round(h * scale))
    img = frame.reformat(width=nw, height=nh, format="rgb24", interpolation="BICUBIC").to_ndarray()
    y0, x0 = (nh - spec.size) // 2, (nw - spec.size) // 2
    return np.ascontiguousarray(img[y0 : y0 + spec.size, x0 : x0 + spec.size])


def sample_frames(
    path: Path | str,
    specs: list[FrameSpec],
    progress: Optional[Callable[[float], None]] = None,
    cancel: Optional[threading.Event] = None,
) -> SampledVideo:
    """Decodifica il video una volta sola e campiona ogni FrameSpec alla sua frequenza.

    Per ogni istante k/fps prende il primo fotogramma con tempo >= k/fps, come fa MMAudio.
    """
    streams: list[list[np.ndarray]] = [[] for _ in specs]
    next_t = [0.0 for _ in specs]
    first_t: Optional[float] = None
    last_rel = 0.0
    with av.open(str(path)) as c:
        vs = c.streams.video[0]
        vs.thread_type = "AUTO"
        fps = float(vs.guessed_rate or vs.average_rate or 25)
        total = float(vs.duration * vs.time_base) if vs.duration and vs.time_base else None
        for frame in c.decode(vs):
            if cancel is not None and cancel.is_set():
                raise Cancelled()
            if frame.time is None:
                continue
            if first_t is None:
                first_t = frame.time
            rel = frame.time - first_t
            last_rel = max(last_rel, rel)
            for i, spec in enumerate(specs):
                img = None
                while rel >= next_t[i] - 1e-6:
                    if img is None:
                        img = _resize(frame, spec)
                    streams[i].append(img)
                    next_t[i] += 1.0 / spec.fps
            if progress is not None and total:
                progress(min(1.0, rel / total))
    if first_t is None:
        raise ValueError("Impossibile decodificare i fotogrammi del video.")
    arrays = [np.stack(s) for s in streams]
    duration = min(len(a) / spec.fps for a, spec in zip(arrays, specs))
    return SampledVideo(
        streams=arrays,
        specs=list(specs),
        duration=duration,
        video_duration=last_rel + 1.0 / fps,
        start_time=float(first_t),
    )


def _audio_frame(audio: np.ndarray, sample_rate: int) -> av.AudioFrame:
    audio = np.ascontiguousarray(audio, dtype=np.float32)
    layout = "mono" if audio.shape[0] == 1 else "stereo"
    frame = av.AudioFrame.from_ndarray(audio, format="fltp", layout=layout)
    frame.sample_rate = sample_rate
    frame.time_base = Fraction(1, sample_rate)
    frame.pts = 0
    return frame


def write_wav(path: Path | str, audio: np.ndarray, sample_rate: int) -> None:
    """audio: float32 (canali, campioni) in [-1, 1]. Scrive PCM 24 bit."""
    with av.open(str(path), "w", format="wav") as out:
        layout = "mono" if audio.shape[0] == 1 else "stereo"
        st = out.add_stream("pcm_s24le", rate=sample_rate, layout=layout)
        for p in st.encode(_audio_frame(audio, sample_rate)):
            out.mux(p)
        for p in st.encode(None):
            out.mux(p)


def output_suffix(video: Path | str) -> str:
    with av.open(str(video)) as c:
        codec = c.streams.video[0].codec_context.name
    return ".mp4" if codec in _MP4_VIDEO_CODECS else ".mkv"


def mux_audio(video: Path | str, audio: np.ndarray, sample_rate: int, out_path: Path | str, offset: float = 0.0) -> None:
    """Copia la traccia video senza ricodificarla e aggiunge l'audio in AAC.

    Un'eventuale traccia audio presente nel file originale viene scartata.
    offset: istante del primo fotogramma, così l'audio parte insieme all'immagine.
    """
    with av.open(str(video)) as inp, av.open(str(out_path), "w") as out:
        vin = inp.streams.video[0]
        vout = out.add_stream_from_template(vin)
        layout = "mono" if audio.shape[0] == 1 else "stereo"
        aout = out.add_stream("aac", rate=sample_rate, layout=layout)
        aout.bit_rate = 192_000 if layout == "mono" else 320_000

        frame = _audio_frame(audio, sample_rate)
        frame.pts = int(round(offset * sample_rate))
        packets = list(aout.encode(frame)) + list(aout.encode(None))

        # Intercalare a mano audio e video: scrivere prima tutto il video
        # costringerebbe il muxer a bufferizzare l'intero file.
        ai = 0
        for packet in inp.demux(vin):
            if packet.dts is None:
                continue
            t = float(packet.dts * packet.time_base)
            while ai < len(packets) and float(packets[ai].dts * packets[ai].time_base) <= t:
                out.mux(packets[ai])
                ai += 1
            packet.stream = vout
            out.mux(packet)
        for p in packets[ai:]:
            out.mux(p)
