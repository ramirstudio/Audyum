# Componenti di terze parti

Audyum usa e scarica i componenti seguenti. Ognuno resta sotto la propria licenza: quella indicata qui è un riassunto, fa fede il testo originale nel repository o nella scheda del modello.

| Componente | Uso | Licenza |
|---|---|---|
| [MMAudio](https://github.com/hkchengrex/MMAudio) (codice) | rete e utilità di inferenza | MIT |
| MMAudio, pesi `mmaudio_*_44k*.pth` | generazione dell'audio | CC BY-NC 4.0, solo uso non commerciale |
| [Synchformer](https://github.com/v-iashin/Synchformer) (pesi distribuiti con MMAudio) | sincronia audio-video | MIT |
| [DFN5B-CLIP-ViT-H-14-384](https://huggingface.co/apple/DFN5B-CLIP-ViT-H-14-384) | encoder di immagini e testo | vedi la scheda del modello |
| [BigVGAN v2 44 kHz](https://huggingface.co/nvidia/bigvgan_v2_44khz_128band_512x) | vocoder | MIT |
| [PyTorch](https://pytorch.org) | calcolo su GPU | BSD-3-Clause |
| [PySide6 / Qt](https://doc.qt.io/qtforpython-6/) | interfaccia grafica | LGPL-3.0 |
| [PyAV](https://github.com/PyAV-Org/PyAV) con le librerie FFmpeg incluse | lettura e scrittura dei video | BSD-3-Clause; FFmpeg secondo le licenze delle librerie incluse |
| [uv](https://github.com/astral-sh/uv) | installazione dell'ambiente Python | MIT o Apache-2.0 |
| Instrument Sans, Instrument Serif | caratteri dell'interfaccia | SIL Open Font License 1.1 (testi in `src/audyum/gui/fonts/`) |

I pesi si scaricano dai siti degli autori al primo utilizzo e non fanno parte dell'installer. L'uso commerciale dell'audio generato dipende dalla licenza dei pesi: con MMAudio non è consentito.
