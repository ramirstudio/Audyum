# Audyum

Programma per Windows che prende un video muto e gli genera sopra l'audio con un modello di IA che gira in locale sulla tua scheda video. Produce il video con la nuova traccia (il video non viene ricodificato) e un WAV a 24 bit da usare nel montaggio.

Il motore è [MMAudio](https://github.com/hkchengrex/MMAudio) (Cheng et al., CVPR 2025) nella variante `large_44k_v2`: guarda i fotogrammi con CLIP per capire cosa c'è in scena e con Synchformer per agganciare i suoni agli istanti giusti (passi, colpi, porte), poi genera audio a 44,1 kHz. Una descrizione testuale facoltativa orienta il risultato.

## Perché MMAudio e non MiniMax

Hailuo 2.3 di MiniMax è un modello chiuso, accessibile solo a pagamento via API, e non genera audio. MiniMax H3 (Hailuo 3.0), rilasciato con pesi aperti ad agosto 2026, genera video con audio e in modalità Ref2VA accetta un video come riferimento, quindi corrisponde all'idea di far credere al generatore che il video in ingresso sia il suo. Però ricrea anche le immagini invece di lasciarle intatte, e l'Omni Transformer da 33 miliardi di parametri più l'encoder Qwen3-VL da 32 miliardi richiedono diverse GPU da data center (il deploy ufficiale ne usa 4). Su una scheda da 12 GB non gira.

HunyuanVideo-Foley di Tencent ottiene punteggi migliori nei benchmark e con l'offload starebbe in 12 GB, ma la sua licenza esclude esplicitamente l'Unione Europea, il Regno Unito e la Corea del Sud. ThinkSound è rilasciato "solo per ricerca". Tra i modelli gratuiti utilizzabili legalmente in Italia su una GPU consumer, MMAudio resta il migliore per qualità e sincronia, e occupa circa 6 GB di VRAM.

Il codice è organizzato a motori (`src/audyum/engines/`): aggiungere un altro modello significa scrivere una sottoclasse di `Engine` e registrarla in `engines/__init__.py`.

## Requisiti

Windows 10 o 11 a 64 bit, scheda NVIDIA con almeno 8 GB di VRAM (il riferimento è una RTX 3080 Ti da 12 GB), driver recente, circa 20 GB liberi su disco e connessione a internet per la prima installazione. Senza GPU NVIDIA il programma funziona sulla CPU, ma una clip di pochi secondi richiede diversi minuti.

## Installazione

L'installer si scarica dalla pagina Actions del repository (artefatto `Audyum-Setup` del workflow "Installer Windows") oppure dalle Release quando viene pubblicato un tag `v*`. Non chiede privilegi di amministratore e si installa in `%LOCALAPPDATA%\Programs\Audyum`.

Il file è piccolo perché contiene solo il codice e `uv`. Durante l'installazione si apre una finestra che scarica Python 3.11, PyTorch con CUDA 12.8 e MMAudio (circa 4 GB). Al primo "Genera audio" il programma scarica i pesi dei modelli, circa 10 GB, in `%LOCALAPPDATA%\Audyum\models`; il download riparte da dove si era fermato se viene interrotto. Se l'ambiente si rompe, "Audyum - ripara installazione" nel menu Start lo ricrea.

## Uso

Trascina il video nella finestra o aprilo con "Apri video…", scrivi se vuoi una descrizione dei suoni e premi "Genera audio". La descrizione va in inglese, perché l'encoder di testo è CLIP: per esempio `footsteps on wet gravel, light rain, distant traffic`. Nel campo dei suoni da evitare funziona bene `music` quando il modello tende ad aggiungere musica di sottofondo.

Con più varianti ottieni tracce diverse dallo stesso video e scegli la migliore ascoltandole nel lettore; il seme di ogni variante è nel nome del file, così puoi rigenerarla identica. I file finiscono in una cartella `Audyum` accanto al video, oppure dove indichi con "Cambia cartella di uscita…".

I parametri avanzati hanno valori predefiniti che vanno bene nella maggior parte dei casi. I passi sono 25: salire oltre cambia poco. L'aderenza al video è 4,5; valori più alti seguono di più immagini e testo ma possono indurire il suono. MMAudio è addestrato su clip di 8 secondi, per cui i video più lunghi vengono generati a finestre da 8 secondi che si sovrappongono di almeno 1 secondo e si uniscono con una dissolvenza, dopo aver allineato il volume nella zona comune.

Per elaborare molti file c'è la riga di comando, dalla cartella di installazione:

```
.venv\Scripts\audyum-cli.exe clip1.mp4 clip2.mp4 --prompt "ocean waves, seagulls" --variants 2
```

## Limiti

MMAudio genera effetti, ambienti e rumori, non parlato comprensibile: se nel video qualcuno parla, ottieni un brusio vocale senza parole. Per i dialoghi serve una pipeline diversa (lettura del labiale o testo fornito, poi sintesi vocale allineata alle labbra). Il video viene letto per intero in memoria a risoluzione ridotta: per clip più lunghe di 15-20 minuti conviene dividerle. I pesi di MMAudio sono sotto licenza CC BY-NC 4.0, quindi l'audio generato non si può usare per scopi commerciali.

## Sviluppo

I test non richiedono GPU né pesi: usano un motore finto e un video sintetico.

```
uv venv --python 3.11
uv pip install "av>=14.0.1" "numpy<2.1" pytest
.venv/bin/python -m pytest
```

Per compilare l'installer a mano su Windows: `uv lock`, poi copia `uv.exe` in `installer\bin\` e lancia `ISCC.exe installer\audyum.iss` (Inno Setup 6). Il workflow `.github/workflows/installer.yml` fa gli stessi passaggi, prima verifica che l'ambiente si installi davvero su Windows e poi pubblica l'installer come artefatto.

Licenze dei componenti inclusi o scaricati: MMAudio codice MIT e pesi CC BY-NC 4.0; font Instrument Serif e Instrument Sans SIL Open Font License (testi in `src/audyum/gui/fonts/`); PySide6 LGPL; PyAV include FFmpeg sotto LGPL.
