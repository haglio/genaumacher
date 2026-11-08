from __future__ import annotations

from unittest.mock import patch

import pytest

from genaumacher.export_pipeline import run_export
from genaumacher.paths import RAW_CLIPS_DIR, audio_dir, flicks_dir, vr_flicks_dir
from genaumacher.sidecar import record_provenance
from tests.stamps import (
    METHOD_KEY_AS_EVERY_FILE_ON_DISK_ALREADY_HOLDS_IT,
    METHOD_VERSION_KEY_AS_EVERY_FILE_ON_DISK_ALREADY_HOLDS_IT,
)

pytestmark = pytest.mark.usefixtures("library")


class _Watcher:
    def __init__(self) -> None:
        self.stages: list[str] = []
        self.clips: list[float] = []
        self.normalizes: list[float] = []
        self.audios: list[float] = []

    def stage(self, text: str) -> None:
        self.stages.append(text)

    def clip(self, fraction: float) -> None:
        self.clips.append(fraction)

    def normalize(self, fraction: float) -> None:
        self.normalizes.append(fraction)

    def audio(self, fraction: float) -> None:
        self.audios.append(fraction)


class _Step:
    def __init__(self, *, stage: str, reports: str, ok: bool = True, detail: str = ""):
        self.stage_text = stage
        self.reports = reports
        self.ok = ok
        self.detail = detail
        self.calls: list[tuple] = []

    def __call__(self, *args):
        self.calls.append(args)
        progress = args[-1]
        progress.stage(self.stage_text)
        getattr(progress, self.reports)(1.0)
        return self.ok, self.detail

    @property
    def called(self) -> bool:
        return bool(self.calls)


@pytest.fixture
def state(make_state):
    return make_state(
        path="C:/fake/video.mp4", session_path="C:/fake/session.json",
        total_frames=300, right_bound=299, in_point=10, out_point=50,
        cursor=10, base_step=1,
    )


@pytest.fixture
def steps():
    stubs = {
        "raw": _Step(stage="clipping", reports="clip", detail="raw.mp4"),
        "normalize": _Step(stage="normalizing", reports="normalize", detail="clip.mp4"),
        "audio": _Step(stage="pulling audio", reports="audio", detail="audio.mp3"),
    }
    with patch("genaumacher.export_steps.export_raw_clip", stubs["raw"]), \
         patch("genaumacher.export_steps.run_normalize", stubs["normalize"]), \
         patch("genaumacher.export_steps.export_full_audio_mp3", stubs["audio"]):
        yield stubs


@pytest.fixture
def watcher():
    return _Watcher()


class TestWhatEachStepIsGiven:
    def test_the_raw_clip_step_gets_the_state_an_output_path_and_the_watcher(
        self, state, steps, watcher
    ):
        run_export(state, watcher)

        clip_state, out_path, progress = steps["raw"].calls[0]
        assert clip_state is state
        assert out_path.parent == RAW_CLIPS_DIR
        assert progress is watcher

    def test_the_normalize_step_gets_the_raw_input_and_the_clip_output(
        self, state, steps, watcher
    ):
        run_export(state, watcher)

        normalize_state, raw_in, clip_out, progress = steps["normalize"].calls[0]
        assert normalize_state is state
        assert raw_in == steps["raw"].calls[0][1]
        assert clip_out.parent == flicks_dir()
        assert progress is watcher

    def test_the_audio_step_writes_beside_the_clip(self, state, steps, watcher):
        run_export(state, watcher)

        _audio_state, audio_out, _progress = steps["audio"].calls[0]
        assert audio_out.parent == audio_dir()
        assert audio_out.suffix == ".mp3"

    def test_all_three_outputs_take_the_session_name(self, state, steps, watcher):
        state.session_name = "second pass"

        run_export(state, watcher)

        assert steps["raw"].calls[0][1].stem == "second pass"
        assert steps["normalize"].calls[0][2].stem == "second pass"
        assert steps["audio"].calls[0][1].stem == "second pass"

    def test_a_session_name_that_cannot_be_a_filename_is_sanitized(
        self, state, steps, watcher
    ):
        state.session_name = "take 1: second pass"

        run_export(state, watcher)

        assert steps["raw"].calls[0][1].stem == "take 1_ second pass"


