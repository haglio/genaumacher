from __future__ import annotations

import json
from types import SimpleNamespace

from app_support import video_ids

from genaumacher.session_persistence import current_payload, name_the_videos_by_id


def _video(library, name="scene one.mp4"):
    video = library / "videos" / "videos" / "2D" / name
    video.parent.mkdir(parents=True, exist_ok=True)
    video.write_bytes(b"")
    return video


def _state(path):
    return SimpleNamespace(
        session_name="demo", path=str(path), fps=30.0, total_frames=120, left_bound=10,
        right_bound=40, in_point=12, out_point=30, cursor=18, base_step=30,
        loop_mode="base-tip-base", wrap_mode="blue", speed=1.0, vr=False)


def test_a_session_of_a_library_video_names_it_by_the_id_its_record_carries(library):
    video = _video(library)

    payload = current_payload(_state(video))

    assert "video_path" not in payload
    assert payload["video_id"] == video_ids.id_of(video_ids.record_of(video))


def test_a_saved_session_of_a_library_video_is_moved_to_its_id_and_the_rest_kept(library, tmp_path):
    video = _video(library)
    outside = tmp_path / "downloads" / "scene two.mp4"
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    (sessions / "one.json").write_text(json.dumps(
        {"version": 1, "session_name": "one", "video_path": str(video), "fps": 30.0}),
        encoding="utf-8")
    (sessions / "two.json").write_text(json.dumps(
        {"version": 1, "session_name": "two", "video_path": str(outside)}), encoding="utf-8")

    name_the_videos_by_id(sessions)

    assert json.loads((sessions / "one.json").read_text(encoding="utf-8")) == {
        "version": 2, "session_name": "one", "fps": 30.0,
        "video_id": video_ids.id_of(video_ids.record_of(video))}
    assert json.loads((sessions / "two.json").read_text(encoding="utf-8"))["video_path"] == str(outside)
