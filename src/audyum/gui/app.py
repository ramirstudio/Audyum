from __future__ import annotations

import html
import logging
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

from audyum.paths import configure_environment, logs_dir

configure_environment()

from PySide6.QtCore import QObject, Qt, QThread, QUrl, Signal, Slot  # noqa: E402
from PySide6.QtGui import QDesktopServices, QIcon  # noqa: E402
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from audyum import engines  # noqa: E402
from audyum import ui_settings  # noqa: E402
from audyum.gui import theme  # noqa: E402
from audyum.gui.settings_dialog import SettingsDialog  # noqa: E402
from audyum.gui.video_view import VideoView  # noqa: E402
from audyum.media import Cancelled, probe  # noqa: E402
from audyum.pipeline import JobSettings, VariantResult, run_job  # noqa: E402

log = logging.getLogger("audyum")

VIDEO_FILTER = "Video (*.mp4 *.mov *.mkv *.webm *.avi *.m4v *.mts *.m2ts *.wmv *.flv)"
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".mts", ".m2ts", ".wmv", ".flv"}


def _friendly_error(e: BaseException) -> str:
    text = f"{type(e).__name__}: {e}"
    if "out of memory" in text.lower():
        return ("La memoria della GPU non basta. Scegli il modello bilanciato o veloce, "
                "oppure chiudi gli altri programmi che usano la scheda video.")
    if any(k in text for k in ("ConnectionError", "Timeout", "HTTPError", "MaxRetryError", "LocalEntryNotFound")):
        return ("Il download dei pesi non è riuscito. Controlla la connessione e riprova: "
                "il download riparte da dove si era fermato.")
    return f"{text}\n\nDettagli nel log: {logs_dir() / 'audyum.log'}"


def _fmt_time(ms: int) -> str:
    s = max(0, ms) // 1000
    return f"{s // 60}:{s % 60:02d}"


class JobWorker(QObject):
    progress = Signal(str, float)  # frazione < 0: durata indeterminata
    done = Signal(list)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, video: Path, engine, settings: JobSettings, out_dir: Path, cancel: threading.Event):
        super().__init__()
        self.video, self.engine, self.settings, self.out_dir, self.cancel = video, engine, settings, out_dir, cancel

    @Slot()
    def run(self) -> None:
        try:
            import torch

            if not torch.cuda.is_available():
                self.progress.emit("GPU NVIDIA non trovata: genero sulla CPU, sarà molto lento", -1.0)
            results = run_job(self.video, self.engine, self.settings, self.out_dir,
                              lambda m, f: self.progress.emit(m, -1.0 if f is None else float(f)), self.cancel)
        except Cancelled:
            self.cancelled.emit()
        except BaseException as e:  # noqa: BLE001 - qualunque errore va mostrato all'utente
            log.exception("Generazione non riuscita")
            self.failed.emit(_friendly_error(e))
        else:
            self.done.emit(results)


