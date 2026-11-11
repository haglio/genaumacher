from __future__ import annotations

import importlib
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pytest
from app_support import haglio_settings
from app_support.flick_folder import flat_flicks_in
from PySide6.QtCore import QEventLoop, QTimer

from genaumacher.clip_range import ClipRange
from genaumacher.frame_window import FrameWindow
from genaumacher.loop_cursor import LoopCursor
from genaumacher.loop_modes import read_loop_mode
from genaumacher.state import VideoState
from genaumacher.suggestions import Suggestions
from genaumacher.wrap_modes import read_wrap_mode
from tests.kept_out_of_his_files import (
    MODULES_BINDING_THE_LAST_SESSION_POINTER,
    MODULES_BINDING_THE_SESSIONS_FOLDER,
)

os.environ[haglio_settings.SETTINGS_ENV] = haglio_settings.THE_EXAMPLE

# Qt reads this when the QApplication below is built.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session", autouse=True)
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture(autouse=True, scope="session")
def _the_last_session_pointer_is_never_the_real_one_redirected_not_saved_and_restored_a_killed_run_never_restores(
        tmp_path_factory):
    scratch = tmp_path_factory.mktemp("pointer") / ".last_session.txt"
    with pytest.MonkeyPatch.context() as patcher:
        for name in MODULES_BINDING_THE_LAST_SESSION_POINTER:
            patcher.setattr(importlib.import_module(name), "LAST_SESSION_FILE", scratch)
        yield


@pytest.fixture(autouse=True, scope="session")
def _no_session_is_ever_written_into_the_checkouts_own_sessions_folder(tmp_path_factory):
    scratch = tmp_path_factory.mktemp("sessions")
    with pytest.MonkeyPatch.context() as patcher:
        for name in MODULES_BINDING_THE_SESSIONS_FOLDER:
            patcher.setattr(importlib.import_module(name), "SESSIONS_DIR", scratch)
        yield


class _FakeCapture:
    def __init__(self, total_frames: int):
        self._total = total_frames
        self._pos = 0

    def set(self, prop, value) -> bool:
        self._pos = int(value)
        return True

    def read(self):
        if self._pos >= self._total:
            return False, None
        self._pos += 1
        return True, np.zeros((2, 2, 3), dtype=np.uint8)

    def release(self) -> None:
        pass


class _FakeAutosave:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, state) -> None:
        self.calls += 1


@pytest.fixture
def ticked_within():
    def wait(signal, budget_ms: int) -> bool:
        seen = []
        loop = QEventLoop()

        def on_fire(*_args):
            seen.append(1)
            loop.quit()

        signal.connect(on_fire)
        QTimer.singleShot(budget_ms, loop.quit)
        loop.exec()
        signal.disconnect(on_fire)
        return bool(seen)
    return wait


@pytest.fixture
def shared_settings(tmp_path, monkeypatch):
    def use(values: dict | None = None) -> Path:
        settings = tmp_path / "haglio_settings.json"
        if values is not None:
            settings.write_text(json.dumps(values), encoding="utf-8")
        monkeypatch.setenv(haglio_settings.SETTINGS_ENV, str(settings))
        return settings

    return use


@pytest.fixture
def library(tmp_path, shared_settings) -> Path:
    root = tmp_path / "library"
    genau = root / "videos" / "videos" / "genau"
    flat_flicks_in(genau / "flicks").mkdir(parents=True)
    shared_settings({
        "library_root": str(root),
        "genau_dir": str(genau),
        "genau_audio_dir": str(root / "videos" / "audio" / "genau"),
    })
    return root


@pytest.fixture
def genau_sidecar(library):
    return lambda clip_name: (library / "videos" / "metadata" / "genau" / "flicks" / "2D" / "non_AI"
                              / f"{clip_name}.json")


@pytest.fixture
def recorded_cut(genau_sidecar):
    return lambda clip_name: json.loads(
        genau_sidecar(clip_name).read_text(encoding="utf-8"))["provenance"]["cut"]


