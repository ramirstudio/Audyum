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

    Con pythonw.exe stdout e stderr sono None: tqdm e alcuni print delle librerie
    andrebbero in errore, perciò li mandiamo su un file di log.
    """
    os.environ.setdefault("HF_HOME", str(hf_home()))
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

    # Il lettore video decodifica sulla CPU: la GPU resta al modello e, a VRAM quasi piena, il decoder
    # hardware di Windows può bloccarsi. Qt ignora (con un avviso nel log) il valore "none" e usa una lista vuota.
    os.environ.setdefault("QT_FFMPEG_DECODING_HW_DEVICE_TYPES", "none")

    logs_dir().mkdir(parents=True, exist_ok=True)
    log_file = logs_dir() / "audyum.log"
    _rotate(log_file)
    handlers: list[logging.Handler] = [logging.FileHandler(log_file, encoding="utf-8")]
    if sys.stderr is not None:  # con pythonw non c'è la console: basta il file
        handlers.append(logging.StreamHandler(sys.stderr))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        handlers=handlers, force=True)
    for noisy in ("httpx", "httpcore", "urllib3", "PIL", "matplotlib"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    global _crash_log
    _crash_log = open(logs_dir() / "crash.log", "a", encoding="utf-8", buffering=1)  # noqa: SIM115 - resta aperto
    faulthandler.enable(_crash_log, all_threads=True)  # un crash nativo finisce qui con lo stack dei thread
    if sys.stdout is None:
        sys.stdout = _crash_log
    if sys.stderr is None:
        sys.stderr = _crash_log


def _rotate(path: Path, keep_bytes: int = 2_000_000) -> None:
    """Il log non cresce senza limite: oltre 2 MB si tiene l'ultima copia precedente."""
    try:
        if path.exists() and path.stat().st_size > keep_bytes:
            old = path.with_suffix(".old.log")
            old.unlink(missing_ok=True)
            path.replace(old)
    except OSError:
        pass
