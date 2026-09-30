"""Uso da riga di comando, utile per elaborare molti video in sequenza.

    audyum-cli video.mp4 --prompt "footsteps on gravel, wind" --variants 2
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from audyum.paths import configure_environment


def main(argv: list[str] | None = None) -> int:
    configure_environment()
    from audyum import engines
    from audyum.pipeline import JobSettings, run_job

    p = argparse.ArgumentParser(prog="audyum-cli", description="Genera l'audio per uno o più video muti.")
    p.add_argument("videos", nargs="+", type=Path)
    p.add_argument("-o", "--out", type=Path, help="cartella di uscita (predefinita: <cartella del video>/Audyum)")
    p.add_argument("--model", default=engines.DEFAULT_PRESET, choices=list(engines.PRESETS))
    p.add_argument("--prompt", default="", help="descrizione dei suoni, in inglese")
    p.add_argument("--negative", default="music, speech", help="suoni da evitare, in inglese")
    p.add_argument("--variants", type=int, default=1)
    p.add_argument("--seed", type=int)
    p.add_argument("--steps", type=int, default=40)
    p.add_argument("--guidance", type=float, default=4.5)
    p.add_argument("--window", type=int, default=8)
    p.add_argument("--overlap", type=int, default=1)
    p.add_argument("--no-normalize", action="store_true")
    p.add_argument("--fast", action="store_true", help="bfloat16: più veloce, audio meno pulito")
    a = p.parse_args(argv)

    engine = engines.create(a.model, full_precision=not a.fast)
    settings = JobSettings(a.prompt, a.negative, a.steps, a.guidance, a.variants, a.seed, a.window, a.overlap,
                           not a.no_normalize)

    def progress(msg: str, frac: float | None) -> None:
        pct = f" {frac * 100:5.1f}%" if frac is not None else ""
        sys.stderr.write(f"\r{msg[:90]:<90}{pct}")
        sys.stderr.flush()

    for video in a.videos:
        out_dir = a.out or video.parent / "Audyum"
        results = run_job(video, engine, settings, out_dir, progress)
        sys.stderr.write("\n")
        for r in results:
            print(r.video)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
