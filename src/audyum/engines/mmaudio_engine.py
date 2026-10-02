"""MMAudio (Cheng et al., CVPR 2025): flow matching condizionato da CLIP (semantica) e Synchformer (sincronia).

Riprende mmaudio.eval_utils.generate separando l'estrazione delle feature dal campionamento:
con più varianti le feature di ogni finestra si calcolano una volta sola.
"""

from __future__ import annotations

import dataclasses
import logging
import threading
from unittest import mock
from typing import Callable, Optional

import numpy as np

from audyum.downloads import ProgressFn, URLFile, describe_path, fetch_url, remove_old_hf_cache
from audyum.engines.base import Engine, GenerationParams
from audyum.media import Cancelled, FrameSpec
from audyum.paths import hf_home, models_dir

_RELEASE = "https://github.com/hkchengrex/MMAudio/releases/download/v0.1/"
log = logging.getLogger(__name__)

_MD5 = {  # dalla tabella dei download ufficiali di MMAudio
    "large_44k_v2": "01ad4464f049b2d7efdaa4c1a59b8dfe",
    "medium_44k": "5a56b6665e45a1e65ada534defa903d0",
    "small_44k": "babd74c884783d13701ea2820a5f5b6d",
}

VARIANTS = {
    "large_44k_v2": "MMAudio L v2 · qualità massima",
    "medium_44k": "MMAudio M · bilanciato",
    "small_44k": "MMAudio S · veloce",
}


