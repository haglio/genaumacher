from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication
from shared_ui.colors import BG_SECONDARY, family_palette
from shared_ui.palette import PREVIEW_INK
from shared_ui.preview import Preview

from genaumacher.gui.app import GenaumacherApp
from genaumacher.loop_modes import LoopMode
from genaumacher.playback import change_speed, toggle_loop_pause
from genaumacher.timecode import format_seconds
from genaumacher.wrap_modes import WrapMode
from tests.qt_events import drain_a_tick_already_on_its_way


@pytest.fixture
def mock_state():
    state = MagicMock()
    state.session_name = "test_session"
    state.path = "/video.mp4"
    state.fps = 30.0
    state.total_frames = 300
    state.left_bound = 0
    state.right_bound = 100
    state.in_point = 20
    state.out_point = 80
    state.cursor = 50
    state.loop_mode = LoopMode.BASE_TIP_BASE
    state.wrap_mode = WrapMode.OVER_BOUNDS
    state.speed = 1.0
    state.loop_paused = False
    state.suggested_in = None
    state.suggested_out = None
    state.session_warning = ""
    state.render_rev = 0
    return state


class TestConstruction:
    def test_creates_main_window(self, mock_state):
        app = GenaumacherApp(mock_state)
        assert app.window is not None

    def test_creates_playback_timer(self, mock_state):
        app = GenaumacherApp(mock_state)
        assert app.playback_timer is not None

    def test_the_window_is_built_around_the_state_it_was_given(self, mock_state):
        app = GenaumacherApp(mock_state)
        assert app.window.session_label.text() == mock_state.session_name

    def test_the_application_wears_the_familys_palette_under_its_sheet_what_the_sheet_leaves_unpainted_the_selection_first_comes_from_it(self, mock_state):
        palette_before = QApplication.instance().palette()
        try:
            GenaumacherApp(mock_state)

            assert QApplication.instance().palette().highlight().color() ==                 family_palette(QPalette()).highlight().color()
        finally:
            QApplication.instance().setPalette(palette_before)

    def test_sets_application_icon(self, mock_state):
        GenaumacherApp(mock_state)

        assert not QApplication.instance().windowIcon().isNull()

    def test_a_preview_wears_its_letter_in_the_preview_ink_and_is_titled_for_its_feature(self, mock_state):
        app = GenaumacherApp(mock_state, preview=Preview(feature="the new loop"))

        top_bar = QApplication.instance().windowIcon().pixmap(32, 32).toImage().pixelColor(16, 6)
        assert (top_bar.red(), top_bar.green(), top_bar.blue()) == PREVIEW_INK
        assert app.window.windowTitle() == "Genaumacher — preview of the new loop"


_TICK_STATE = {
    "total_frames": 100, "left_bound": 10, "right_bound": 60,
    "in_point": 20, "out_point": 40, "cursor": 33, "base_step": 5,
    "fps": 25.0,
}


@pytest.fixture
def live_app(make_state):
    state = make_state(**_TICK_STATE)
    for idx in state.frames:
        state.frames[idx] = np.full((8, 8, 3), 200, dtype=np.uint8)
    app = GenaumacherApp(state)
    app.window.resize(1520, 960)
    yield app
    app.window.close()


def _is_blank(pane, rendered) -> bool:
    image = rendered(pane)
    return all(
        image.pixelColor(x, y).name() == BG_SECONDARY.name()
        for x in range(0, image.width(), 7)
        for y in range(0, image.height(), 7)
    )


