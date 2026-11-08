from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget
from shared_ui.colors import TEXT_PRIMARY
from shared_ui.icon_button import fill_square_with_icon
from shared_ui.icons import qt_icon

_ICON_COLOR_MATCHING_THE_LABEL_BESIDE_IT = TEXT_PRIMARY


class ButtonBar(QWidget):
    speed_down_clicked = pyqtSignal()
    speed_up_clicked = pyqtSignal()
    play_pause_clicked = pyqtSignal()
    export_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._icon_play = qt_icon("play", color=_ICON_COLOR_MATCHING_THE_LABEL_BESIDE_IT)
        self._icon_pause = qt_icon("pause", color=_ICON_COLOR_MATCHING_THE_LABEL_BESIDE_IT)

        self.speed_down_btn = QPushButton(qt_icon("minus", color=_ICON_COLOR_MATCHING_THE_LABEL_BESIDE_IT), "")
        self.speed_up_btn = QPushButton(qt_icon("plus", color=_ICON_COLOR_MATCHING_THE_LABEL_BESIDE_IT), "")
        self.play_pause_btn = QPushButton(self._icon_play, "")
        self.export_btn = QPushButton("export")

        for btn in (self.speed_down_btn, self.speed_up_btn, self.play_pause_btn):
            fill_square_with_icon(btn)

        self.speed_down_btn.clicked.connect(self.speed_down_clicked)
        self.speed_up_btn.clicked.connect(self.speed_up_clicked)
        self.play_pause_btn.clicked.connect(self.play_pause_clicked)
        self.export_btn.clicked.connect(self.export_clicked)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.speed_down_btn)
        layout.addWidget(self.speed_up_btn)
        layout.addWidget(self.play_pause_btn)
        layout.addWidget(self.export_btn)

    def set_playing(self, playing: bool) -> None:
        self.play_pause_btn.setIcon(
            self._icon_pause if playing else self._icon_play
        )
