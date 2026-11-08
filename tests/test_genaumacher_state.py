from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest

from genaumacher.bounds import (
    contract_left,
    contract_right,
    extend_left,
    extend_right,
)
from genaumacher.editing import (
    accept_suggested_in,
    accept_suggested_out,
    cycle_loop_mode,
    set_mark_in,
    set_mark_out,
    shift_in_out,
)
from genaumacher.loop_suggestions import update_loop_suggestions
from genaumacher.navigation import (
    move_cursor_left,
    move_cursor_right,
    toggle_wrap_mode,
)
from genaumacher.playback import (
    change_speed,
    current_loop_frame_index,
    loop_preview_indices,
    toggle_loop_pause,
)
from genaumacher.state import VideoState


class _CapturesUpTo:
    def __init__(self, last_readable: int):
        self._last = last_readable
        self._pos = 0

    def set(self, prop, value) -> bool:
        self._pos = int(value)
        return True

    def read(self):
        if self._pos > self._last:
            return False, None
        self._pos += 1
        return True, np.zeros((2, 2, 3), dtype=np.uint8)

    def release(self) -> None:
        pass


def _pattern_frame(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(40, 40, 3), dtype=np.uint8)


class TestVideoStateDefaults:
    def test_skip_normalize_defaults_false(self, make_state):
        s = make_state()
        assert s.skip_normalize is False


class TestVideoStateProperties:
    def test_loaded_count(self, make_state):
        s = make_state(left_bound=0, right_bound=49)
        assert s.loaded_count == 50

    def test_loaded_count_single_frame(self, make_state):
        s = make_state(left_bound=5, right_bound=5)
        assert s.loaded_count == 1


class TestClampCurrent:
    def test_clamped_up_to_loaded_start_in_blue_mode(self, make_state):
        s = make_state(left_bound=10, cursor=5, wrap_mode="blue")
        s.clamp_cursor()
        assert s.cursor == s.left_bound

    def test_clamped_down_to_loaded_end_in_blue_mode(self, make_state):
        s = make_state(right_bound=50, cursor=99, wrap_mode="blue")
        s.clamp_cursor()
        assert s.cursor == s.right_bound

    def test_within_range_unchanged(self, make_state):
        s = make_state(left_bound=0, right_bound=99, cursor=50, wrap_mode="blue")
        s.clamp_cursor()
        assert s.cursor == 50


class TestCurrentPayload:
    def test_has_required_keys(self, make_state):
        s = make_state()
        payload = s.current_payload()
        for key in ("version", "session_name", "video_path", "fps", "total_frames",
                    "loaded_start", "loaded_end", "active_start", "active_end",
                    "current", "seconds_per_step", "loop_mode", "wrap_mode", "speed"):
            assert key in payload, f"Missing key: {key}"

    def test_version_is_1(self, make_state):
        s = make_state()
        assert s.current_payload()["version"] == 2

    def test_session_name_correct(self, make_state):
        s = make_state(session_name="my_clip")
        assert s.current_payload()["session_name"] == "my_clip"

    def test_seconds_per_step(self, make_state):
        s = make_state(base_step=30, fps=30.0)
        assert s.current_payload()["seconds_per_step"] == pytest.approx(1.0)

    def test_loop_mode_preserved(self, make_state):
        s = make_state(loop_mode="tip-base")
        assert s.current_payload()["loop_mode"] == "tip-base"


class TestCycleLoopMode:
    def test_cycles_to_next_mode(self, make_state):
        s = make_state(loop_mode="base-tip-base")
        cycle_loop_mode(s)
        assert s.loop_mode == "tip-base-tip"


