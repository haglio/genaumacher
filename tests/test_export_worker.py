from __future__ import annotations

from unittest.mock import patch

import pytest

from genaumacher.gui.export_dialog import ExportDialog
from genaumacher.gui.export_worker import ExportWorker, connect_export


@pytest.fixture
def state(make_state):
    return make_state(
        path="C:/fake/video.mp4", session_path="C:/fake/session.json",
        total_frames=300, right_bound=299, in_point=10, out_point=50,
        cursor=10, base_step=1,
    )


class _Step:
    def __init__(self, *, stage: str, reports: str):
        self.stage_text = stage
        self.reports = reports

    def __call__(self, *args):
        progress = args[-1]
        progress.stage(self.stage_text)
        getattr(progress, self.reports)(1.0)
        return True, "written.mp4"


@pytest.fixture
def steps(library):
    with patch("genaumacher.export_steps.export_raw_clip",
               _Step(stage="clipping", reports="clip")), \
         patch("genaumacher.export_steps.run_normalize",
               _Step(stage="normalizing", reports="normalize")), \
         patch("genaumacher.export_steps.export_full_audio_mp3",
               _Step(stage="pulling audio", reports="audio")):
        yield


def _recorded(worker: ExportWorker) -> dict[str, list]:
    seen: dict[str, list] = {}
    for name in ("stage_changed", "clip_progress", "normalize_progress",
                 "audio_progress", "export_finished"):
        seen[name] = []
        getattr(worker, name).connect(
            lambda *args, _name=name: seen[_name].append(args if len(args) > 1 else args[0])
        )
    return seen


class TestSignals:
    def test_a_run_emits_every_signal_the_worker_declares_run_in_this_thread_so_qt_delivers_them_at_once_not_queued(self, state, steps):
        worker = ExportWorker(state)
        seen = _recorded(worker)

        worker.run()

        assert seen["stage_changed"] == [
            "preparing export", "clipping", "normalizing", "pulling audio",
        ]
        assert seen["clip_progress"] == [0.0, 1.0]
        assert seen["normalize_progress"] == [0.0, 1.0]
        assert seen["audio_progress"] == [0.0, 1.0]
        assert len(seen["export_finished"]) == 1


class TestWhatTheRunAnswers:
    @pytest.mark.parametrize("answer", [
        (True, "Done: clip.mp4"),
        (False, "ffmpeg not found on PATH"),
    ])
    def test_the_finished_signal_carries_what_the_export_answered(self, state, answer):
        worker = ExportWorker(state)
        seen = _recorded(worker)

        with patch("genaumacher.gui.export_worker.run_export", return_value=answer) as export:
            worker.run()

        assert seen["export_finished"] == [answer]
        assert export.call_args.args == (state, worker)


class TestConnectExport:
    def test_every_signal_the_worker_emits_reaches_the_dialog_one_wiring_the_caller_holds_and_starts_a_qthread_whose_last_reference_goes_dies_mid_export(self, state, steps):
        dialog = ExportDialog()
        worker = connect_export(state, dialog)
        assert not worker.isRunning()

        worker.run()

        assert dialog.stage_label.text() == "Export complete."
