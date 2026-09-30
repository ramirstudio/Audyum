"""Dal video muto ai file finali: pesi, fotogrammi, generazione a finestre, ricucitura, mux."""

from __future__ import annotations

import dataclasses
import random
import threading
from pathlib import Path
from typing import Optional

from audyum.downloads import ProgressFn
from audyum.engines.base import Engine, GenerationParams
from audyum.media import mux_audio, output_suffix, sample_frames, write_wav
from audyum.timeline import finalize, fit_length, plan_windows, stitch


@dataclasses.dataclass
class JobSettings:
    prompt: str = ""
    negative_prompt: str = ""
    steps: int = 40
    guidance: float = 4.5
    variants: int = 1
    seed: Optional[int] = None  # None: casuale
    window: int = 8
    overlap: int = 1
    normalize: bool = True


@dataclasses.dataclass(frozen=True)
class VariantResult:
    seed: int
    video: Path
    wav: Path


def _window_seed(seed: int, index: int) -> int:
    return (seed * 1_000_003 + index) % (2**63)


def run_job(
    video: Path | str,
    engine: Engine,
    settings: JobSettings,
    out_dir: Path | str,
    progress: ProgressFn,
    cancel: Optional[threading.Event] = None,
) -> list[VariantResult]:
    video, out_dir = Path(video), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    progress("Controllo i pesi del modello", None)
    engine.ensure_weights(progress, cancel)
    if not engine.loaded:
        engine.load(progress)

    sampled = sample_frames(video, engine.frame_specs, lambda f: progress("Leggo il video", f), cancel)
    windows = plan_windows(sampled.duration, min(settings.window, engine.max_window), settings.overlap)
    base = settings.seed if settings.seed is not None else random.randrange(1, 2**31)
    seeds = [base + i for i in range(settings.variants)]
    params = GenerationParams(settings.prompt, settings.negative_prompt, settings.steps, settings.guidance)

    segments: list[list] = [[] for _ in seeds]
    for wi, (start, dur) in enumerate(windows):
        label = f"Genero l'audio, finestra {wi + 1} di {len(windows)}"
        progress(label, wi / len(windows))
        audios = engine.generate(
            sampled.window(start, dur),
            dur,
            params,
            [_window_seed(s, wi) for s in seeds],
            lambda f, wi=wi, label=label: progress(label, (wi + f) / len(windows)),
            cancel,
        )
        for v, audio in enumerate(audios):
            segments[v].append((start, audio))

    sr = engine.sample_rate
    suffix = output_suffix(video)
    results = []
    for v, seed in enumerate(seeds):
        progress("Scrivo i file", v / len(seeds))
        track = finalize(stitch(segments[v], sr, sampled.duration), sr, settings.normalize)
        track = fit_length(track, sr, sampled.video_duration)
        name = f"{video.stem}_audyum_{seed}"
        wav, out_video = out_dir / f"{name}.wav", out_dir / f"{name}{suffix}"
        write_wav(wav, track, sr)
        mux_audio(video, track, sr, out_video, offset=sampled.start_time)
        results.append(VariantResult(seed, out_video, wav))
    progress("Fatto", 1.0)
    return results
