"""What one run of normalize was asked for, and the defaults it falls back on."""
from __future__ import annotations

from dataclasses import dataclass

from .loop_modes import LoopMode


@dataclass(frozen=True)
class NormalizeOptions:
    input: str
    output: str
    loop_mode: LoopMode = LoopMode.BASE_TIP_BASE
    bridge_ms: float = 80.0
    bridge_frames: int | None = None
    mode: str = "register"
    keep_length: bool = True
    symmetric_blend: int = 0
    seam_ms: float = 250.0
    copy_audio: bool = False
    crf: int = 12
    preset: str = "slow"
    pix_fmt: str = "yuv420p"
    max_mb: float = 1.0
