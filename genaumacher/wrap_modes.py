from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state import VideoState


class WrapMode(StrEnum):
    OVER_BOUNDS = "blue"
    OVER_IN_OUT = "yellow"


def read_wrap_mode(raw: object) -> WrapMode:
    try:
        return WrapMode(raw)
    except ValueError:
        return WrapMode.OVER_BOUNDS


def wrap_bounds(state: VideoState) -> tuple[int, int]:
    if state.wrap_mode is WrapMode.OVER_BOUNDS:
        return state.left_bound, state.right_bound
    return state.in_point, state.out_point
