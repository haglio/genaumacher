from __future__ import annotations

import ast
import inspect
import textwrap
from pathlib import Path

from app_support.siblings import primary_checkout_of

from genaumacher import main_funestra_prefill
from genaumacher.create_session import SessionAsk, build_session_payload
from genaumacher.main_funestra_prefill import SessionPrefill, detect_main_funestra_session_prefill
from genaumacher.paths import PROJECT_DIR

_PLAYING = {
    "video": "S:/library/main/alpha clip.mp4",
    "position_ms": "72500",
    "duration_ms": "300000",
    "has_funscript": "1",
    "funscript_resting": "0",
    "state": "normal",
}


def _status(tmp_path: Path, **overrides) -> Path:
    fields = {**_PLAYING, **overrides}
    path = tmp_path / "main_player_status.txt"
    path.write_text(
        "".join(f"{k}={v}\n" for k, v in fields.items()), encoding="utf-8"
    )
    return path


class TestWhatItReads:
    def test_it_takes_the_video_the_main_funestra_is_playing(self, tmp_path: Path):
        prefill = detect_main_funestra_session_prefill(_status(tmp_path))

        assert prefill.video_file == "S:/library/main/alpha clip.mp4"

    def test_the_timestamp_is_the_playhead(self, tmp_path: Path):
        prefill = detect_main_funestra_session_prefill(_status(tmp_path))

        assert prefill.timestamp == "00:01:12.500"

    def test_the_session_is_named_the_way_the_push_side_names_it(self, tmp_path: Path):
        prefill = detect_main_funestra_session_prefill(_status(tmp_path))
        pushed = build_session_payload(SessionAsk(prefill.video_file, 0.0), fps=30.0, total_frames=100)

        assert prefill.session_name == pushed["session_name"]

class TestWhenThereIsNothingToPrefill:
    def test_a_machine_that_has_not_named_the_status_file_under_fun_times_own_name_main_player_status_file_gets_a_blank_launcher(self, monkeypatch):
        monkeypatch.setattr(main_funestra_prefill, "main_funestra_status_file", lambda: None)

        assert detect_main_funestra_session_prefill() is None

    def test_the_main_funestra_is_not_running_so_the_file_is_not_there(self, tmp_path: Path):
        assert detect_main_funestra_session_prefill(tmp_path / "main_player_status.txt") is None

    def test_the_main_funestra_is_running_with_nothing_playing(self, tmp_path: Path):
        assert detect_main_funestra_session_prefill(_status(tmp_path, video="")) is None

    def test_a_status_file_caught_mid_write(self, tmp_path: Path):
        path = tmp_path / "main_player_status.txt"
        path.write_text("vid", encoding="utf-8")

        assert detect_main_funestra_session_prefill(path) is None

    def test_a_blank_playhead_starts_at_zero(self, tmp_path: Path):
        prefill = detect_main_funestra_session_prefill(_status(tmp_path, position_ms="  "))

        assert prefill.timestamp == "00:00:00.000"

    def test_a_playhead_that_is_not_a_number_costs_the_timestamp_and_not_the_video(self, tmp_path: Path):
        prefill = detect_main_funestra_session_prefill(_status(tmp_path, position_ms="soon"))

        assert prefill.timestamp == "00:00:00.000"

    def test_a_status_file_of_undecodable_bytes(self, tmp_path: Path):
        path = tmp_path / "main_player_status.txt"
        path.write_bytes(b"video=\xff\xfe")

        assert detect_main_funestra_session_prefill(path) is None

    def test_a_file_that_cannot_be_read(self, tmp_path: Path):
        assert detect_main_funestra_session_prefill(tmp_path) is None


class TestTheContractWithTheMainFunestraGenaumachersWholeLinkToTheOtherApps:
    _THE_OLD_FOLDER_NAME_ON_A_MACHINE_THAT_HAS_NOT_MOVED_IT = "player_core"

    @staticmethod
    def _status_sources_beside_the_primary_checkout_a_worktrees_neighbors_are_worktrees() -> list[Path]:
        siblings = primary_checkout_of(PROJECT_DIR).parent
        sources = (siblings / "funestra" / "funestra" / "status.py",
                   siblings / TestTheContractWithTheMainFunestraGenaumachersWholeLinkToTheOtherApps._THE_OLD_FOLDER_NAME_ON_A_MACHINE_THAT_HAS_NOT_MOVED_IT / "funestra" / "status.py",
                   siblings / "fun_time" / "main_funestra" / "status.py")
        return [source for source in sources if source.is_file()]

    @staticmethod
    def _keys_genaumacher_reads() -> set[str]:
        source = inspect.getsource(main_funestra_prefill.detect_main_funestra_session_prefill)
        tree = ast.parse(textwrap.dedent(source))
        return {
            node.args[0].value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        }

    @staticmethod
    def _keys_the_main_funestra_publishes(source: Path) -> set[str]:
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "status_fields":
                return {
                    key.value
                    for inner in ast.walk(node)
                    if isinstance(inner, ast.Dict)
                    for key in inner.keys
                    if isinstance(key, ast.Constant) and isinstance(key.value, str)
                }
        return set()

    def test_the_main_funestra_still_publishes_both_fields_genaumacher_reads_the_same_two_fun_times_semicolon_reads_to_start_a_session(self):
        wanted = self._keys_genaumacher_reads()
        sources = self._status_sources_beside_the_primary_checkout_a_worktrees_neighbors_are_worktrees()
        published = set().union(*map(self._keys_the_main_funestra_publishes, sources)) if sources else wanted

        uncovered = (f"the Main Funestra publishes {sorted(published)}, which no longer covers "
                     f"{sorted(wanted)} -- the launcher would prefill nothing")
        assert wanted, uncovered
        assert wanted <= published, uncovered

    def test_the_prefill_reads_a_payload_the_main_funestra_itself_produced(self, tmp_path: Path):
        sources = self._status_sources_beside_the_primary_checkout_a_worktrees_neighbors_are_worktrees()
        keys = set().union(*map(self._keys_the_main_funestra_publishes, sources)) if sources else set(_PLAYING)
        payload = {key: _PLAYING.get(key, "0") for key in sorted(keys)}
        payload["video"] = "S:/library/main/beta clip.mp4"
        payload["position_ms"] = "1000"
        path = tmp_path / "main_player_status.txt"
        path.write_text("".join(f"{k}={v}\n" for k, v in payload.items()), encoding="utf-8")

        prefill = detect_main_funestra_session_prefill(path)

        assert prefill == SessionPrefill(
            video_file="S:/library/main/beta clip.mp4",
            session_name="beta clip",
            timestamp="00:00:01.000",
        )
