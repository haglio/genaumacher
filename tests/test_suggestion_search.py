from __future__ import annotations

import numpy as np
import pytest

from genaumacher.suggestion_search import (
    best_duplicate_match_index,
    best_turning_point_index,
    candidate_similarity_curve,
    find_similarity_dip,
    smooth_1d,
)


def _curve(state, ref_idx, direction):
    return candidate_similarity_curve(state, ref_idx, direction=direction)


class TestSmooth1d:
    def test_a_radius_of_zero_searches_nowhere_and_changes_nothing(self):
        values = np.array([1.0, 5.0, 1.0])

        assert list(smooth_1d(values, 0)) == [1.0, 5.0, 1.0]

    def test_it_does_not_write_into_what_it_was_given(self):
        values = np.array([1.0, 5.0, 1.0])

        smooth_1d(values, 1)

        assert list(values) == [1.0, 5.0, 1.0]

    def test_it_averages_each_point_with_its_neighbors(self):
        values = np.array([0.0, 0.0, 3.0, 0.0, 0.0])

        smoothed = smooth_1d(values, 1)

        assert len(smoothed) == 5
        assert smoothed[2] == pytest.approx(1.0)
        assert smoothed.max() == pytest.approx(1.0)


class TestTheCandidateWindow:
    def test_it_starts_ten_frames_clear_of_the_reference(self, make_state):
        state = make_state(total_frames=200, left_bound=0, right_bound=120)

        candidates, _smoothed = _curve(state, 40, direction=+1)

        assert candidates[0] == 50
        assert candidates[-1] == 120

    def test_there_is_no_curve_when_the_window_holds_too_few_frames(self, make_state):
        state = make_state(total_frames=200, left_bound=0, right_bound=52)

        assert _curve(state, 40, direction=+1) is None

    def test_there_is_no_curve_when_the_window_is_empty(self, make_state):
        state = make_state(total_frames=200, left_bound=0, right_bound=45)

        assert _curve(state, 40, direction=+1) is None


class TestTheTwoDirectionsAreMirrorImages:
    def test_forward_the_window_begins_next_to_the_reference(self, make_state):
        state = make_state(total_frames=200, left_bound=20, right_bound=120)

        candidates, _smoothed = _curve(state, 60, direction=+1)

        assert candidates[0] == 70
        assert candidates[-1] == 120

    def test_backward_the_window_begins_next_to_the_reference_too(self, make_state):
        state = make_state(total_frames=200, left_bound=20, right_bound=120)

        candidates, _smoothed = _curve(state, 60, direction=-1)

        assert candidates[0] == 50
        assert candidates[-1] == 20

    def test_each_step_away_from_the_reference_is_one_step_along_the_list(self, make_state):
        state = make_state(total_frames=200, left_bound=20, right_bound=120)

        forward, _f = _curve(state, 60, direction=+1)
        backward, _b = _curve(state, 60, direction=-1)

        assert [c - 60 for c in forward[:3]] == [10, 11, 12]
        assert [c - 60 for c in backward[:3]] == [-10, -11, -12]

    def test_the_two_windows_hold_the_same_frames_in_opposite_order(self, make_state):
        state = make_state(total_frames=200, left_bound=20, right_bound=120)

        backward, _b = _curve(state, 60, direction=-1)

        assert sorted(backward) == list(range(20, 51))


class TestFindingTheRepeatBeforeAFrame:
    PERIOD = 60
    REF = 180

    @pytest.fixture
    def looping_clip(self, make_state):
        rng = np.random.default_rng(11)
        texture = rng.integers(0, 256, (64, 64, 3), dtype=np.uint8)
        state = make_state(total_frames=201, left_bound=0, right_bound=200, fps=30.0)
        state.frames = {
            i: np.roll(texture, i % self.PERIOD, axis=1) for i in range(201)
        }
        state.frame_signatures = {}
        return state

    def test_the_backward_search_finds_the_nearest_repeat(self, looping_clip):
        match = best_duplicate_match_index(looping_clip, self.REF, direction=-1)

        assert match == self.REF - self.PERIOD

    def test_the_backward_turning_point_is_near_the_reference_not_the_far_edge(self, looping_clip):
        turning = best_turning_point_index(looping_clip, self.REF, direction=-1)

        assert turning is not None
        assert self.REF - self.PERIOD < turning < self.REF


class TestTheDipItself:
    def test_it_names_what_it_found(self, make_state):
        rng = np.random.default_rng(11)
        texture = rng.integers(0, 256, (64, 64, 3), dtype=np.uint8)
        state = make_state(total_frames=201, left_bound=0, right_bound=200, fps=30.0)
        state.frames = {i: np.roll(texture, i % 60, axis=1) for i in range(201)}
        state.frame_signatures = {}

        dip = find_similarity_dip(state, 180, direction=-1)

        assert dip is not None
        assert dip.candidates[dip.dip_idx] == best_turning_point_index(
            state, 180, direction=-1
        )
        assert dip.baseline > dip.smoothed[dip.dip_idx]
        assert len(dip.slope) == len(dip.smoothed) - 1
        assert dip.run >= 2