class TestWhatItReports:
    def test_it_starts_every_bar_at_zero_and_names_each_step(
        self, state, steps, watcher
    ):
        run_export(state, watcher)

        assert watcher.stages == [
            "preparing export", "clipping", "normalizing", "pulling audio",
        ]
        assert watcher.clips == [0.0, 1.0]
        assert watcher.normalizes == [0.0, 1.0]
        assert watcher.audios == [0.0, 1.0]

    def test_a_finished_run_names_the_clip_it_wrote(self, state, steps, watcher):
        ok, message = run_export(state, watcher)

        assert ok is True
        assert str(flicks_dir()) in message


class TestFailures:
    def test_a_failed_clip_stops_the_run_and_reports_why(self, state, steps, watcher):
        steps["raw"].ok = False
        steps["raw"].detail = "ffmpeg not found on PATH"

        assert run_export(state, watcher) == (False, "ffmpeg not found on PATH")
        assert not steps["normalize"].called
        assert not steps["audio"].called

    def test_a_failed_normalize_stops_before_the_audio(self, state, steps, watcher):
        steps["normalize"].ok = False
        steps["normalize"].detail = "the bridge is too long"

        assert run_export(state, watcher) == (False, "the bridge is too long")
        assert not steps["audio"].called

    def test_a_failed_audio_pull_is_reported(self, state, steps, watcher):
        steps["audio"].ok = False
        steps["audio"].detail = "no audio stream"

        assert run_export(state, watcher) == (False, "no audio stream")

    def test_a_step_that_raises_is_reported_rather_than_lost(self, state, steps, watcher):
        def explode(*_args):
            raise RuntimeError("the disk went away")

        with patch("genaumacher.export_steps.export_raw_clip", explode):
            assert run_export(state, watcher) == (False, "the disk went away")


class TestVrExportPath:
    def test_a_non_vr_clip_lands_in_the_clips_folder(self, state, steps, watcher):
        state.vr = False

        run_export(state, watcher)

        assert steps["normalize"].calls[0][2].parent == flicks_dir()

    def test_a_vr_clip_lands_in_the_vr_clips_folder(self, state, steps, watcher):
        state.vr = True

        run_export(state, watcher)

        assert steps["normalize"].calls[0][2].parent == vr_flicks_dir()


class TestALoopedClipsRecord:
    def test_the_export_leaves_the_stamp_normalizing_wrote_its_code_may_be_newer_than_the_windows(
        self, state, steps, watcher, recorded_cut
    ):
        def normalize(_state, _raw_path, clip_path, _progress):
            record_provenance(clip_path, method="clip_postprocess", method_version="3")
            return True, str(clip_path)

        with patch("genaumacher.export_steps.run_normalize", normalize):
            run_export(state, watcher)

        recorded = recorded_cut(state.session_name)
        assert (recorded[METHOD_KEY_AS_EVERY_FILE_ON_DISK_ALREADY_HOLDS_IT], recorded[METHOD_VERSION_KEY_AS_EVERY_FILE_ON_DISK_ALREADY_HOLDS_IT]) == ("clip_postprocess", "3")


class TestSkipNormalize:
    @pytest.fixture(autouse=True)
    def _skipping(self, state):
        state.skip_normalize = True

    def test_the_normalize_step_never_runs_a_whole_video_is_already_a_loop(self, state, steps, watcher):
        run_export(state, watcher)

        assert not steps["normalize"].called

    def test_the_clip_is_written_straight_into_the_clips_folder(
        self, state, steps, watcher
    ):
        run_export(state, watcher)

        assert steps["raw"].calls[0][1].parent == flicks_dir()

    def test_the_skipped_stage_still_reports_itself_finished(
        self, state, steps, watcher
    ):
        run_export(state, watcher)

        assert watcher.normalizes == [0.0, 1.0]

    def test_the_audio_is_still_pulled(self, state, steps, watcher):
        run_export(state, watcher)

        assert steps["audio"].called

    def test_the_clip_says_genaumacher_made_it_without_normalizing_so_a_sweep_for_clips_made_before_a_change_passes_it_by(
        self, state, steps, watcher, recorded_cut
    ):
        run_export(state, watcher)

        recorded = recorded_cut(state.session_name)
        assert (recorded["app"], recorded[METHOD_KEY_AS_EVERY_FILE_ON_DISK_ALREADY_HOLDS_IT], recorded[METHOD_VERSION_KEY_AS_EVERY_FILE_ON_DISK_ALREADY_HOLDS_IT]) == (
            "genaumacher", None, None,
        )
