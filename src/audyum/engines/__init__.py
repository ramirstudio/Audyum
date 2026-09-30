"""Registro dei motori. Per aggiungere un modello: sottoclasse di Engine e una voce in PRESETS."""

from __future__ import annotations

from typing import Callable

from audyum.engines.base import Engine, GenerationParams
from audyum.engines.mmaudio_engine import VARIANTS as _MMAUDIO_VARIANTS
from audyum.engines.mmaudio_engine import MMAudioEngine

PRESETS: dict[str, tuple[str, Callable[..., Engine]]] = {
    f"mmaudio:{v}": (label, (lambda v=v, **kw: MMAudioEngine(v, **kw))) for v, label in _MMAUDIO_VARIANTS.items()
}
DEFAULT_PRESET = "mmaudio:large_44k_v2"


def create(preset: str, **options) -> Engine:
    return PRESETS[preset][1](**options)


__all__ = ["Engine", "GenerationParams", "PRESETS", "DEFAULT_PRESET", "create"]
