from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
import pytest
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from genaumacher.create_session import build_session_payload
from genaumacher.editing import set_mark_in
from genaumacher.gui.main_window import GenaumacherMainWindow
from genaumacher.launch_choice import LoadSession
from genaumacher.session_launch import build_state
from genaumacher.session_persistence import current_payload

GOLDEN_SESSION = """{
  "version": 1,
  "session_name": "beta rehearsal",
  "video_path": "D:/media/example/beta rehearsal.mp4",
  "fps": 30.0,
  "total_frames": 480,
  "loaded_start": 60,
  "loaded_end": 210,
  "active_start": 90,
  "active_end": 150,
  "current": 120,
  "seconds_per_step": 1.0,
  "loop_mode": "base-tip",
  "wrap_mode": "blue",
  "speed": 1.25,
  "vr": true
}
"""


class _StubCapture:
    def __init__(self, fps: float, total_frames: int):
        self._fps = fps
        self._total = total_frames
        self._pos = 0

    def isOpened(self) -> bool:  # noqa: N802 -- cv2 spells it this way
        return True

    def get(self, prop):
        return {cv2.CAP_PROP_FPS: self._fps,
                cv2.CAP_PROP_FRAME_COUNT: float(self._total)}[prop]

    def set(self, prop, value) -> bool:
        self._pos = int(value)
        return True

    def read(self):
        if self._pos >= self._total:
            return False, None
        self._pos += 1
        return True, np.zeros((4, 4, 3), dtype=np.uint8)

    def release(self) -> None:
        pass


@pytest.fixture
def session_file(tmp_path: Path) -> Path:
    path = tmp_path / "beta rehearsal.json"
    path.write_text(GOLDEN_SESSION, encoding="utf-8")
    return path


@pytest.fixture
def load_session(session_file):
    def load():
        golden = json.loads(GOLDEN_SESSION)
        capture = _StubCapture(golden["fps"], golden["total_frames"])
        with patch("genaumacher.state_factory.cv2.VideoCapture", return_value=capture):
            return build_state(LoadSession(session_json=str(session_file)))

    return load


def test_the_two_writers_of_this_format_agree_on_it(make_state):
    created = build_session_payload(
        "D:/media/example/beta rehearsal.mp4", 2.0, 30.0, 480,
        session_name="beta rehearsal", seconds=5.0, loop_mode="base-tip", vr=True,
    )
    saved = current_payload(make_state())

    assert list(created) == list(saved) == list(json.loads(GOLDEN_SESSION))


def test_a_session_file_survives_a_load_and_a_save_byte_for_byte(session_file, load_session):
    state = load_session()

    state.autosave_session()

    assert session_file.read_text(encoding="utf-8") == GOLDEN_SESSION


def test_an_edit_rewrites_the_values_and_nothing_else(session_file, load_session):
    state = load_session()
    set_mark_in(state)

    saved = json.loads(session_file.read_text(encoding="utf-8"))
    golden = json.loads(GOLDEN_SESSION)

    assert list(saved) == list(golden)
    assert saved["active_start"] == 120
    assert {k: v for k, v in saved.items() if k != "active_start"} == {
        k: v for k, v in golden.items() if k != "active_start"
    }


def test_closing_an_edited_session_asks_nothing_and_loses_nothing(load_session):
    state = load_session()
    window = GenaumacherMainWindow(state)
    window.show()
    set_mark_in(state)

    boxes_it_put_up: list[str] = []

    def answer_any_box() -> None:
        box = QApplication.activeModalWidget()
        if box is not None:
            boxes_it_put_up.append(box.windowTitle())
            box.reject()

    answerer = QTimer()
    answerer.timeout.connect(answer_any_box)
    answerer.start(0)
    try:
        closed = window.close()
    finally:
        answerer.stop()

    assert boxes_it_put_up == []
    assert closed is True
    assert load_session().in_point == 120
