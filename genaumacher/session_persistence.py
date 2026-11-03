from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app_support.file_channel import write_whole

from .loop_modes import LoopMode
from .paths import LAST_SESSION_FILE
from .wrap_modes import WrapMode

logger = logging.getLogger(__name__)


def safe_atomic_write_json(path: Path, payload: dict[str, Any]) -> tuple[bool, str]:
    if not path.parent.is_dir():
        return False, f"{path.parent} is not there, so {path.name} was not saved"
    try:
        write_whole(path, json.dumps(payload, indent=2) + "\n")
    except (OSError, TypeError, ValueError) as exc:
        return False, str(exc)
    return True, ""


def remember_last_session(session_path: Path | str) -> None:
    try:
        LAST_SESSION_FILE.write_text(str(session_path), encoding="utf-8")
    except OSError:
        logger.warning("Could not update %s", LAST_SESSION_FILE, exc_info=True)


def read_json(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


SESSION_FORMAT_VERSION = 1


def session_payload(
    *,
    session_name: str,
    video_path: str,
    fps: float,
    total_frames: int,
    left_bound: int,
    right_bound: int,
    in_point: int,
    out_point: int,
    cursor: int,
    seconds_per_step: float,
    loop_mode: LoopMode,
    wrap_mode: WrapMode,
    speed: float,
    vr: bool,
) -> dict:
    return {
        "version": SESSION_FORMAT_VERSION,
        "session_name": session_name,
        "video_path": video_path,
        "fps": fps,
        "total_frames": total_frames,
        "loaded_start": left_bound,
        "loaded_end": right_bound,
        "active_start": in_point,
        "active_end": out_point,
        "current": cursor,
        "seconds_per_step": seconds_per_step,
        "loop_mode": loop_mode,
        "wrap_mode": wrap_mode,
        "speed": speed,
        "vr": vr,
    }


def current_payload(state) -> dict:
    return session_payload(
        session_name=state.session_name,
        video_path=state.path,
        fps=state.fps,
        total_frames=state.total_frames,
        left_bound=state.left_bound,
        right_bound=state.right_bound,
        in_point=state.in_point,
        out_point=state.out_point,
        cursor=state.cursor,
        seconds_per_step=state.base_step / state.fps,
        loop_mode=state.loop_mode,
        wrap_mode=state.wrap_mode,
        speed=state.speed,
        vr=state.vr,
    )


def autosave_session(state) -> None:
    payload = current_payload(state)
    ok, detail = safe_atomic_write_json(Path(state.session_path), payload)
    if ok:
        state.session_warning = ""
        state.last_saved_payload = payload
        remember_last_session(state.session_path)
    else:
        state.session_warning = f"Autosave failed: {detail}"
