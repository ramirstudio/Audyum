"""Divisione del video in finestre sovrapposte e ricucitura dell'audio generato."""

from __future__ import annotations

import math

import numpy as np


def plan_windows(duration: float, window: int = 8, overlap: int = 1) -> list[tuple[float, float]]:
    """Restituisce (inizio, durata) in secondi.

    Gli inizi cadono su secondi interi: a 8 e 25 fps (le frequenze di MMAudio) un secondo intero
    corrisponde a un indice esatto di fotogramma in entrambi gli stream. Le finestre sono distribuite
    in modo uniforme e l'ultima finisce a fine video: nessun frammento corto in coda, e ogni coppia
    vicina si sovrappone di almeno `overlap` secondi.
    """
    if window <= overlap:
        raise ValueError("La finestra deve essere più lunga della sovrapposizione.")
    if duration <= 0:
        return []
    if duration <= window:
        return [(0.0, duration)]
    last = math.ceil(duration - window)
    gaps = math.ceil((duration - window) / (window - overlap))
    starts = [math.floor(i * last / gaps) for i in range(gaps)] + [last]
    return [(float(s), float(min(window, duration - s))) for s in starts]


def _rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(x, dtype=np.float64)))) if x.size else 0.0


def stitch(segments: list[tuple[float, np.ndarray]], sample_rate: int, total: float) -> np.ndarray:
    """Unisce segmenti (inizio_s, audio[canali, campioni]) con dissolvenza a potenza costante.

    Nella zona sovrapposta entrambi i segmenti descrivono le stesse immagini, quindi il volume
    del nuovo segmento viene allineato al precedente (entro ±6 dB) prima della dissolvenza.
    """
    channels = segments[0][1].shape[0]
    n_total = int(round(total * sample_rate))
    out = np.zeros((channels, n_total), dtype=np.float32)
    written = 0
    for start_s, audio in segments:
        s0 = int(round(start_s * sample_rate))
        if s0 >= n_total:
            break
        seg = audio[:, : n_total - s0].astype(np.float32, copy=True)
        n = seg.shape[1]
        ov = min(max(0, written - s0), n)
        if ov > 0:
            prev, new = out[:, s0 : s0 + ov], seg[:, :ov]
            rp, rn = _rms(prev), _rms(new)
            if rp > 1e-4 and rn > 1e-4:
                seg *= np.clip(rp / rn, 0.5, 2.0)
            theta = np.linspace(0.0, np.pi / 2, ov, dtype=np.float32)
            out[:, s0 : s0 + ov] = prev * np.cos(theta) + seg[:, :ov] * np.sin(theta)
        out[:, s0 + ov : s0 + n] = seg[:, ov:]
        written = max(written, s0 + n)
    return out


def finalize(audio: np.ndarray, sample_rate: int, normalize: bool = True, peak_db: float = -1.0) -> np.ndarray:
    """Brevi fade agli estremi contro i click e picco a -1 dBFS (o solo protezione dal clipping)."""
    audio = audio.copy()
    n = audio.shape[1]
    fi, fo = min(n, int(0.01 * sample_rate)), min(n, int(0.03 * sample_rate))
    if fi:
        audio[:, :fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)
    if fo:
        audio[:, n - fo :] *= np.linspace(1.0, 0.0, fo, dtype=np.float32)
    peak = float(np.max(np.abs(audio))) if n else 0.0
    target = 10 ** (peak_db / 20)
    if peak > 1e-6 and (normalize or peak > target):
        audio *= target / peak
    return audio


def fit_length(audio: np.ndarray, sample_rate: int, duration: float) -> np.ndarray:
    """Taglia o allunga con silenzio fino alla durata esatta del video."""
    n = int(round(duration * sample_rate))
    if audio.shape[1] >= n:
        return audio[:, :n]
    return np.pad(audio, ((0, 0), (0, n - audio.shape[1])))
