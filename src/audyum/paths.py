"""Cartelle dell'applicazione e variabili d'ambiente da impostare prima di importare torch/HF."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path


def app_home() -> Path:
    if os.environ.get("AUDYUM_HOME"):
        return Path(os.environ["AUDYUM_HOME"])
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "Audyum"
    return Path.home() / ".local" / "share" / "Audyum"


def models_dir() -> Path:
    return app_home() / "models"


def hf_home() -> Path:
    return models_dir() / "hf"


def logs_dir() -> Path:
    return app_home() / "logs"


def configure_environment() -> None:
    """Da chiamare per prima cosa in ogni entry point.

    huggingface_hub legge HF_HOME solo al momento dell'import, quindi va impostata prima.
    Con pythonw.exe stdout e stderr sono None: tqdm e alcuni print delle librerie
    andrebbero in errore, perciò li mandiamo su un file di log.
    """
    os.environ.setdefault("HF_HOME", str(hf_home()))
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    logs_dir().mkdir(parents=True, exist_ok=True)
    log_file = logs_dir() / "audyum.log"
    if sys.stdout is None or sys.stderr is None:
        stream = open(log_file, "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stdout or stream
        sys.stderr = sys.stderr or stream
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler(sys.stderr)],
    )