class TestToggleWrapMode:
    def test_switching_to_yellow_clamps_current_into_in_out(self, make_state):
        s = make_state(wrap_mode="blue", in_point=10, out_point=20, cursor=25)
        toggle_wrap_mode(s)
        assert s.wrap_mode == "yellow"
        assert s.cursor == 20

    def test_switching_back_to_blue_preserves_current(self, make_state):
        s = make_state(wrap_mode="yellow", in_point=10, out_point=20, cursor=15)
        toggle_wrap_mode(s)
        assert s.wrap_mode == "blue"
        assert s.cursor == 15


class TestMoveCurrent:
    def test_move_left_wraps_within_loaded_range_in_blue_mode(self, make_state):
        s = make_state(left_bound=10, right_bound=20, cursor=10, wrap_mode="blue")
        move_cursor_left(s)
        assert s.cursor == 20
        assert s.render_rev == 1

    def test_move_left_wraps_within_in_out_in_yellow_mode(self, make_state):
        s = make_state(left_bound=0, right_bound=30, in_point=10, out_point=20, cursor=10, wrap_mode="yellow")
        move_cursor_left(s)
        assert s.cursor == 20
        assert s.render_rev == 1

    def test_move_right_wraps_within_loaded_range_in_blue_mode(self, make_state):
        s = make_state(left_bound=10, right_bound=20, cursor=20, wrap_mode="blue")
        move_cursor_right(s)
        assert s.cursor == 10
        assert s.render_rev == 1

    def test_move_right_wraps_within_in_out_in_yellow_mode(self, make_state):
        s = make_state(left_bound=0, right_bound=30, in_point=10, out_point=20, cursor=20, wrap_mode="yellow")
        move_cursor_right(s)
        assert s.cursor == 10
        assert s.render_rev == 1


class TestLoopPause:
    def test_current_loop_frame_stays_fixed_while_paused(self, make_state):
        s = make_state(in_point=10, out_point=19, fps=10.0, speed=1.0,
                       loop_anchor=100.0)
        with patch("genaumacher.playback.time.monotonic", side_effect=[100.45, 100.8, 100.9]):
            toggle_loop_pause(s)
            first = current_loop_frame_index(s)
            second = current_loop_frame_index(s)
        assert s.loop_paused is True
        assert first == 14
        assert second == 14

    def test_toggle_pause_resume_keeps_same_frame_continuity(self, make_state):
        s = make_state(in_point=10, out_point=19, fps=10.0, speed=1.0,
                       loop_anchor=100.0)
        with patch("genaumacher.playback.time.monotonic", side_effect=[100.45, 100.45, 100.65]):
            toggle_loop_pause(s)
            toggle_loop_pause(s)
            resumed = current_loop_frame_index(s)
        assert s.loop_paused is False
        assert resumed == 16


class TestLoopPreviewIndices:
    def test_base_tip_preview_mirrors_back(self, make_state):
        s = make_state(in_point=10, out_point=12, loop_mode="base-tip")
        assert loop_preview_indices(s) == [10, 11, 12, 11, 10]

    def test_tip_base_preview_prepends_reversed_half(self, make_state):
        s = make_state(in_point=10, out_point=12, loop_mode="tip-base")
        assert loop_preview_indices(s) == [12, 11, 10, 11, 12]

    def test_tip_base_tip_preview_rotates_halfway(self, make_state):
        s = make_state(in_point=10, out_point=15, loop_mode="tip-base-tip")
        assert loop_preview_indices(s) == [13, 14, 15, 10, 11, 12]


class TestChangeSpeed:
    def test_speed_does_not_drop_below_quarter_x(self, make_state):
        s = make_state(speed=0.25)
        with patch("genaumacher.playback.time.monotonic", return_value=100.0):
            change_speed(s, -0.25)
        assert s.speed == pytest.approx(0.25)

    def test_change_speed_while_paused_keeps_paused_state(self, make_state):
        s = make_state(in_point=10, out_point=19, fps=10.0, speed=1.0,
                       loop_paused=True, paused_loop_idx=14)
        with patch("genaumacher.playback.time.monotonic", return_value=100.0):
            change_speed(s, 0.25)
        assert s.loop_paused is True
        assert s.loop.paused_idx == 14
        assert s.speed == pytest.approx(1.25)


