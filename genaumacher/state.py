from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from .clip_range import ClipRange
from .frame_window import FrameWindow
from .loop_cursor import LoopCursor
from .loop_modes import LoopMode
from .session_persistence import (
    autosave_session as persist_session_state,
)
from .session_persistence import (
    current_payload as build_current_payload,
)
from .suggestions import Suggestions
from .wrap_modes import WrapMode, wrap_bounds


@dataclass
class VideoState:
    cap: cv2.VideoCapture
    path: str
    fps: float
    window: FrameWindow
    clip: ClipRange
    frames: dict[int, np.ndarray]
    loop: LoopCursor
    suggestions: Suggestions
    session_name: str
    session_path: str
    loop_mode: LoopMode = LoopMode.BASE_TIP_BASE
    wrap_mode: WrapMode = WrapMode.OVER_BOUNDS
    skip_normalize: bool = False
    vr: bool = False
    session_warning: str = ""
    last_saved_payload: dict[str, Any] | None = None
    render_rev: int = 0
    frame_signatures: dict[int, np.ndarray] = field(default_factory=dict)
    persist_session: Callable[[VideoState], None] = field(
        default=persist_session_state, repr=False
    )

    @property
    def total_frames(self) -> int:
        return self.window.total_frames

    @property
    def left_bound(self) -> int:
        return self.window.left_bound

    @property
    def right_bound(self) -> int:
        return self.window.right_bound

    @property
    def cursor(self) -> int:
        return self.window.cursor

    @property
    def base_step(self) -> int:
        return self.window.base_step

    @property
    def loaded_count(self) -> int:
        return self.window.count

    @property
    def in_point(self) -> int:
        return self.clip.start

    @property
    def out_point(self) -> int:
        return self.clip.end

    @property
    def suggested_in(self) -> int | None:
        return self.suggestions.suggested_in

    @property
    def suggested_out(self) -> int | None:
        return self.suggestions.suggested_out

    @property
    def speed(self) -> float:
        return self.loop.speed

    @property
    def loop_paused(self) -> bool:
        return self.loop.paused

    @property
    def paused_loop_pos(self) -> int | None:
        return self.loop.paused_pos

    def clamp_cursor(self) -> None:
        self.window.hold_within(*wrap_bounds(self))

    def reset_loop_anchor(self) -> None:
        self.loop.restart_at(time.monotonic())

    def bump_render(self) -> None:
        self.render_rev += 1

    def save_edit(self) -> None:
        self.bump_render()
        self.autosave_session()

    def current_payload(self) -> dict[str, Any]:
        return build_current_payload(self)

    def autosave_session(self) -> None:
        self.persist_session(self)
