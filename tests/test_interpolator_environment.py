from __future__ import annotations

from pathlib import Path

import pytest

from genaumacher import app, interpolator_environment
from genaumacher.interpolator_environment import complaints, locate


@pytest.fixture
def checkout(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(interpolator_environment, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(interpolator_environment.shutil, "which", lambda _name: None)
    return tmp_path


def _fetched(root: Path, *, models: tuple[bytes, ...] = (b"weights", b"weights")) -> Path:
    exe = root / interpolator_environment.VENDORED_EXE
    exe.parent.mkdir(parents=True, exist_ok=True)
    exe.write_bytes(b"MZ")
    model_dir = exe.parent / interpolator_environment.MODEL_DIR_NAME
    model_dir.mkdir(exist_ok=True)
    for name, contents in zip(interpolator_environment.MODEL_FILES, models, strict=False):
        (model_dir / name).write_bytes(contents)
    return exe


class TestWhatTheCheckerSays:
    def test_a_checkout_that_never_fetched_is_told_how_to(self, checkout: Path):
        (said,) = complaints()

        assert "tools/fetch_rife.py" in said
        assert "geometric seam" in said

    def test_a_fetch_that_landed_no_model_names_what_is_missing(self, checkout: Path):
        _fetched(checkout, models=())

        (said,) = complaints()

        assert "flownet.bin" in said
        assert "flownet.param" in said
        assert "tools/fetch_rife.py" in said

    def test_a_weights_file_left_empty_is_not_a_fetch_that_finished(self, checkout: Path):
        _fetched(checkout, models=(b"weights", b""))

        (said,) = complaints()

        assert "flownet.param" in said
        assert "flownet.bin" not in said

    def test_a_finished_fetch_draws_no_complaint(self, checkout: Path):
        _fetched(checkout)

        assert complaints() == []


class TestWhichInterpolatorIsUsedAssertedExactlyAStringyWrongPathOncePassed:
    def test_the_copy_fetched_into_this_checkout_is_the_one_used(self, checkout: Path):
        exe = _fetched(checkout)

        assert locate() == (exe, exe.parent / interpolator_environment.MODEL_DIR_NAME)

    def test_the_fetched_copy_beats_one_installed_on_the_path(
        self, checkout: Path, monkeypatch
    ):
        exe = _fetched(checkout)
        elsewhere = _fetched(checkout / "installed")
        monkeypatch.setattr(
            interpolator_environment.shutil, "which", lambda _name: str(elsewhere))

        assert locate()[0] == exe

    def test_one_installed_on_the_path_is_used_when_this_checkout_has_none(
        self, checkout: Path, monkeypatch
    ):
        elsewhere = _fetched(checkout / "installed")
        monkeypatch.setattr(
            interpolator_environment.shutil, "which", lambda _name: str(elsewhere))

        assert locate()[0] == elsewhere

    def test_a_directory_where_the_executable_should_be_is_not_one(self, checkout: Path):
        (checkout / interpolator_environment.VENDORED_EXE).mkdir(parents=True)

        assert locate() is None

    def test_an_interpolator_with_no_weights_is_not_reached_for_at_all_it_would_start_fail_on_every_frame_and_fall_back_one_process_per_frame_later(
        self, checkout: Path
    ):
        _fetched(checkout, models=())

        assert locate() is None


class _RecordingLog:
    def __init__(self):
        self.warnings: list[str] = []

    def warning(self, message: str, *args) -> None:
        self.warnings.append(message % args)

    def info(self, message: str, *args) -> None:
        pass

    def exception(self, message: str) -> None:
        raise AssertionError(f"the launch crashed: {message}")


class TestWhereTheComplaintsGo:
    def test_the_launch_writes_what_the_checker_says_into_genaumachers_log_a_test_of_a_missing_interpolator_could_only_pass_on_the_gate_which_always_fetches_it(self, monkeypatch):
        logged = _RecordingLog()
        monkeypatch.setattr(app, "complaints", lambda: ["no interpolator here"])
        monkeypatch.setattr(app, "_claim_the_taskbar_identity_before_the_first_window", lambda preview: None)
        monkeypatch.setattr(app, "_name_this_process", lambda: None)
        monkeypatch.setattr(app, "_init_logger", lambda: logged)
        monkeypatch.setattr(app, "launch_state", lambda: None)

        assert app.main() == 0
        assert logged.warnings == ["Frame interpolator: no interpolator here"]
