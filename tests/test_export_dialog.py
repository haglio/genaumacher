"""Tests for genaumacher.gui.export_dialog — export progress dialog."""

from __future__ import annotations

import pytest

from genaumacher.gui.export_dialog import ExportDialog


@pytest.fixture
def dialog():
    return ExportDialog()


class TestConstruction:
    def test_has_three_progress_bars(self, dialog):
        assert dialog.clip_bar is not None
        assert dialog.normalize_bar is not None
        assert dialog.audio_bar is not None

    def test_bars_start_at_zero(self, dialog):
        assert dialog.clip_bar.value() == 0
        assert dialog.normalize_bar.value() == 0
        assert dialog.audio_bar.value() == 0

    def test_each_bar_is_labeled_with_the_step_it_shows(self, dialog):
        layout = dialog.layout()

        def label_above(bar):
            return layout.itemAt(layout.indexOf(bar) - 1).widget().text()

        assert [label_above(bar) for bar in (dialog.clip_bar, dialog.normalize_bar, dialog.audio_bar)] == [
            "Raw clip:", "Normalize:", "Audio extract:",
        ]


class TestProgressUpdates:
    def test_set_clip_progress(self, dialog):
        dialog.set_clip_progress(0.5)
        assert dialog.clip_bar.value() == 50

    def test_set_normalize_progress(self, dialog):
        dialog.set_normalize_progress(0.75)
        assert dialog.normalize_bar.value() == 75

    def test_set_audio_progress(self, dialog):
        dialog.set_audio_progress(1.0)
        assert dialog.audio_bar.value() == 100


class TestStatusUpdates:
    def test_set_stage(self, dialog):
        dialog.set_stage("extracting audio")
        assert "audio" in dialog.stage_label.text().lower()

    def test_set_error(self, dialog):
        dialog.set_error("something broke")
        assert "broke" in dialog.error_label.text()

    def test_set_done(self, dialog):
        dialog.set_done(True)
        assert dialog.close_btn.isEnabled()