class TestOnTick:
    def test_it_hands_the_scrubber_the_state_it_is_looking_at(self, live_app):
        state = live_app._state

        live_app._push_the_state_to_the_window_which_alone_knows_its_widgets()

        scrubber = live_app.window.scrubber
        assert (scrubber.left_bound, scrubber.right_bound) == (10, 60)
        assert (scrubber.in_point, scrubber.out_point) == (20, 40)
        assert scrubber.cursor_pos == 33
        assert state.in_point <= scrubber.loop_pos <= state.out_point

    def test_it_follows_the_state_when_it_moves(self, live_app):
        live_app._push_the_state_to_the_window_which_alone_knows_its_widgets()
        live_app._state.window.jump_to(47)
        live_app._state.clip.mark_out(50)

        live_app._push_the_state_to_the_window_which_alone_knows_its_widgets()

        scrubber = live_app.window.scrubber
        assert scrubber.cursor_pos == 47
        assert scrubber.out_point == 50

    def test_it_passes_the_suggestions_through(self, live_app):
        live_app._state.suggestions.offer(22, 38)

        live_app._push_the_state_to_the_window_which_alone_knows_its_widgets()

        scrubber = live_app.window.scrubber
        assert (scrubber.suggested_in, scrubber.suggested_out) == (22, 38)

    def test_it_puts_a_frame_in_both_panes(self, live_app, rendered):
        window = live_app.window
        assert _is_blank(window.frame_at_cursor_pane, rendered)
        assert _is_blank(window.loop_preview_pane, rendered)

        live_app._push_the_state_to_the_window_which_alone_knows_its_widgets()

        assert not _is_blank(window.frame_at_cursor_pane, rendered)
        assert not _is_blank(window.loop_preview_pane, rendered)

    def test_it_writes_the_cursor_position_and_timestamp(self, live_app):
        live_app._push_the_state_to_the_window_which_alone_knows_its_widgets()

        frame_of_the_loaded = _TICK_STATE["cursor"] - _TICK_STATE["left_bound"]
        last_loaded = _TICK_STATE["right_bound"] - _TICK_STATE["left_bound"]
        at = format_seconds(_TICK_STATE["cursor"] / _TICK_STATE["fps"])
        assert live_app.window.cursor_label.text() == f"cursor: {frame_of_the_loaded}/{last_loaded} @ {at}"

    def test_it_writes_the_loop_length_and_the_speed(self, live_app):
        change_speed(live_app._state, 0.5)

        live_app._push_the_state_to_the_window_which_alone_knows_its_widgets()

        assert "/21 @ " in live_app.window.loop_label.text()
        assert live_app.window.speed_label.text() == "speed: 1.50x (playing)"

    def test_a_paused_loop_says_so(self, live_app):
        toggle_loop_pause(live_app._state)

        live_app._push_the_state_to_the_window_which_alone_knows_its_widgets()

        assert live_app.window.speed_label.text() == "speed: 1.00x (paused)"

    def test_it_shows_the_session_warning_the_state_carries(self, live_app):
        live_app._state.session_warning = "Autosave failed: disk full"

        live_app._push_the_state_to_the_window_which_alone_knows_its_widgets()

        assert live_app.window.warning_label.text() == "Autosave failed: disk full"

    def test_it_tells_the_controls_which_loop_mode_is_on(self, live_app):
        live_app._state.loop_mode = LoopMode.TIP_BASE

        live_app._push_the_state_to_the_window_which_alone_knows_its_widgets()

        assert live_app.window.scrubber_controls.loop_mode_btn.text() == "tip-base"

    def test_a_frame_that_cannot_be_decoded_does_not_stop_the_rest(self, live_app, rendered):
        with patch("genaumacher.gui.main_window.safe_frame", side_effect=KeyError("gone")):
            live_app._push_the_state_to_the_window_which_alone_knows_its_widgets()

        assert _is_blank(live_app.window.frame_at_cursor_pane, rendered)
        assert _is_blank(live_app.window.loop_preview_pane, rendered)
        assert live_app.window.scrubber.cursor_pos == 33
        assert live_app.window.speed_label.text() == "speed: 1.00x (playing)"


class TestRun:
    def test_run_shows_the_window_and_starts_the_animation(self, live_app, ticked_within):
        with patch.object(QApplication, "exec", return_value=0) as event_loop:
            assert live_app.run() == 0

        event_loop.assert_called_once()
        assert live_app.window.isVisible()
        assert ticked_within(live_app.playback_timer.tick, 2000) is True

    def test_the_tick_is_wired_to_the_frame_update(self, live_app, ticked_within):
        with patch.object(QApplication, "exec", return_value=0):
            live_app.run()

        assert ticked_within(live_app.playback_timer.tick, 2000) is True
        assert live_app.window.scrubber.cursor_pos == 33

    def test_closing_the_window_stops_the_animation(self, live_app, ticked_within):
        with patch.object(QApplication, "exec", return_value=0):
            live_app.run()
        assert ticked_within(live_app.playback_timer.tick, 2000) is True

        live_app.window.close()
        drain_a_tick_already_on_its_way()

        assert ticked_within(live_app.playback_timer.tick, 200) is False


def test_a_frame_the_decoder_will_not_give_up_does_not_take_the_window_with_it_an_exception_out_of_a_qt_slot_would_end_the_process(live_app, rendered):
    with patch("genaumacher.gui.main_window.safe_frame",
               side_effect=RuntimeError("Could not load frame 211")):
        live_app._push_the_state_to_the_window_which_alone_knows_its_widgets()

    assert _is_blank(live_app.window.frame_at_cursor_pane, rendered)
    assert _is_blank(live_app.window.loop_preview_pane, rendered)
    assert live_app.window.scrubber.cursor_pos == 33
    assert live_app.window.speed_label.text() == "speed: 1.00x (playing)"
