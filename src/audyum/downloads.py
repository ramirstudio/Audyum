"""Download dei pesi con avanzamento in byte, ripresa dei download interrotti e annullamento.

I file vengono scritti da qui come file normali nella cartella dei modelli e poi letti direttamente:
non si passa dalla cache di Hugging Face, i cui file (collegamenti simbolici e blob scritti dal client
xet) su alcuni PC Windows non si riescono più a riaprire (errori 22 e 448).
"""

from __future__ import annotations

import dataclasses
import hashlib
import logging
import os
import stat
import threading
from pathlib import Path
from typing import Callable, Optional

from audyum.media import Cancelled

log = logging.getLogger(__name__)

ProgressFn = Callable[[str, Optional[float]], None]


@dataclasses.dataclass(frozen=True)
class URLFile:
    url: str
    dest: Path
    label: str
    md5: Optional[str] = None  # se noto, il file scaricato viene verificato; altrimenti conta la dimensione


def _gb(n: float) -> str:
    return f"{n / 1e9:.2f} GB"


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def _stamp(item: URLFile) -> Path:
    return item.dest.with_name(item.dest.name + ".ok")


def _is_complete(item: URLFile) -> bool:
    dest, stamp = item.dest, _stamp(item)
    try:
        return dest.is_file() and stamp.read_text().strip() == f"{item.md5 or '-'} {dest.stat().st_size}"
    except OSError:
        return False


class NotEnoughSpace(RuntimeError):
    pass


def _check_space(dest: Path, needed: int) -> None:
    import shutil

    free = shutil.disk_usage(dest.parent).free
    if needed and free < needed + (1 << 29):  # il file più mezzo GB di margine
        raise NotEnoughSpace(
            f"Spazio insufficiente su {dest.anchor or dest.parent}: servono circa {_gb(needed)} "
            f"per {dest.name} e ne restano {_gb(free)}. Libera spazio e riprova: il download riparte da qui.")


def _attempt(item: URLFile, part: Path, progress: ProgressFn, cancel: Optional[threading.Event]) -> int:
    """Un tentativo di download che riprende dal .part. Restituisce la dimensione totale attesa (0 se ignota)."""
    import requests

    done = part.stat().st_size if part.exists() else 0
    headers = {"Range": f"bytes={done}-"} if done else {}
    with requests.get(item.url, stream=True, headers=headers, timeout=(15, 60), allow_redirects=True) as r:
        if r.status_code == 416:  # il .part è già completo
            return done
        r.raise_for_status()
        if done and r.status_code != 206:  # il server ignora Range: si riparte da zero
            done = 0
        total = done + int(r.headers.get("content-length", 0))
        _check_space(item.dest, total - done)
        with open(part, "ab" if done else "wb") as f:
            for chunk in r.iter_content(1 << 20):
                if cancel is not None and cancel.is_set():
                    raise Cancelled()
                f.write(chunk)
                done += len(chunk)
                if total:
                    progress(f"Scarico {item.label}: {_gb(done)} di {_gb(total)}", done / total)
        return total


def fetch_url(item: URLFile, progress: ProgressFn, cancel: Optional[threading.Event] = None,
              retries: int = 8) -> Path:
    """Scarica (o riprende) il file e lo lascia in item.dest. Un file già completo non si riscarica.

    Un'interruzione di rete a metà (frequente con file da diversi GB) non fa perdere il lavoro fatto:
    si riprova fino a `retries` volte ripartendo da dove si era arrivati.
    """
    import requests

    dest = item.dest
    if _is_complete(item):
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    if item.md5 and dest.is_file() and _md5(dest) == item.md5:
        _stamp(item).write_text(f"{item.md5} {dest.stat().st_size}")
        return dest

    part = dest.with_name(dest.name + ".part")
    total = 0
    for attempt in range(1, retries + 1):
        try:
            total = _attempt(item, part, progress, cancel)
            break
        except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError) as e:
            if attempt == retries:
                raise
            wait = min(30, 2 ** attempt)
            log.warning("Download di %s interrotto (%s): tentativo %d di %d tra %d s", item.label, e, attempt,
                        retries, wait)
            progress(f"Connessione persa, riprovo tra {wait} s ({attempt} di {retries})", None)
            if cancel is not None and cancel.wait(wait):
                raise Cancelled() from e
    size = part.stat().st_size
    if total and size != total:
        raise RuntimeError(f"Download incompleto per {item.label} ({size} byte su {total}). Riprova.")
    if item.md5 and _md5(part) != item.md5:
        part.unlink(missing_ok=True)
        raise RuntimeError(f"Il file scaricato per {item.label} è corrotto. Riprova.")
    os.replace(part, dest)
    _stamp(item).write_text(f"{item.md5 or '-'} {dest.stat().st_size}")
    return dest


def describe_path(path: Path | str) -> str:
    """Testo diagnostico per il log: dimensione e attributi del file e di ogni cartella sopra, con i punti di
    reparse (collegamenti, giunzioni, segnaposto cloud) che Windows può rifiutare di attraversare."""
    lines = []
    p = Path(path)
    for cur in [p, *p.parents][:9]:
        try:
            st = os.lstat(cur)
            attrs = getattr(st, "st_file_attributes", 0)
            reparse = bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
            tag = getattr(st, "st_reparse_tag", 0)
            lines.append(f"{cur}: size={st.st_size} attrs={attrs:#x} reparse={reparse} tag={tag:#x}")
        except OSError as e:
            lines.append(f"{cur}: lstat non riuscito ({e})")
    return "\n".join(lines)


def remove_old_hf_cache(hub: Path) -> None:
    """Toglie la cache Hugging Face delle versioni precedenti (circa 9 GB), ora inutile."""
    import shutil

    if hub.exists():
        log.info("Rimuovo la vecchia cache Hugging Face: %s", hub)
        shutil.rmtree(hub, ignore_errors=True)