class TestContractLeft:
    def test_shrinks_loaded_start_by_base_step(self, make_state):
        s = make_state(left_bound=10, in_point=20, base_step=5)
        contract_left(s)
        assert s.left_bound == 15

    def test_prunes_frames_and_signatures_before_new_loaded_start(self, make_state):
        s = make_state(left_bound=10, in_point=20, base_step=5)
        s.frames = {i: np.zeros((2, 2, 3), dtype=np.uint8) for i in range(10, 31)}
        s.frame_signatures = {i: np.zeros((2, 2), dtype=np.float32) for i in range(10, 31)}

        contract_left(s)

        assert s.left_bound == 15
        assert all(idx >= 15 for idx in s.frames)
        assert all(idx >= 15 for idx in s.frame_signatures)

    def test_does_nothing_when_gap_too_small(self, make_state):
        s = make_state(left_bound=0, in_point=3, base_step=5)
        s.frames = {i: np.zeros((2, 2, 3), dtype=np.uint8) for i in range(100)}
        original = s.left_bound
        contract_left(s)
        assert s.left_bound == original

    def test_current_clamped_upward(self, make_state):
        s = make_state(left_bound=0, in_point=20, base_step=5, cursor=3)
        contract_left(s)
        assert s.cursor >= s.left_bound


class TestExtendLeft:
    def test_widens_the_loaded_range_by_one_step(self, make_state):
        s = make_state(left_bound=20, right_bound=60, base_step=5)

        extend_left(s)

        assert s.left_bound == 15

    def test_it_loads_the_frames_it_just_made_room_for(self, make_state):
        s = make_state(left_bound=20, right_bound=60, base_step=5)

        extend_left(s)

        assert all(idx in s.frames for idx in range(15, 20))

    def test_it_stops_at_the_start_of_the_video(self, make_state):
        s = make_state(left_bound=2, right_bound=60, base_step=5)

        extend_left(s)

        assert s.left_bound == 0

    def test_at_the_start_of_the_video_it_saves_nothing(self, make_state):
        s = make_state(left_bound=0, right_bound=60, base_step=5)

        extend_left(s)

        assert s.left_bound == 0
        assert s.persist_session.calls == 0


class TestExtendRight:
    def test_widens_the_loaded_range_by_one_step(self, make_state):
        s = make_state(total_frames=100, left_bound=0, right_bound=60, base_step=5)

        extend_right(s)

        assert s.right_bound == 65

    def test_it_loads_the_frames_it_just_made_room_for(self, make_state):
        s = make_state(total_frames=100, left_bound=0, right_bound=60, base_step=5)

        extend_right(s)

        assert all(idx in s.frames for idx in range(61, 66))

    def test_it_stops_at_the_end_of_the_video(self, make_state):
        s = make_state(total_frames=100, left_bound=0, right_bound=97, base_step=5)

        extend_right(s)

        assert s.right_bound == 99

    def test_at_the_end_of_the_video_it_saves_nothing(self, make_state):
        s = make_state(total_frames=100, left_bound=0, right_bound=99, base_step=5)

        extend_right(s)

        assert s.right_bound == 99
        assert s.persist_session.calls == 0

    def test_the_edge_is_the_last_frame_the_decoder_produced(self, make_state):
        s = make_state(total_frames=100, left_bound=0, right_bound=60, base_step=5)
        s.cap = _CapturesUpTo(62)

        extend_right(s)

        assert s.right_bound == 62
        assert max(s.frames) == 62

        saves = s.persist_session.calls
        extend_right(s)

        assert s.right_bound == 62
        assert s.persist_session.calls == saves


