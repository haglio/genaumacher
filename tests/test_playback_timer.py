from __future__ import annotations

import pytest
from PyQt6.QtWidgets import QApplication

from genaumacher.gui.playback_timer import PlaybackTimer


@pytest.fixture
def timer():
    return PlaybackTimer()


class TestTicking:
    def test_a_new_timer_does_not_tick(self, timer, ticked_within):
        assert ticked_within(timer.tick, 100) is False

    def test_it_ticks_once_started(self, timer, ticked_within):
        timer.start()
        try:
            assert ticked_within(timer.tick, 2000) is True
        finally:
            timer.stop()

    def test_it_stops_ticking_when_stopped(self, timer, ticked_within):
        timer.start()
        assert ticked_within(timer.tick, 2000) is True

        timer.stop()
        QApplication.processEvents()

        assert ticked_within(timer.tick, 100) is False

    def test_it_ticks_fast_enough_for_smooth_playback(self, timer):
        assert 0 < timer.interval_ms <= 20
