from __future__ import annotations

import time
from pathlib import Path

import cv2
from PySide6.QtWidgets import QDialog

from .clip_range import ClipRange
from .create_session import SessionAsk, create_session, ffprobe_video_metadata
from .frame_window import FrameWindow
from .gui.launcher_dialog import LauncherDialog
from .launch_choice import ClipWholeVideo, LaunchChoice, LoadSession, NewSession
from .loop_cursor import LoopCursor
from .main_funestra_prefill import detect_main_funestra_session_prefill
from .paths import LAST_SESSION_FILE, SESSIONS_DIR, ensure_runtime_dirs, sanitize_name
from .session_persistence import name_the_videos_by_id, read_json, remember_last_session
from .state import VideoState
from .state_factory import load_video_state
from .suggestions import Suggestions
from .timecode import parse_timestamp


def _load_state_from_session_file(session_path: Path) -> VideoState:
    payload = read_json(session_path)
    state = load_video_state(payload, session_path.stem)
    state.session_path = str(session_path)
    return state


def build_clip_whole_state(video_file: str) -> VideoState:
    fps, total_frames = ffprobe_video_metadata(video_file)
    session_name = sanitize_name(Path(video_file).stem)
    end_idx = total_frames - 2
    cap = cv2.VideoCapture(video_file)
    return VideoState(
        cap=cap,
        path=video_file,
        fps=fps,
        window=FrameWindow(
            total_frames=total_frames,
            left_bound=0,
            right_bound=end_idx,
            cursor=0,
            base_step=max(1, round(fps)),
        ),
        clip=ClipRange(start=0, end=end_idx),
        frames={},
        loop=LoopCursor(anchor=time.monotonic()),
        suggestions=Suggestions(),
        session_name=session_name,
        session_path=str(SESSIONS_DIR / f"{session_name}.json"),
        skip_normalize=True,
    )


def build_state(choice: LoadSession | NewSession) -> VideoState:
    if isinstance(choice, LoadSession):
        session_path = Path(choice.session_json)
    else:
        session_path = create_session(SessionAsk(
            choice.video_file,
            parse_timestamp(choice.timestamp),
            session_name=choice.session_name,
            seconds=choice.seconds,
            loop_mode=choice.loop_mode,
            vr=choice.vr,
        ))
    state = _load_state_from_session_file(session_path)
    remember_last_session(state.session_path)
    return state


def _run_clip_whole_export(video_file: str) -> None:
    # Qt: genaumacher.app imports this module before it knows a window is wanted.
    from .gui.export_dialog import ExportDialog  # noqa: PLC0415
    from .gui.export_worker import connect_export  # noqa: PLC0415

    state = build_clip_whole_state(video_file)
    dialog = ExportDialog()
    dialog.setWindowTitle("Exporting whole video")
    worker = connect_export(state, dialog)
    worker.start()
    dialog.exec()
    state.cap.release()


def launch_state() -> VideoState | None:
    ensure_runtime_dirs()
    name_the_videos_by_id(SESSIONS_DIR)
    last_session = LAST_SESSION_FILE.read_text(encoding="utf-8").strip() if LAST_SESSION_FILE.exists() else ""
    dialog = LauncherDialog(last_session=last_session)

    prefill = detect_main_funestra_session_prefill()
    if prefill:
        dialog.prefill(prefill.session_name, prefill.video_file, prefill.timestamp)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    choice: LaunchChoice = dialog.build_result()
    if isinstance(choice, ClipWholeVideo):
        _run_clip_whole_export(choice.video_file)
        return None
    return build_state(choice)