class TestContractRight:
    def test_shrinks_loaded_end(self, make_state):
        s = make_state(right_bound=99, out_point=70, base_step=5)
        contract_right(s)
        assert s.right_bound == 94

    def test_prunes_frames_and_signatures_after_new_loaded_end(self, make_state):
        s = make_state(left_bound=0, right_bound=30, out_point=20, base_step=5)
        s.frames = {i: np.zeros((2, 2, 3), dtype=np.uint8) for i in range(31)}
        s.frame_signatures = {i: np.zeros((2, 2), dtype=np.float32) for i in range(31)}

        contract_right(s)

        assert s.right_bound == 25
        assert all(idx <= 25 for idx in s.frames)
        assert all(idx <= 25 for idx in s.frame_signatures)

    def test_does_nothing_when_gap_too_small(self, make_state):
        s = make_state(right_bound=99, out_point=97, base_step=5)
        original = s.right_bound
        contract_right(s)
        assert s.right_bound == original


def _suggest_in(idx: int):
    def prepare(state: VideoState) -> None:
        state.suggestions.offer(idx, state.suggested_out)
    return prepare


def _suggest_out(idx: int):
    def prepare(state: VideoState) -> None:
        state.suggestions.offer(state.suggested_in, idx)
    return prepare


def _no_prep(state: VideoState) -> None:
    pass


def _speed(delta: float):
    def act(state: VideoState) -> None:
        change_speed(state, delta)
    return act


def _shift(direction: int):
    def act(state: VideoState) -> None:
        shift_in_out(state, direction)
    return act


_EDITS_THAT_CHANGE_THE_CLIP = [
    ("set_mark_in", {"in_point": 5, "out_point": 50, "cursor": 20}, _no_prep, set_mark_in),
    ("set_mark_out", {"in_point": 5, "out_point": 50, "cursor": 30}, _no_prep, set_mark_out),
    ("accept_suggested_in", {"in_point": 10, "out_point": 30}, _suggest_in(12), accept_suggested_in),
    ("accept_suggested_out", {"in_point": 10, "out_point": 30}, _suggest_out(28), accept_suggested_out),
    ("shift_in_out", {"in_point": 10, "out_point": 20, "cursor": 14}, _no_prep, _shift(1)),
    ("cycle_loop_mode", {"loop_mode": "base-tip-base"}, _no_prep, cycle_loop_mode),
    ("toggle_wrap_mode", {"wrap_mode": "blue", "in_point": 10, "out_point": 20, "cursor": 25}, _no_prep, toggle_wrap_mode),
    ("contract_left", {"left_bound": 10, "in_point": 20, "base_step": 5}, _no_prep, contract_left),
    ("contract_right", {"right_bound": 99, "out_point": 70, "base_step": 5}, _no_prep, contract_right),
    ("extend_left", {"left_bound": 20, "right_bound": 60, "base_step": 5}, _no_prep, extend_left),
    ("extend_right", {"total_frames": 100, "right_bound": 60, "base_step": 5}, _no_prep, extend_right),
    ("change_speed", {"speed": 1.0}, _no_prep, _speed(0.25)),
    ("move_cursor_left", {"left_bound": 0, "right_bound": 99, "cursor": 20}, _no_prep, move_cursor_left),
    ("move_cursor_right", {"left_bound": 0, "right_bound": 99, "cursor": 20}, _no_prep, move_cursor_right),
]

_EDITS_THAT_REFUSE = [
    ("set_mark_in past active_end", {"in_point": 5, "out_point": 50, "cursor": 55}, _no_prep, set_mark_in),
    ("set_mark_out before active_start", {"in_point": 20, "out_point": 50, "cursor": 10}, _no_prep, set_mark_out),
    ("accept_suggested_in at active_end", {"in_point": 10, "out_point": 30}, _suggest_in(30), accept_suggested_in),
    ("accept_suggested_out at in_point", {"in_point": 10, "out_point": 30}, _suggest_out(10), accept_suggested_out),
    ("shift_in_out out of bounds", {"in_point": 2, "out_point": 12, "cursor": 5}, _no_prep, _shift(-1)),
    ("contract_left with no room", {"left_bound": 0, "in_point": 3, "base_step": 5}, _no_prep, contract_left),
    ("contract_right with no room", {"right_bound": 99, "out_point": 97, "base_step": 5}, _no_prep, contract_right),
    ("change_speed already at the floor", {"speed": 0.25}, _no_prep, _speed(-0.25)),
]


