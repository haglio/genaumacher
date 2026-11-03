from __future__ import annotations

from dataclasses import dataclass

from .loop_modes import LoopMode


@dataclass(frozen=True)
class LoadSession:
    session_json: str


@dataclass(frozen=True)
class NewSession:
    video_file: str
    session_name: str
    timestamp: str
    seconds: float
    loop_mode: LoopMode = LoopMode.BASE_TIP_BASE
    vr: bool = False


@dataclass(frozen=True)
class ClipWholeVideo:
    video_file: str


LaunchChoice = LoadSession | NewSession | ClipWholeVideo
