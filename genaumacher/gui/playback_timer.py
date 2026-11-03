from __future__ import annotations

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class PlaybackTimer(QObject):
    tick = pyqtSignal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.interval_ms = 16
        self._timer = QTimer(self)
        self._timer.setInterval(self.interval_ms)
        self._timer.timeout.connect(self.tick)

    def start(self) -> None:
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
