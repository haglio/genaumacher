from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QThread, Signal

from genaumacher.export_pipeline import run_export

if TYPE_CHECKING:
    from genaumacher.state import VideoState


def connect_export(state: VideoState, dialog) -> ExportWorker:
    worker = ExportWorker(state)
    worker.stage_changed.connect(dialog.set_stage)
    worker.clip_progress.connect(dialog.set_clip_progress)
    worker.normalize_progress.connect(dialog.set_normalize_progress)
    worker.audio_progress.connect(dialog.set_audio_progress)
    worker.export_finished.connect(
        lambda ok, msg: (dialog.set_done(ok), dialog.set_error("" if ok else msg))
    )
    return worker


class ExportWorker(QThread):
    stage_changed = Signal(str)
    clip_progress = Signal(float)
    normalize_progress = Signal(float)
    audio_progress = Signal(float)
    export_finished = Signal(bool, str)

    def __init__(self, state: VideoState, parent=None):
        super().__init__(parent)
        self._state = state

    def stage(self, text: str) -> None:
        self.stage_changed.emit(text)

    def clip(self, fraction: float) -> None:
        self.clip_progress.emit(fraction)

    def normalize(self, fraction: float) -> None:
        self.normalize_progress.emit(fraction)

    def audio(self, fraction: float) -> None:
        self.audio_progress.emit(fraction)

    def run(self) -> None:
        ok, message = run_export(self._state, self)
        self.export_finished.emit(ok, message)
