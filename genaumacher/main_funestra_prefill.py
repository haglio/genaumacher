from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from app_support.file_channel import read_key_values

from .content import load_content
from .paths import sanitize_name
from .timecode import format_seconds


@dataclass(frozen=True)
class SessionPrefill:
    video_file: str
    session_name: str
    timestamp: str


def main_funestra_status_file() -> Path | None:
    raw = load_content().get("main_player_status_file")
    return Path(raw) if raw else None


def _published_values(status_file: Path) -> dict[str, str]:
    try:
        return read_key_values(status_file)
    except (OSError, UnicodeDecodeError):
        return {}


def detect_main_funestra_session_prefill(status_file: Path | None = None) -> SessionPrefill | None:
    status_file = main_funestra_status_file() if status_file is None else status_file
    if status_file is None:
        return None

    values = _published_values(status_file)
    video = values.get("video", "").strip()
    if not video:
        return None

    try:
        position_seconds = int(values.get("position_ms", "0").strip() or 0) / 1000
    except ValueError:
        position_seconds = 0.0

    name = _named_as_the_main_funestra_wrote_it_on_windows(video)
    return SessionPrefill(
        video_file=video,
        session_name=sanitize_name(name),
        timestamp=format_seconds(position_seconds),
    )


def _named_as_the_main_funestra_wrote_it_on_windows(video: str) -> str:
    return PureWindowsPath(video).stem
