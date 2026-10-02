"""Impostazioni dell'aspetto: sfondo (tema, sfumatura, tinta unita, immagine) e colore d'accento.

Nessuna dipendenza da Qt: si salvano in settings.json accanto ai dati dell'app e si possono testare da sole.
"""

from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path

from audyum.paths import app_home

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
BG_MODES = ("reference", "gradient", "solid", "image")
ACCENT_MODES = ("gradient", "solid")


def hex_to_rgb(c: str) -> tuple[int, int, int]:
    return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)


def rgb_to_hex(r: float, g: float, b: float) -> str:
    return "#" + "".join(f"{max(0, min(255, round(v))):02X}" for v in (r, g, b))


def mix(a: str, b: str, t: float) -> str:
    """t=0 restituisce a, t=1 restituisce b."""
    ra, rb = hex_to_rgb(a), hex_to_rgb(b)
    return rgb_to_hex(*(x + (y - x) * t for x, y in zip(ra, rb, strict=True)))


def lighten(c: str, t: float) -> str:
    return mix(c, "#FFFFFF", t)


def darken(c: str, t: float) -> str:
    return mix(c, "#000000", t)


@dataclasses.dataclass
class UISettings:
    preset: str = "tramonto"
    bg_mode: str = "reference"
    bg1: str = "#2A1838"
    bg2: str = "#0E0A14"
    bg_angle: int = 160
    glow: bool = True
    glow_color: str = "#D66E5A"
    bg_solid: str = "#140E1C"
    bg_image: str = ""
    accent_mode: str = "gradient"
    accent1: str = "#EE8A6C"
    accent2: str = "#D9577A"

    def accent_end(self) -> str:
        return self.accent2 if self.accent_mode == "gradient" else self.accent1

    def base(self) -> str:
        """Colore più scuro dello sfondo: serve a menu, finestre di dialogo e testo sopra l'accento."""
        if self.bg_mode == "solid":
            return self.bg_solid
        if self.bg_mode == "gradient":
            return self.bg2
        return "#0B0612"

    def validated(self) -> UISettings:
        d = dataclasses.asdict(self)
        ref = UISettings()
        for k, v in d.items():
            default = getattr(ref, k)
            if isinstance(default, bool):
                d[k] = bool(v)
            elif isinstance(default, int):
                d[k] = int(v) % 360 if k == "bg_angle" else int(v)
            elif k in ("bg1", "bg2", "glow_color", "bg_solid", "accent1", "accent2"):
                d[k] = v if isinstance(v, str) and _HEX.match(v) else default
            elif k == "bg_mode":
                d[k] = v if v in BG_MODES else default
            elif k == "accent_mode":
                d[k] = v if v in ACCENT_MODES else default
            else:
                d[k] = v if isinstance(v, str) else default
        if d["bg_mode"] == "image" and not Path(d["bg_image"]).is_file():
            d["bg_mode"] = "reference"
        return UISettings(**d)


PRESET_NAMES = {
    "tramonto": "Tramonto",
    "oceano": "Oceano",
    "bosco": "Bosco",
    "ambra": "Ambra",
    "grafite": "Grafite",
}

PRESETS: dict[str, UISettings] = {
    "tramonto": UISettings(),
    "oceano": UISettings(
        preset="oceano", bg_mode="gradient", bg1="#123C4A", bg2="#050B10", bg_angle=165,
        glow=True, glow_color="#2FA8A0", accent_mode="gradient", accent1="#4FD1C5", accent2="#3B8FD6"),
    "bosco": UISettings(
        preset="bosco", bg_mode="gradient", bg1="#1B3324", bg2="#070D09", bg_angle=170,
        glow=True, glow_color="#7A9A45", accent_mode="gradient", accent1="#B4D06E", accent2="#5FA36B"),
    "ambra": UISettings(
        preset="ambra", bg_mode="gradient", bg1="#3A2410", bg2="#0C0805", bg_angle=160,
        glow=True, glow_color="#E0952F", accent_mode="gradient", accent1="#F5BC5E", accent2="#E0742F"),
    "grafite": UISettings(
        preset="grafite", bg_mode="solid", bg_solid="#17171A", glow=False,
        accent_mode="solid", accent1="#E9E3D8", accent2="#E9E3D8"),
}


def settings_path() -> Path:
    return app_home() / "settings.json"


def load(path: Path | None = None) -> UISettings:
    path = path or settings_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        known = {f.name for f in dataclasses.fields(UISettings)}
        return UISettings(**{k: v for k, v in raw.items() if k in known}).validated()
    except (OSError, ValueError, TypeError):
        return UISettings()


def save(ui: UISettings, path: Path | None = None) -> None:
    path = path or settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(dataclasses.asdict(ui), indent=2), encoding="utf-8")
    except OSError:
        pass  # impostazioni non salvabili: l'app funziona lo stesso con quelle correnti
