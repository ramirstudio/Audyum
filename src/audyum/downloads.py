"""Download dei pesi con avanzamento in byte, ripresa dei download interrotti e annullamento."""

from __future__ import annotations

import dataclasses
import hashlib
import os
import shutil
import threading
from pathlib import Path
from typing import Callable, Optional

from audyum.media import Cancelled
from audyum.paths import hf_home

ProgressFn = Callable[[str, Optional[float]], None]


@dataclasses.dataclass(frozen=True)
class HFFile:
    """File su Hugging Face, scaricato nella cache standard (HF_HOME) dove lo cercano open_clip e BigVGAN."""

    repo_id: str
    filenames: tuple[str, ...]  # alternative in ordine di preferenza
    label: str


@dataclasses.dataclass(frozen=True)
class URLFile:
    url: str
    dest: Path
    md5: str
    label: str


def _gb(n: float) -> str:
    return f"{n / 1e9:.2f} GB"


def _tqdm_class(label: str, progress: ProgressFn, cancel: Optional[threading.Event]):
    from tqdm.std import tqdm

    class _Bar(tqdm):
        def __init__(self, *args, **kwargs):
            kwargs["disable"] = False
            kwargs["file"] = open(os.devnull, "w")
            super().__init__(*args, **kwargs)

        def update(self, n=1):
            if cancel is not None and cancel.is_set():
                raise Cancelled()
            ret = super().update(n)
            if self.total:
                progress(f"Scarico {label}: {_gb(self.n)} di {_gb(self.total)}", self.n / self.total)
            return ret

    return _Bar


def heal_hf_cache(hub: Path | None = None) -> int:
    """Sostituisce con file veri i collegamenti simbolici della cache Hugging Face.

    Alcuni PC Windows rifiutano di aprire i collegamenti (errore 22 o 448). Il file vero è un hardlink
    al blob già scaricato (nessun GB in più sul disco, nessun nuovo download); se l'hardlink non è
    possibile si copia. Restituisce quanti collegamenti sono stati sostituiti.
    """
    hub = hub or (hf_home() / "hub")
    fixed = 0
    for folder, _dirs, files in os.walk(hub):
        if os.sep + "snapshots" + os.sep not in folder + os.sep:
            continue
        for name in files:
            link = os.path.join(folder, name)
            if not os.path.islink(link):
                continue
            blob = os.path.normpath(os.path.join(folder, os.readlink(link)))
            if not os.path.isfile(blob):
                continue
            os.unlink(link)
            try:
                os.link(blob, link)
            except OSError:
                shutil.copy2(blob, link)
            fixed += 1
    return fixed


def fetch_hf(item: HFFile, progress: ProgressFn, cancel: Optional[threading.Event] = None) -> Path:
    from huggingface_hub import hf_hub_download
    from huggingface_hub.errors import EntryNotFoundError

    for i, name in enumerate(item.filenames):
        try:
            try:
                return Path(hf_hub_download(item.repo_id, name, local_files_only=True))
            except Exception:
                pass
            progress(f"Scarico {item.label}", None)
            path = Path(hf_hub_download(item.repo_id, name, tqdm_class=_tqdm_class(item.label, progress, cancel)))
            heal_hf_cache()
            return path
        except EntryNotFoundError:
            if i == len(item.filenames) - 1:
                raise
    raise FileNotFoundError(item.repo_id)


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_url(item: URLFile, progress: ProgressFn, cancel: Optional[threading.Event] = None) -> Path:
    import requests

    dest = item.dest
    stamp = dest.with_name(dest.name + ".ok")
    if dest.exists() and stamp.exists() and stamp.read_text().strip() == f"{item.md5} {dest.stat().st_size}":
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and _md5(dest) == item.md5:
        stamp.write_text(f"{item.md5} {dest.stat().st_size}")
        return dest

    part = dest.with_name(dest.name + ".part")
    done = part.stat().st_size if part.exists() else 0
    headers = {"Range": f"bytes={done}-"} if done else {}
    with requests.get(item.url, stream=True, headers=headers, timeout=60) as r:
        if r.status_code == 416:  # il .part è già completo
            r.close()
        else:
            r.raise_for_status()
            if done and r.status_code != 206:  # il server ignora Range: si riparte da zero
                done = 0
            total = done + int(r.headers.get("content-length", 0))
            with open(part, "ab" if done else "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    if cancel is not None and cancel.is_set():
                        raise Cancelled()
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        progress(f"Scarico {item.label}: {_gb(done)} di {_gb(total)}", done / total)
    if _md5(part) != item.md5:
        part.unlink(missing_ok=True)
        raise RuntimeError(f"Il file scaricato per {item.label} è corrotto. Riprova.")
    os.replace(part, dest)
    stamp.write_text(f"{item.md5} {dest.stat().st_size}")
    return dest


def fetch(item: HFFile | URLFile, progress: ProgressFn, cancel: Optional[threading.Event] = None) -> Path:
    if isinstance(item, HFFile):
        return fetch_hf(item, progress, cancel)
    return fetch_url(item, progress, cancel)
