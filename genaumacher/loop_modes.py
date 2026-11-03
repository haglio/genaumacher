from __future__ import annotations

from enum import StrEnum


class LoopMode(StrEnum):
    BASE_TIP_BASE = "base-tip-base"
    TIP_BASE_TIP = "tip-base-tip"
    BASE_TIP = "base-tip"
    TIP_BASE = "tip-base"


LOOP_MODES = tuple(LoopMode)


def read_loop_mode(raw: object) -> LoopMode:
    try:
        return LoopMode(raw)
    except ValueError:
        return LoopMode.BASE_TIP_BASE