class MainWindow(QMainWindow):
    def __init__(self, ui: ui_settings.UISettings | None = None):
        ui = ui or ui_settings.UISettings()
        super().__init__()
        self.setWindowTitle("Audyum")
        self.setMinimumSize(1080, 660)
        self.setAcceptDrops(True)
        self._file_info = None
        self.video: Path | None = None
        self.out_dir: Path | None = None
        self.results: list[VariantResult] = []
        self._engines: dict[str, engines.Engine] = {}
        self._thread: QThread | None = None
        self._worker: JobWorker | None = None
        self._cancel = threading.Event()

        self.ui = ui
        self.backdrop = theme.Backdrop(ui)
        root = theme.GradientRoot(self.backdrop)
        lay = QHBoxLayout(root)
        lay.setContentsMargins(40, 24, 28, 24)
        lay.setSpacing(56)
        lay.addLayout(self._build_player(), 3)
        lay.addWidget(self._build_panel(), 0)
        self.setCentralWidget(root)
        self._refresh_state()

    # ---- costruzione ----------------------------------------------------------------------

    def _build_player(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(14)
        head = QHBoxLayout()
        mark = QLabel("Audyum")
        mark.setObjectName("wordmark")
        self.settings_btn = QPushButton("Impostazioni")
        self.settings_btn.clicked.connect(self._open_settings)
        head.addWidget(mark, 1)
        head.addWidget(self.settings_btn, 0, Qt.AlignTop)
        col.addLayout(head)

        self.video_view = VideoView(radius=18, hint="Trascina qui un video muto")
        col.addWidget(self.video_view, 1)

        self.player = QMediaPlayer(self)
        self.audio_out = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_out)
        self.player.setVideoOutput(self.video_view.sink)

        self._icon_play = QIcon(str(theme.ICONS / "play.svg"))
        self._icon_pause = QIcon(str(theme.ICONS / "pause.svg"))
        transport = QHBoxLayout()
        transport.setSpacing(14)
        self.play_btn = QPushButton()
        self.play_btn.setObjectName("round")
        self.play_btn.setFixedSize(44, 44)
        self.play_btn.setIcon(self._icon_play)
        self.play_btn.setToolTip("Riproduci")
        self.play_btn.clicked.connect(self._toggle_play)
        self.seek = QSlider(Qt.Horizontal)
        self.seek.sliderMoved.connect(self.player.setPosition)
        self.time_lbl = QLabel("0:00 / 0:00")
        self.time_lbl.setObjectName("muted")
        transport.addWidget(self.play_btn)
        transport.addWidget(self.seek, 1)
        transport.addWidget(self.time_lbl)
        col.addLayout(transport)

        self.player.durationChanged.connect(lambda d: (self.seek.setRange(0, d), self._update_time()))
        self.player.positionChanged.connect(self._on_position)
        self.player.playbackStateChanged.connect(
            lambda s: self.play_btn.setIcon(self._icon_pause if s == QMediaPlayer.PlayingState else self._icon_play))
        return col

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("section")
        return lbl

    def _muted(self, text: str = "", name: str = "muted") -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName(name)
        lbl.setWordWrap(True)
        return lbl

    def _group(self) -> tuple[QFrame, QVBoxLayout]:
        box = QFrame()
        box.setObjectName("group")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(10)
        return box, lay

    def _sep(self) -> QFrame:
        line = QFrame()
        line.setObjectName("sep")
        return line

    def _row(self, label: str, *widgets) -> QHBoxLayout:
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setObjectName("rowLabel")
        row.addWidget(lbl, 1)
        for w in widgets:
            row.addWidget(w)
        return row

    def _build_panel(self) -> QScrollArea:
        panel = QWidget()
        col = QVBoxLayout(panel)
        col.setContentsMargins(0, 0, 10, 0)
        col.setSpacing(6)

        col.addWidget(self._section("Video"))
        box, g = self._group()
        self.file_lbl = QLabel("Nessun file")
        self.file_lbl.setWordWrap(True)
        g.addWidget(self.file_lbl)
        g.addWidget(self._sep())
        self.out_lbl = self._muted("")
        g.addWidget(self.out_lbl)
        btns = QHBoxLayout()
        open_btn = QPushButton("Apri video…")
        open_btn.clicked.connect(self._choose_video)
        self.out_btn = QPushButton("Cambia cartella…")
        self.out_btn.clicked.connect(self._choose_out_dir)
        btns.addWidget(open_btn, 1)
        btns.addWidget(self.out_btn, 1)
        g.addLayout(btns)
        col.addWidget(box)

        col.addWidget(self._section("Suoni"))
        box, g = self._group()
        self.prompt = QPlainTextEdit()
        self.prompt.setPlaceholderText("Descrizione facoltativa, in inglese. Esempio: heavy rain on a car roof")
        self.prompt.setFixedHeight(72)
        self.negative = QLineEdit()
        self.negative.setPlaceholderText("Da evitare, in inglese. Esempio: music, speech")
        g.addWidget(self.prompt)
        g.addWidget(self.negative)
        col.addWidget(box)
        col.addWidget(self._muted("Senza descrizione il modello decide dai soli fotogrammi.", "footnote"))

        col.addWidget(self._section("Modello"))
        box, g = self._group()
        self.model = QComboBox()
        for key, (label, _) in engines.PRESETS.items():
            self.model.addItem(label, key)
        self.model.setCurrentIndex(self.model.findData(engines.DEFAULT_PRESET))
        g.addWidget(self.model)
        g.addWidget(self._sep())
        self.variants = QSpinBox()
        self.variants.setRange(1, 6)
        self.variants.setFixedWidth(90)
        self.variants.setAlignment(Qt.AlignRight)
        g.addLayout(self._row("Varianti", self.variants))
        g.addWidget(self._sep())
        self.random_seed = QCheckBox()
        self.random_seed.setChecked(True)
        g.addLayout(self._row("Seme casuale", self.random_seed))
        self.seed = QSpinBox()
        self.seed.setRange(0, 2**31 - 1)
        self.seed.setValue(42)
        self.seed.setFixedWidth(140)
        self.seed.setAlignment(Qt.AlignRight)
        self.seed.setEnabled(False)
        seed_row_w = QWidget()
        seed_row = self._row("Seme", self.seed)
        seed_row.setContentsMargins(0, 0, 0, 0)
        seed_row_w.setLayout(seed_row)
        seed_row_w.setVisible(False)
        self.random_seed.toggled.connect(lambda on: (self.seed.setEnabled(not on), seed_row_w.setVisible(not on)))
        g.addWidget(seed_row_w)
        col.addWidget(box)
        col.addWidget(self._muted("Pesi MMAudio sotto licenza CC BY-NC 4.0, uso non commerciale. "
                                  "Al primo utilizzo vengono scaricati circa 10 GB.", "footnote"))

        self.adv_btn = QToolButton()
        self.adv_btn.setObjectName("disclosure")
        self.adv_btn.setText("Mostra parametri avanzati")
        self.adv_btn.setCheckable(True)
        col.addWidget(self.adv_btn)
        adv, g = self._group()
        self.steps = QSpinBox()
        self.steps.setRange(8, 100)
        self.steps.setValue(25)
        self.guidance = QDoubleSpinBox()
        self.guidance.setRange(1.0, 12.0)
        self.guidance.setSingleStep(0.5)
        self.guidance.setValue(4.5)
        self.window = QSpinBox()
        self.window.setRange(4, 8)
        self.window.setValue(8)
        self.window.setSuffix(" s")
        self.overlap = QSpinBox()
        self.overlap.setRange(1, 3)
        self.overlap.setValue(1)
        self.overlap.setSuffix(" s")
        self.normalize = QCheckBox()
        self.normalize.setChecked(True)
        rows = [("Passi", self.steps), ("Aderenza al video", self.guidance), ("Finestra", self.window),
                ("Sovrapposizione", self.overlap)]
        for i, (label, w) in enumerate(rows):
            w.setFixedWidth(90)
            w.setAlignment(Qt.AlignRight)
            if i:
                g.addWidget(self._sep())
            g.addLayout(self._row(label, w))
        g.addWidget(self._sep())
        g.addLayout(self._row("Picco a -1 dBFS", self.normalize))
        adv.setVisible(False)
        self.adv_btn.toggled.connect(lambda on: (adv.setVisible(on), self.adv_btn.setText(
            "Nascondi parametri avanzati" if on else "Mostra parametri avanzati")))
        col.addWidget(adv)

        col.addSpacing(14)
        self.gen_btn = QPushButton("Genera audio")
        self.gen_btn.setObjectName("primary")
        self.gen_btn.clicked.connect(self._start)
        col.addWidget(self.gen_btn)
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 1000)
        self.bar.setValue(0)
        status_row = QHBoxLayout()
        self.status = self._muted("")
        self.cancel_btn = QPushButton("Annulla")
        self.cancel_btn.setObjectName("plain")
        self.cancel_btn.clicked.connect(self._cancel_job)
        status_row.addWidget(self.status, 1)
        status_row.addWidget(self.cancel_btn)
        col.addWidget(self.bar)
        col.addLayout(status_row)

        col.addWidget(self._section("Risultati"))
        box, g = self._group()
        g.setContentsMargins(0, 4, 0, 4)
        self.result_list = QListWidget()
        self.result_list.setMinimumHeight(150)
        self.result_list.currentRowChanged.connect(self._preview_row)
        g.addWidget(self.result_list)
        row = QHBoxLayout()
        self.save_video_btn = QPushButton("Salva video…")
        self.save_video_btn.clicked.connect(lambda: self._save_selected(video=True))
        self.save_wav_btn = QPushButton("Salva WAV…")
        self.save_wav_btn.clicked.connect(lambda: self._save_selected(video=False))
        self.open_dir_btn = QPushButton("Cartella")
        self.open_dir_btn.clicked.connect(self._open_out_dir)
        row.addWidget(self.save_video_btn)
        row.addWidget(self.save_wav_btn)
        row.addWidget(self.open_dir_btn)
        g.addLayout(row)
        col.addWidget(box)
        col.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidget(panel)
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(440)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        return scroll

    # ---- stato ----------------------------------------------------------------------------

    def _busy(self) -> bool:
        return self._thread is not None

    def _refresh_state(self) -> None:
        busy = self._busy()
        self.gen_btn.setEnabled(self.video is not None and not busy)
        self.cancel_btn.setEnabled(busy)
        self.out_btn.setEnabled(self.video is not None and not busy)
        has_result = self.result_list.currentRow() > 0
        self.save_video_btn.setEnabled(has_result)
        self.save_wav_btn.setEnabled(has_result)
        self.open_dir_btn.setEnabled(bool(self.results))
        for w in (self.model, self.prompt, self.negative, self.variants, self.steps, self.guidance,
                  self.window, self.overlap):
            w.setEnabled(not busy)

    def _on_position(self, pos: int) -> None:
        if not self.seek.isSliderDown():
            self.seek.setValue(pos)
        self._update_time()

    def _update_time(self) -> None:
        self.time_lbl.setText(f"{_fmt_time(self.player.position())} / {_fmt_time(self.player.duration())}")

    def _toggle_play(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    # ---- file -----------------------------------------------------------------------------

    def dragEnterEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if urls and Path(urls[0].toLocalFile()).suffix.lower() in VIDEO_SUFFIXES:
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        self._set_video(Path(event.mimeData().urls()[0].toLocalFile()))

    def _render_file_label(self) -> None:
        if not getattr(self, "_file_info", None):
            return
        name, detail = self._file_info
        self.file_lbl.setText(
            f"<span style='color:{theme.C['peach']}; font-weight:700'>{html.escape(name)}</span><br>"
            f"<span style='color:{theme.C['secondary']}'>{html.escape(detail)}</span>")

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self.ui, self.backdrop, self)
        dlg.changed.connect(self._apply_ui)
        dlg.exec()

    def _apply_ui(self, ui: ui_settings.UISettings) -> None:
        self.ui = ui
        self.backdrop.set(ui)
        theme.restyle(QApplication.instance(), ui)
        self._render_file_label()
        self.centralWidget().update()
        ui_settings.save(ui)

    def _choose_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Apri video", str(self.video.parent if self.video else ""),
                                              VIDEO_FILTER)
        if path:
            self._set_video(Path(path))

    def _set_video(self, path: Path) -> None:
        if self._busy():
            return
        try:
            info = probe(path)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Video non leggibile", str(e))
            return
        self.video = path
        self.out_dir = path.parent / "Audyum"
        self.results = []
        note = " · contiene già una traccia audio, verrà sostituita" if info.has_audio else ""
        self._file_info = (path.name, f"{info.width}×{info.height} · {info.fps:.2f} fps · {info.duration:.1f} s{note}")
        self._render_file_label()
        self.out_lbl.setText(f"Salva in {self.out_dir}")
        self.result_list.clear()
        QListWidgetItem("Originale", self.result_list)
        self.result_list.setCurrentRow(0)
        self._refresh_state()

    def _choose_out_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Cartella di uscita", str(self.out_dir or ""))
        if path:
            self.out_dir = Path(path)
            self.out_lbl.setText(f"Salva in {self.out_dir}")

    def _preview_row(self, row: int) -> None:
        if row < 0 or self.video is None:
            return
        source = self.video if row == 0 else self.results[row - 1].video
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(str(source)))
        self._refresh_state()

    def _save_selected(self, video: bool) -> None:
        row = self.result_list.currentRow()
        if row <= 0:
            return
        src = self.results[row - 1].video if video else self.results[row - 1].wav
        filt = f"*{src.suffix}"
        dest, _ = QFileDialog.getSaveFileName(self, "Salva", str(Path.home() / src.name), filt)
        if dest:
            shutil.copy2(src, dest)

    def _open_out_dir(self) -> None:
        if self.out_dir is None:
            return
        if sys.platform == "win32":
            os.startfile(self.out_dir)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(self.out_dir)])
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.out_dir)))

    # ---- generazione ----------------------------------------------------------------------

    def _engine(self) -> engines.Engine:
        key = self.model.currentData()
        for other, eng in list(self._engines.items()):
            if other != key:  # un solo modello in VRAM alla volta
                eng.unload()
                del self._engines[other]
        if key not in self._engines:
            self._engines[key] = engines.create(key)
        return self._engines[key]

    def _start(self) -> None:
        if self.video is None or self._busy():
            return
        settings = JobSettings(
            prompt=self.prompt.toPlainText().strip(),
            negative_prompt=self.negative.text().strip(),
            steps=self.steps.value(),
            guidance=self.guidance.value(),
            variants=self.variants.value(),
            seed=None if self.random_seed.isChecked() else self.seed.value(),
            window=self.window.value(),
            overlap=min(self.overlap.value(), self.window.value() - 1),
            normalize=self.normalize.isChecked(),
        )
        self.player.stop()
        self.player.setSource(QUrl())  # libera il file se si rigenera nella stessa cartella
        self._cancel = threading.Event()
        self._thread = QThread(self)
        self._worker = JobWorker(self.video, self._engine(), settings, self.out_dir, self._cancel)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.cancelled.connect(self._on_cancelled)
        for sig in (self._worker.done, self._worker.failed, self._worker.cancelled):
            sig.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_finished)
        self.status.setText("Avvio")
        self._thread.start()
        self._refresh_state()

    def _cancel_job(self) -> None:
        self._cancel.set()
        self.status.setText("Annullo…")

    @Slot(str, float)
    def _on_progress(self, msg: str, frac: float) -> None:
        self.status.setText(msg)
        if frac < 0:
            self.bar.setRange(0, 0)
        else:
            self.bar.setRange(0, 1000)
            self.bar.setValue(int(frac * 1000))

    @Slot(list)
    def _on_done(self, results: list) -> None:
        self.results = results
        self.result_list.clear()
        QListWidgetItem("Originale", self.result_list)
        for i, r in enumerate(results, 1):
            QListWidgetItem(f"Variante {i} · seme {r.seed}", self.result_list)
        self.result_list.setCurrentRow(1)
        self.status.setText(f"Salvato in {self.out_dir}")

    @Slot(str)
    def _on_failed(self, msg: str) -> None:
        self.status.setText("Generazione non riuscita")
        QMessageBox.critical(self, "Errore", msg)

    @Slot()
    def _on_cancelled(self) -> None:
        self.status.setText("Annullato")

    @Slot()
    def _on_thread_finished(self) -> None:
        self.bar.setRange(0, 1000)
        self.bar.setValue(1000 if self.results else 0)
        self._thread.deleteLater()
        self._worker.deleteLater()
        self._thread = self._worker = None
        self._refresh_state()

    def closeEvent(self, event) -> None:
        if self._busy():
            self._cancel.set()
            self._thread.wait(15000)
        super().closeEvent(event)


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Audyum")
    app.setWindowIcon(QIcon(str(Path(__file__).parent / "icon.png")))
    ui = ui_settings.load()
    theme.apply(app, ui)
    win = MainWindow(ui)
    win.show()
    if len(sys.argv) > 1 and Path(sys.argv[1]).exists():
        win._set_video(Path(sys.argv[1]))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