class TestAnEditIsSaved:
    @pytest.mark.parametrize(
        ("kwargs", "prepare", "act"),
        [pytest.param(k, p, a, id=label) for label, k, p, a in _EDITS_THAT_CHANGE_THE_CLIP],
    )
    def test_an_edit_redraws_and_saves_the_session(self, kwargs, prepare, act, make_state):
        s = make_state(**kwargs)
        prepare(s)
        before = s.render_rev
        act(s)
        assert s.render_rev > before
        assert s.persist_session.calls == 1

    @pytest.mark.parametrize(
        ("kwargs", "prepare", "act"),
        [pytest.param(k, p, a, id=label) for label, k, p, a in _EDITS_THAT_REFUSE],
    )
    def test_a_refused_edit_saves_nothing(self, kwargs, prepare, act, make_state):
        s = make_state(**kwargs)
        prepare(s)
        act(s)
        assert s.persist_session.calls == 0


class TestSetMarkIn:
    def test_advances_active_start_to_current(self, make_state):
        s = make_state(in_point=5, out_point=50, cursor=20)
        set_mark_in(s)
        assert s.in_point == 20

    def test_does_not_advance_past_active_end(self, make_state):
        s = make_state(in_point=5, out_point=50, cursor=55)
        original = s.in_point
        set_mark_in(s)
        assert s.in_point == original


class TestSetMarkOut:
    def test_retreats_active_end_to_current(self, make_state):
        s = make_state(in_point=5, out_point=50, cursor=30)
        set_mark_out(s)
        assert s.out_point == 30

    def test_does_not_retreat_before_active_start(self, make_state):
        s = make_state(in_point=20, out_point=50, cursor=10)
        original = s.out_point
        set_mark_out(s)
        assert s.out_point == original


class TestAcceptSuggestedMarks:
    def test_accept_suggested_in_updates_active_start(self, make_state):
        s = make_state(in_point=10, out_point=30, loop_anchor=0.0)
        s.suggestions.offer(12, None)
        with patch("genaumacher.editing.update_loop_suggestions") as refresh_suggestions:
            accept_suggested_in(s)
        assert s.in_point == 12
        assert s.clip.anchor_in == 12
        assert s.loop.anchor > 0.0
        refresh_suggestions.assert_called_once_with(s)

    def test_accept_suggested_out_updates_active_end(self, make_state):
        s = make_state(in_point=10, out_point=30, loop_anchor=0.0)
        s.suggestions.offer(None, 28)
        with patch("genaumacher.editing.update_loop_suggestions") as refresh_suggestions:
            accept_suggested_out(s)
        assert s.out_point == 28
        assert s.clip.anchor_out == 28
        assert s.loop.anchor > 0.0
        refresh_suggestions.assert_called_once_with(s)

    def test_accept_suggested_in_ignores_invalid_candidate(self, make_state):
        s = make_state(in_point=10, out_point=30, loop_anchor=0.0)
        s.suggestions.offer(30, None)
        with patch("genaumacher.editing.update_loop_suggestions") as refresh_suggestions:
            accept_suggested_in(s)
        assert s.in_point == 10
        assert s.loop.anchor == 0.0
        refresh_suggestions.assert_not_called()

    def test_accept_suggested_out_ignores_invalid_candidate(self, make_state):
        s = make_state(in_point=10, out_point=30, loop_anchor=0.0)
        s.suggestions.offer(None, 10)
        with patch("genaumacher.editing.update_loop_suggestions") as refresh_suggestions:
            accept_suggested_out(s)
        assert s.out_point == 30
        assert s.loop.anchor == 0.0
        refresh_suggestions.assert_not_called()


