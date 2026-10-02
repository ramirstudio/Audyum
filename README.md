# Audyum

Programma per Windows che prende un video muto e gli genera sopra l'audio con un modello di IA che gira in locale sulla tua scheda video. Produce il video con la nuova traccia (l'immagine non viene ricodificata) e un WAV a 24 bit da usare nel montaggio. Funziona offline dopo il primo avvio.

Il motore è [MMAudio](https://github.com/hkchengrex/MMAudio) (Cheng et al., CVPR 2025), variante `large_44k_v2`: guarda i fotogrammi con CLIP per capire cosa c'è in scena e con Synchformer per agganciare i suoni agli istanti giusti (passi, colpi, porte), poi genera audio mono a 44,1 kHz. Una descrizione testuale facoltativa orienta il risultato.

## Requisiti

Windows 10 o 11 a 64 bit e una scheda NVIDIA con almeno 8 GB di VRAM (provato su una RTX 3080 Ti da 12 GB). Servono circa 20 GB liberi sul disco di installazione e una connessione a internet per la prima installazione. Senza GPU NVIDIA il programma gira sulla CPU, ma una clip di pochi secondi richiede diversi minuti.

## Installazione

Scarica `Audyum-Setup-<versione>.exe` dalla pagina delle Release (oppure dalla scheda Actions, artefatto `Audyum-Setup`). Non chiede privilegi di amministratore. Windows SmartScreen può avvisare che l'editore è sconosciuto, perché l'installer non è firmato: "Ulteriori informazioni", poi "Esegui comunque".

Nella schermata della cartella di destinazione puoi scegliere un altro disco: Python, PyTorch, la cache dei pacchetti e i modelli finiscono tutti lì, e il disco C: non viene toccato. Il file di installazione è piccolo perché contiene solo il codice e `uv`. Durante l'installazione si apre una finestra che scarica Python 3.11, PyTorch con CUDA 12.8 e MMAudio, circa 4 GB, e se la connessione cade riprova da sola. Al primo "Genera audio" il programma scarica i pesi dei modelli, circa 9 GB, in `data\models` dentro la cartella di installazione; anche questo download riprende da dove si era fermato.

Se l'ambiente si rompe, "Audyum - ripara installazione" nel menu Start lo ricrea senza riscaricare quello che c'è già.

## Uso

Trascina il video nella finestra o aprilo con "Apri video…", scrivi se vuoi una descrizione dei suoni e premi "Genera audio". La descrizione va in inglese, perché l'encoder di testo è CLIP: per esempio `footsteps on wet gravel, light rain, distant traffic`. Più è precisa sull'azione e sul materiale, meglio funziona: "wooden door closing slowly" rende più di "door". Tra i suoni da evitare è già scritto `music, speech`, perché il modello tende ad aggiungere musica e voci di sottofondo.

Con più varianti ottieni tracce diverse dallo stesso video e scegli la migliore ascoltandole nel lettore. Il seme di ogni variante è nel nome del file, così puoi riottenerla identica. I file finiscono in una cartella `Audyum` accanto al video, oppure dove indichi con "Cambia cartella…". I video girati in verticale con il telefono vengono letti con l'orientamento giusto e conservano la rotazione.

MMAudio è addestrato su clip di 8 secondi. I video più lunghi vengono generati a finestre da 8 secondi che si sovrappongono di almeno un secondo e si uniscono con una dissolvenza, dopo aver allineato il volume nella zona comune. Nei parametri avanzati i passi sono 40 e l'aderenza al video 4,5: valori più alti seguono di più immagini e testo ma possono indurire il suono. La "precisione piena" tiene in float32 il decoder e il vocoder, che disegnano la forma d'onda: costa poca memoria e toglie il suono sporco e metallico che si ha in bfloat16.

Il pulsante "Impostazioni" in alto a destra apre l'aspetto: cinque temi, sfumatura personalizzata, tinta unita o una tua immagine per lo sfondo, e il colore d'accento. Le scelte vengono salvate.

Per elaborare molti file c'è la riga di comando, dalla cartella di installazione:

```
.venv\Scripts\audyum-cli.exe clip1.mp4 clip2.mp4 --prompt "ocean waves, seagulls" --variants 2
```

## Limiti

MMAudio genera effetti, ambienti e rumori, non parlato comprensibile: se nel video qualcuno parla, ottieni un brusio senza parole. Per i dialoghi serve una pipeline diversa. Il video viene letto per intero in memoria a risoluzione ridotta, circa 450 MB al minuto: sopra i 15 minuti conviene dividerlo. I pesi di MMAudio sono sotto licenza CC BY-NC 4.0, quindi l'audio generato non si può usare per scopi commerciali.

## Perché MMAudio

Hailuo 2.3 di MiniMax è un modello chiuso, a pagamento via API, e non genera audio. MiniMax H3 ha pesi aperti dall'agosto 2026 e in modalità Ref2VA accetta un video di riferimento, ma ricrea anche le immagini e richiede un Omni Transformer da 33 miliardi di parametri più un encoder da 32: il deploy ufficiale usa quattro GPU da data center. HunyuanVideo-Foley ha ottimi punteggi, ma la sua licenza esclude l'Unione Europea, il Regno Unito e la Corea del Sud. ThinkSound e PrismAudio sono rilasciati solo per ricerca. Tra i modelli aperti utilizzabili in Italia su una GPU consumer, MMAudio ha i risultati migliori nei confronti pubblicati, e occupa circa 5 GB di VRAM.

Il codice è organizzato a motori in `src/audyum/engines/`: aggiungere un modello significa scrivere una sottoclasse di `Engine` e registrarla in `engines/__init__.py`.

## Sviluppo

I test non richiedono GPU né pesi: usano un motore finto, un video sintetico e un piccolo server HTTP locale.

```
uv venv --python 3.11
uv pip install "av>=14.0.1" "numpy<2.1" requests pytest
.venv/bin/python -m pytest
```

Per compilare l'installer a mano su Windows: `uv lock`, copia `uv.exe` (versione 0.7.22) in `installer\bin\` e lancia `ISCC.exe installer\audyum.iss` con Inno Setup 6. Il workflow `.github/workflows/installer.yml` fa gli stessi passaggi: prima esegue i test, poi verifica su Windows che l'ambiente si installi e che i moduli si importino, infine compila l'installer e lo pubblica come artefatto. Se il workflow parte da un tag `v*`, allega l'installer anche alla Release.

Licenze dei componenti in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
