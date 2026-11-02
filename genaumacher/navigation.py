from __future__ import annotations

from typing import TYPE_CHECKING

from .wrap_modes import WrapMode, wrap_bounds

if TYPE_CHECKING:
    from .state import VideoState


def toggle_wrap_mode(state: VideoState) -> None:
    state.wrap_mode = (
        WrapMode.OVER_IN_OUT if state.wrap_mode is WrapMode.OVER_BOUNDS else WrapMode.OVER_BOUNDS
    )
    if state.wrap_mode is WrapMode.OVER_IN_OUT:
        state.window.hold_within(*wrap_bounds(state))
    state.save_edit()


def move_cursor_left(state: VideoState) -> None:
    state.window.step_cursor_back(*wrap_bounds(state))
    state.save_edit()


def move_cursor_right(state: VideoState) -> None:
    state.window.step_cursor_forward(*wrap_bounds(state))
    state.save_edit()