class TestShiftActiveRange:
    def test_shift_right_reuses_old_out_as_new_in(self, make_state):
        s = make_state(in_point=10, out_point=20, cursor=14)
        shift_in_out(s, 1)
        assert s.in_point == 20
        assert s.out_point == 30
        assert s.cursor == 24

    def test_shift_left_reuses_old_in_as_new_out(self, make_state):
        s = make_state(in_point=20, out_point=30, cursor=26)
        shift_in_out(s, -1)
        assert s.in_point == 10
        assert s.out_point == 20
        assert s.cursor == 16

    def test_shift_right_expands_loaded_bounds_when_needed(self, make_state):
        s = make_state(left_bound=0, right_bound=24, in_point=10, out_point=20, cursor=12, total_frames=40)

        def fake_ensure_loaded(state: VideoState, want_start: int, want_end: int) -> None:
            state.window.widen_left_to(want_start)
            state.window.widen_right_to(want_end)

        with patch("genaumacher.editing.ensure_loaded", side_effect=fake_ensure_loaded), \
             patch("genaumacher.editing.update_loop_suggestions"):
            shift_in_out(s, 1)
        assert s.right_bound == 35
        assert s.in_point == 20
        assert s.out_point == 30

    def test_shift_left_expands_loaded_bounds_when_needed(self, make_state):
        s = make_state(left_bound=12, right_bound=40, in_point=20, out_point=30, cursor=25, total_frames=60)

        def fake_ensure_loaded(state: VideoState, want_start: int, want_end: int) -> None:
            state.window.widen_left_to(want_start)
            state.window.widen_right_to(want_end)

        with patch("genaumacher.editing.ensure_loaded", side_effect=fake_ensure_loaded), \
             patch("genaumacher.editing.update_loop_suggestions"):
            shift_in_out(s, -1)
        assert s.left_bound == 5
        assert s.in_point == 10
        assert s.out_point == 20

    def test_shift_right_preserves_existing_loaded_end_when_buffer_already_exists(self, make_state):
        s = make_state(left_bound=0, right_bound=40, in_point=10, out_point=20, cursor=14, base_step=5)
        with patch("genaumacher.editing.update_loop_suggestions"):
            shift_in_out(s, 1)
        assert s.right_bound == 40
        assert s.out_point == 30

    def test_shift_left_preserves_existing_loaded_start_when_buffer_already_exists(self, make_state):
        s = make_state(left_bound=0, right_bound=40, in_point=20, out_point=30, cursor=24, base_step=5)
        with patch("genaumacher.editing.update_loop_suggestions"):
            shift_in_out(s, -1)
        assert s.left_bound == 0
        assert s.in_point == 10

    def test_shift_pulls_the_cursor_back_inside_the_loaded_range(self, make_state):
        s = make_state(total_frames=41, left_bound=0, right_bound=40,
                        in_point=0, out_point=20, cursor=39)
        shift_in_out(s, 1)
        assert (s.in_point, s.out_point) == (20, 40)
        assert s.cursor == 40

    def test_shift_does_nothing_if_it_would_leave_video_bounds(self, make_state):
        s = make_state(in_point=2, out_point=12, cursor=5, loop_anchor=0.0)
        original = (s.in_point, s.out_point, s.cursor)
        shift_in_out(s, -1)
        assert (s.in_point, s.out_point, s.cursor) == original
        assert s.loop.anchor == 0.0