class MMAudioEngine(Engine):
    sample_rate = 44100
    channels = 1
    frame_specs = [FrameSpec(8.0, 384, "squash"), FrameSpec(25.0, 224, "crop")]
    max_window = 8  # MMAudio è addestrato su clip di 8 secondi
    license_note = "Pesi MMAudio sotto licenza CC BY-NC 4.0: solo uso non commerciale."

    def __init__(self, variant: str = "large_44k_v2", device: Optional[str] = None, full_precision: bool = True):
        if variant not in VARIANTS:
            raise ValueError(f"Variante MMAudio sconosciuta: {variant}")
        self.variant = variant
        self.id = f"mmaudio:{variant}"
        self.label = VARIANTS[variant]
        self._device = device
        self.full_precision = full_precision
        self._paths: dict[str, object] = {}
        self._net = None
        self._fu = None
        self._dtype = None
        self._decode_dtype = None

    @property
    def loaded(self) -> bool:
        return self._net is not None

    def _files(self) -> list[tuple[str, URLFile]]:
        root = models_dir() / "mmaudio"
        hf = "https://huggingface.co/"
        clip, big = hf + "apple/DFN5B-CLIP-ViT-H-14-384/resolve/main/", hf + "nvidia/bigvgan_v2_44khz_128band_512x/resolve/main/"
        return [
            ("model", URLFile(hf + f"hkchengrex/MMAudio/resolve/main/weights/mmaudio_{self.variant}.pth",
                              root / f"mmaudio_{self.variant}.pth", f"MMAudio {self.variant}", _MD5[self.variant])),
            ("vae", URLFile(_RELEASE + "v1-44.pth", root / "v1-44.pth", "autoencoder audio",
                            "fab020275fa44c6589820ce025191600")),
            ("sync", URLFile(_RELEASE + "synchformer_state_dict.pth", root / "synchformer_state_dict.pth",
                             "Synchformer", "5b2f5594b0730f70e41e549b7c94390c")),
            ("clip_cfg", URLFile(clip + "open_clip_config.json", root / "clip" / "open_clip_config.json",
                                 "configurazione CLIP")),
            ("clip", URLFile(clip + "open_clip_pytorch_model.bin", root / "clip" / "open_clip_pytorch_model.bin",
                             "encoder visivo CLIP")),
            ("vocoder_cfg", URLFile(big + "config.json", root / "bigvgan" / "config.json",
                                    "configurazione vocoder")),
            ("vocoder", URLFile(big + "bigvgan_generator.pt", root / "bigvgan" / "bigvgan_generator.pt",
                                "vocoder BigVGAN")),
        ]

    def ensure_weights(self, progress: ProgressFn, cancel: Optional[threading.Event] = None) -> None:
        files = self._files()
        for i, (key, item) in enumerate(files, 1):
            step = f" ({i}/{len(files)})"
            self._paths[key] = fetch_url(item, lambda msg, f, step=step: progress(msg + step, f), cancel)
        # La cache Hugging Face delle versioni precedenti (circa 9 GB) non serve più.
        remove_old_hf_cache(hf_home() / "hub")

    def load(self, progress: ProgressFn) -> None:
        import torch
        from mmaudio.ext.autoencoder import autoencoder as ae_mod
        from mmaudio.model.networks import get_my_mmaudio
        from mmaudio.model.utils import features_utils as fu_mod
        from mmaudio.model.utils.features_utils import FeaturesUtils

        device = self._device or ("cuda" if torch.cuda.is_available() else "cpu")
        # Transformer, CLIP e Synchformer in bfloat16 (RTX 30xx in su): metà VRAM, qualità invariata.
        # Il decoder audio e il vocoder disegnano la forma d'onda: con la precisione piena restano in
        # float32, che costa poca memoria (circa 0,5 GB) ed evita l'audio sporco.
        dtype = torch.bfloat16 if device == "cuda" and torch.cuda.get_device_capability()[0] >= 8 else torch.float32
        if device == "cuda":
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = not self.full_precision

        progress("Carico MMAudio in memoria", None)
        net = get_my_mmaudio(self.variant).to(device, dtype).eval()
        try:
            state = torch.load(self._paths["model"], map_location=device, weights_only=True)
        except OSError:
            log.error("Apertura dei pesi non riuscita:\n%s", describe_path(self._paths["model"]))
            raise
        net.load_weights(state)

        # MMAudio scarica CLIP e il vocoder da Hugging Face a ogni avvio; qui lo si dirotta sui file
        # già scaricati da noi, senza passare dalla cache di Hugging Face.
        clip_dir, big_dir = self._paths["clip"].parent, self._paths["vocoder"].parent
        orig_clip, orig_big = fu_mod.create_model_from_pretrained, ae_mod.BigVGANv2.from_pretrained

        def local_clip(_name, **kw):
            return orig_clip(f"local-dir:{clip_dir}", **kw)

        def local_big(_name, **kw):
            return orig_big(str(big_dir), **kw)

        progress("Carico CLIP, Synchformer e il vocoder", None)
        with mock.patch.object(fu_mod, "create_model_from_pretrained", local_clip), \
                mock.patch.object(ae_mod.BigVGANv2, "from_pretrained", local_big):
            fu = FeaturesUtils(
                tod_vae_ckpt=str(self._paths["vae"]),
                synchformer_ckpt=str(self._paths["sync"]),
                enable_conditions=True,
                mode="44k",
                bigvgan_vocoder_ckpt=None,
                need_vae_encoder=False,
            ).to(device, dtype).eval()
        if self.full_precision:
            fu.tod.float()
        self._decode_dtype = torch.float32 if self.full_precision else dtype
        if device == "cuda":
            torch.cuda.empty_cache()
        self._net, self._fu, self._dtype, self._device = net, fu, dtype, device

    def unload(self) -> None:
        self._net = self._fu = None
        try:
            import gc

            import torch

            gc.collect()
            torch.cuda.empty_cache()
        except Exception:
            pass

    def generate(
        self,
        frames: list[np.ndarray],
        duration: float,
        params: GenerationParams,
        seeds: list[int],
        on_progress: Optional[Callable[[float], None]] = None,
        cancel: Optional[threading.Event] = None,
    ) -> list[np.ndarray]:
        import torch
        from mmaudio.model.flow_matching import FlowMatching
        from mmaudio.model.sequence_config import CONFIG_44K

        net, fu, device, dtype = self._net, self._fu, self._device, self._dtype
        seq = dataclasses.replace(CONFIG_44K, duration=duration)
        clip_u8 = frames[0][: seq.clip_seq_len]
        sync_u8 = frames[1][: int(seq.sync_frame_rate * duration)]

        # Stesse trasformazioni di mmaudio.eval_utils.load_video; la normalizzazione CLIP la fa FeaturesUtils.
        clip = torch.from_numpy(clip_u8).permute(0, 3, 1, 2).unsqueeze(0).to(device, dtype) / 255.0
        sync = torch.from_numpy(sync_u8).permute(0, 3, 1, 2).unsqueeze(0).to(device, dtype) / 255.0
        sync = (sync - 0.5) / 0.5

        net.update_seq_lengths(seq.latent_seq_len, seq.clip_seq_len, seq.sync_seq_len)
        outputs = []
        with torch.inference_mode():
            clip_f = fu.encode_video_with_clip(clip, batch_size=40)
            sync_f = fu.encode_video_with_sync(sync, batch_size=40)
            text_f = fu.encode_text([params.prompt])
            neg_f = fu.encode_text([params.negative_prompt])
            conditions = net.preprocess_conditions(clip_f, sync_f, text_f)
            empty = net.get_empty_conditions(1, negative_text_features=neg_f)
            fm = FlowMatching(min_sigma=0, inference_mode="euler", num_steps=params.steps)

            for v, seed in enumerate(seeds):
                rng = torch.Generator(device=device)
                rng.manual_seed(seed)
                x0 = torch.randn(1, net.latent_seq_len, net.latent_dim, device=device, dtype=dtype, generator=rng)
                calls = 0

                def ode(t, x, v=v):
                    nonlocal calls
                    if cancel is not None and cancel.is_set():
                        raise Cancelled()
                    calls += 1
                    if on_progress is not None:
                        on_progress((v + min(calls, params.steps) / params.steps) / len(seeds))
                    return net.ode_wrapper(t, x, conditions, empty, params.guidance)

                x1 = net.unnormalize(fm.to_data(ode, x0))
                audio = fu.vocode(fu.decode(x1.to(self._decode_dtype))).float().cpu().numpy()[0]
                outputs.append(audio[None] if audio.ndim == 1 else audio)
        if device == "cuda":
            torch.cuda.empty_cache()  # restituisce la VRAM temporanea: serve anche al lettore video
        return outputs
