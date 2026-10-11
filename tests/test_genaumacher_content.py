"""The content overlay: this machine's own file when it has one, else the committed example."""
from __future__ import annotations

import json
from pathlib import Path

from genaumacher.content import load_content

_OURS = "D:/example-suite/main_player_status.txt"
_EXAMPLES = "C:/path/to/main_player_status.txt"


def _overlay(tmp_path: Path) -> tuple[Path, Path]:
    """A local overlay and the committed example beside it, both fabricated."""
    local = tmp_path / "content.local.json"
    local.write_text(json.dumps({"main_player_status_file": _OURS}), encoding="utf-8")
    example = tmp_path / "content.example.json"
    example.write_text(json.dumps({"main_player_status_file": _EXAMPLES}), encoding="utf-8")
    return local, example


class TestWhichFileAnswers:
    def test_the_local_overlay_answers_when_there_is_one(self, tmp_path: Path):
        local, example = _overlay(tmp_path)

        assert load_content(local, example)["main_player_status_file"] == _OURS

    def test_the_committed_example_answers_when_there_is_not(self, tmp_path: Path):
        _local, example = _overlay(tmp_path)

        assert load_content(tmp_path / "absent.json", example)["main_player_status_file"] == _EXAMPLES

    def test_a_change_to_the_file_is_read_by_the_next_caller(self, tmp_path: Path):
        local, example = _overlay(tmp_path)
        load_content(local, example)

        local.write_text(json.dumps({"main_player_status_file": "E:/other-suite/status.txt"}), encoding="utf-8")

        assert load_content(local, example)["main_player_status_file"] == "E:/other-suite/status.txt"