class TestLoopSuggestions:
    def test_no_suggestions_for_untouched_initial_selection(self, make_state):
        s = make_state(in_point=10, out_point=40, initial_in_point=10, initial_out_point=40)
        update_loop_suggestions(s)
        assert s.suggested_in is None
        assert s.suggested_out is None

    def test_marked_in_suggests_neighbor_before_matching_return_frame(self, make_state):
        s = make_state(
            total_frames=80,
            left_bound=0,
            right_bound=79,
            in_point=10,
            out_point=60,
            cursor=10,
            initial_in_point=0,
            initial_out_point=60,
        )
        frames = {i: _pattern_frame(1000 + i) for i in range(80)}
        frames[10] = _pattern_frame(42)
        frames[12] = frames[10].copy()
        frames[50] = frames[10].copy()
        s.frames = frames

        update_loop_suggestions(s)

        assert s.suggested_in is None
        assert s.suggested_out == 49

    def test_when_both_marks_are_set_pair_can_nudge_to_better_neighboring_loop(self, make_state):
        s = make_state(
            total_frames=80,
            left_bound=0,
            right_bound=79,
            in_point=10,
            out_point=20,
            cursor=10,
            initial_in_point=0,
            initial_out_point=79,
        )
        frames = {i: _pattern_frame(2000 + i) for i in range(80)}
        frames[10] = _pattern_frame(11)
        frames[11] = _pattern_frame(12)
        frames[21] = frames[10].copy()
        frames[22] = frames[11].copy()
        s.frames = frames

        update_loop_suggestions(s)

        assert s.suggested_in == 11
        assert s.suggested_out == 21

    def test_refinement_stays_anchored_after_accepting_suggested_out(self, make_state):
        s = make_state(
            total_frames=80,
            left_bound=0,
            right_bound=79,
            in_point=10,
            out_point=20,
            cursor=10,
            initial_in_point=0,
            initial_out_point=79,
        )
        frames = {i: _pattern_frame(3000 + i) for i in range(80)}
        frames[10] = _pattern_frame(21)
        frames[11] = _pattern_frame(22)
        frames[12] = _pattern_frame(23)
        frames[21] = frames[10].copy()
        frames[22] = frames[11].copy()
        frames[23] = frames[12].copy()
        s.frames = frames
        s.suggestions.offer(None, 20)
        s.clip.anchor_in = 10
        s.clip.anchor_out = 20

        accept_suggested_out(s)
        update_loop_suggestions(s)

        first_pair = (s.suggested_in, s.suggested_out)

        s.clip.start, s.clip.end = first_pair
        update_loop_suggestions(s)

        assert (s.suggested_in, s.suggested_out) == first_pair

    @pytest.mark.parametrize(("loop_mode", "initial", "turning_points", "expected"), [
        pytest.param("base-tip", (0, 60), [37], (None, 37), id="base-tip suggests the out point"),
        pytest.param("tip-base", (10, 79), [33], (33, None), id="tip-base suggests the in point"),
        pytest.param("base-tip", (0, 79), [35, 24], (24, 35), id="both marks moved"),
    ])
    def test_a_half_loop_mode_searches_for_turning_points_and_nothing_else(
        self, make_state, loop_mode, initial, turning_points, expected
    ):
        s = make_state(
            total_frames=80, left_bound=0, right_bound=79,
            in_point=10, out_point=60,
            initial_in_point=initial[0], initial_out_point=initial[1],
            loop_mode=loop_mode,
        )

        with patch("genaumacher.loop_suggestions.best_turning_point_index",
                   side_effect=turning_points) as turning, \
             patch("genaumacher.loop_suggestions.best_duplicate_match_index") as duplicate, \
             patch("genaumacher.loop_suggestions.pair_transition_score") as pair_score:
            update_loop_suggestions(s)

        assert (s.suggested_in, s.suggested_out) == expected
        assert turning.call_count == len(turning_points)
        duplicate.assert_not_called()
        pair_score.assert_not_called()


def test_the_frame_windows_fields_are_read_only_views_every_change_goes_through_the_window_which_keeps_the_cursor_inside(
        make_state):
    state = make_state()
    for name in ("total_frames", "left_bound", "right_bound", "cursor", "base_step"):
        with pytest.raises(AttributeError):
            setattr(state, name, 1)
