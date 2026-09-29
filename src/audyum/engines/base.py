from __future__ import annotations

import abc
import dataclasses
import threading
from typing import Callable, Optional

import numpy as np

from audyum.downloads import ProgressFn
from audyum.media import FrameSpec


@dataclasses.dataclass(frozen=True)
class GenerationParams:
    prompt: str = ""
    negative_prompt: str = ""
    steps: int = 25
    guidance: float = 4.5


class Engine(abc.ABC):
    """Un modello video-to-audio. Riceve fotogrammi già campionati secondo `frame_specs`."""

    id: str
    label: str
    sample_rate: int
    channels: int = 1
    frame_specs: list[FrameSpec]
    max_window: int = 8  # secondi per singola generazione
    license_note: str = ""

    @property
    @abc.abstractmethod
    def loaded(self) -> bool: ...

    @abc.abstractmethod
    def ensure_weights(self, progress: ProgressFn, cancel: Optional[threading.Event] = None) -> None: ...

    @abc.abstractmethod
    def load(self, progress: ProgressFn) -> None: ...

    @abc.abstractmethod
    def generate(
        self,
        frames: list[np.ndarray],
        duration: float,
        params: GenerationParams,
        seeds: list[int],
        on_progress: Optional[Callable[[float], None]] = None,
        cancel: Optional[threading.Event] = None,
    ) -> list[np.ndarray]:
        """Una traccia float32 (canali, campioni) per ogni seme."""

    def unload(self) -> None:
        pass
