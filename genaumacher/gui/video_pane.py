from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QWidget
from shared_ui.colors import BG_SECONDARY, BORDER_SUBTLE


class VideoPane(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._image: QImage | None = None
        self.setMinimumSize(320, 240)
        self.setStyleSheet(
            f"border: 1px solid {BORDER_SUBTLE.name()}; background: {BG_SECONDARY.name()};"
        )

    def set_frame(self, image: QImage | None) -> None:
        self._image = image
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), BG_SECONDARY)

        if self._image is not None:
            iw, ih = self._image.width(), self._image.height()
            x = (self.width() - iw) / 2
            y = (self.height() - ih) / 2
            p.drawImage(QRectF(x, y, iw, ih), self._image)

        p.end()
