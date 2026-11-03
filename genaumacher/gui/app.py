from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QApplication
from shared_ui.colors import dress_application
from shared_ui.preview import Preview
from shared_ui.preview_icon import app_icon

from genaumacher.window_icons import genaumacher_icon_path

from .main_window import GenaumacherMainWindow
from .playback_timer import PlaybackTimer

if TYPE_CHECKING:
    from genaumacher.state import VideoState


class GenaumacherApp:
    def __init__(self, state: VideoState, *, preview: Preview | None = None):
        self._state = state

        # app.main() set the AppUserModelID Windows groups the taskbar button by.

        self._app = QApplication.instance()
        if self._app is None:
            self._app = QApplication(sys.argv)
        self._app.setApplicationName("Genaumacher")
        dress_application(self._app)

        self._app.setWindowIcon(app_icon(genaumacher_icon_path(), preview))

        self.window = GenaumacherMainWindow(state, preview=preview)
        self.playback_timer = PlaybackTimer()
        self.playback_timer.tick.connect(self._on_tick)
        self.window.closed.connect(self.playback_timer.stop)

    def run(self) -> int:
        self.window.show()
        self.playback_timer.start()
        return self._app.exec()

    def _on_tick(self) -> None:
        self.window.render(self._state)
