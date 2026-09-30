"""Cartelle dell'applicazione e variabili d'ambiente da impostare prima di importare torch/HF."""

from __future__ import annotations

import faulthandler
import logging
import os
import sys
from pathlib import Path


_crash_log = None


def install_root() -> Path:
    return Path(__file__).resolve().parents[2]


def app_home() -> Path:
    if os.environ.get("AUDYUM_HOME"):
        return Path(os.environ["AUDYUM_HOME"])
    # Installata con l'installer: modelli e log stanno nella cartella scelta, non su C:.
    if (install_root() / "portable.txt").exists():
        return install_root() / "data"
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
    # Su alcuni PC Windows i collegamenti simbolici non si possono aprire (errore 22/448): file veri.
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")  # download classico: file scritti in modo normale
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    # Il lettore video decodifica sulla CPU: la GPU resta al modello e, a VRAM quasi piena, il
    # decoder hardware di Windows si blocca o fa chiudere l'app. "none" non è un tipo valido: nessun decoder GPU.
    os.environ.setdefault("QT_FFMPEG_DECODING_HW_DEVICE_TYPES", "none")

    logs_dir().mkdir(parents=True, exist_ok=True)
    log_file = logs_dir() / "audyum.log"
    # Un crash nativo (Qt, driver, CUDA) finisce nel log con lo stack di ogni thread.
    global _crash_log
    _crash_log = open(logs_dir() / "crash.log", "a", encoding="utf-8", buffering=1)
    faulthandler.enable(_crash_log, all_threads=True)
    if sys.stdout is None or sys.stderr is None:
        stream = open(log_file, "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stdout or stream
        sys.stderr = sys.stderr or stream
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler(sys.stderr)],
    )