@pytest.fixture
def rendered():
    def paint(widget):
        return widget.grab().toImage()
    return paint


@pytest.fixture
def frames_of():
    def factory(values: list[int], size: int = 1) -> list[np.ndarray]:
        return [np.full((size, size, 3), value, dtype=np.uint8) for value in values]
    return factory


@pytest.fixture
def textured_frames(textured_frames_solid_ones_have_no_keypoints_and_test_only_the_fallback):
    return textured_frames_solid_ones_have_no_keypoints_and_test_only_the_fallback


@pytest.fixture
def textured_frames_solid_ones_have_no_keypoints_and_test_only_the_fallback():
    def factory(count: int = 10, size: int = 128, seed: int = 10,
                drift: tuple[int, int] = (8, 6)) -> list[np.ndarray]:
        frame = np.random.RandomState(seed).randint(0, 256, (size, size, 3), dtype=np.uint8)
        shifted = []
        for i in range(count):
            travelled = i / max(1, count - 1)
            move = np.array(
                [[1, 0, drift[0] * travelled], [0, 1, drift[1] * travelled]],
                dtype=np.float32,
            )
            shifted.append(
                cv2.warpAffine(frame, move, (size, size), borderMode=cv2.BORDER_REFLECT)
            )
        return shifted
    return factory


@pytest.fixture
def values_of():
    def factory(frames: list[np.ndarray]) -> list[int]:
        return [int(frame[0, 0, 0]) for frame in frames]
    return factory


@dataclass
class _StateFields:
    total_frames: int = 100
    left_bound: int = 0
    right_bound: int | None = None
    in_point: int = 10
    out_point: int | None = None
    cursor: int = 20
    base_step: int = 5
    fps: float = 30.0
    speed: float = 1.0
    wrap_mode: str = "blue"
    loop_mode: str = "base-tip-base"
    session_name: str = "test_session"
    path: str = "/fake/video.mp4"
    session_path: str = "/fake/sessions/test_session.json"
    initial_in_point: int | None = None
    initial_out_point: int | None = None
    loop_anchor: float | None = None
    loop_paused: bool = False
    paused_loop_idx: int | None = None
    paused_loop_pos: int | None = None


@pytest.fixture
def make_state():
    def factory(**fields) -> VideoState:
        f = _StateFields(**fields)
        right_bound = f.total_frames - 1 if f.right_bound is None else f.right_bound
        out_point = f.total_frames - 10 if f.out_point is None else f.out_point
        return VideoState(
            cap=_FakeCapture(f.total_frames),
            path=f.path,
            fps=f.fps,
            window=FrameWindow(
                total_frames=f.total_frames,
                left_bound=f.left_bound,
                right_bound=right_bound,
                cursor=f.cursor,
                base_step=f.base_step,
            ),
            clip=ClipRange(
                start=f.in_point,
                end=out_point,
                anchor_in=f.in_point,
                anchor_out=out_point,
            ),
            frames={
                i: np.zeros((2, 2, 3), dtype=np.uint8)
                for i in range(f.left_bound, right_bound + 1)
            },
            loop=LoopCursor(
                anchor=time.monotonic() if f.loop_anchor is None else f.loop_anchor,
                speed=f.speed,
                paused=f.loop_paused,
                paused_idx=f.paused_loop_idx,
                paused_pos=f.paused_loop_pos,
            ),
            suggestions=Suggestions(
                initial_start=f.in_point if f.initial_in_point is None else f.initial_in_point,
                initial_end=out_point if f.initial_out_point is None else f.initial_out_point,
            ),
            session_name=f.session_name,
            session_path=f.session_path,
            loop_mode=read_loop_mode(f.loop_mode),
            wrap_mode=read_wrap_mode(f.wrap_mode),
            persist_session=_FakeAutosave(),
        )

    return factory
