from __future__ import annotations

from genaumacher.frame_window import FrameWindow


def _window(**overrides) -> FrameWindow:
    kwargs = {"total_frames": 100, "left_bound": 10, "right_bound": 60,
              "cursor": 30, "base_step": 5}
    kwargs.update(overrides)
    return FrameWindow(**kwargs)


class TestCount:
    def test_it_counts_both_ends_of_the_loaded_stretch(self):
        assert _window(left_bound=0, right_bound=49).count == 50

    def test_a_single_loaded_frame_counts_as_one(self):
        assert _window(left_bound=5, right_bound=5).count == 1


class TestHoldWithin:
    def test_a_cursor_below_the_range_is_pulled_up_to_the_floor(self):
        window = _window(cursor=5)

        window.hold_within(10, 60)

        assert window.cursor == 10

    def test_a_cursor_above_the_range_is_pulled_down_to_the_ceiling(self):
        window = _window(cursor=99)

        window.hold_within(10, 60)

        assert window.cursor == 60

    def test_a_cursor_already_inside_it_does_not_move(self):
        window = _window(cursor=30)

        window.hold_within(10, 60)

        assert window.cursor == 30


class TestContractLeft:
    def test_it_takes_one_step_off_the_left(self):
        window = _window(left_bound=10, base_step=5)

        assert window.contract_left(in_point=20) is True
        assert window.left_bound == 15

    def test_it_refuses_when_a_step_would_reach_the_in_out(self):
        window = _window(left_bound=0, base_step=5)

        assert window.contract_left(in_point=3) is False
        assert window.left_bound == 0

    def test_a_step_that_lands_exactly_on_the_active_start_is_allowed(self):
        window = _window(left_bound=10, base_step=5)

        assert window.contract_left(in_point=15) is True
        assert window.left_bound == 15

    def test_it_drags_a_stranded_cursor_along(self):
        window = _window(left_bound=10, cursor=12, base_step=5)

        window.contract_left(in_point=20)

        assert window.cursor == 15


class TestContractRight:
    def test_it_takes_one_step_off_the_right(self):
        window = _window(right_bound=99, base_step=5)

        assert window.contract_right(out_point=70) is True
        assert window.right_bound == 94

    def test_it_refuses_when_a_step_would_reach_the_in_out(self):
        window = _window(right_bound=99, base_step=5)

        assert window.contract_right(out_point=97) is False
        assert window.right_bound == 99

    def test_it_drags_a_stranded_cursor_along(self):
        window = _window(right_bound=99, cursor=98, base_step=5)

        window.contract_right(out_point=70)

        assert window.cursor == 94


class TestStepOut:
    def test_a_step_out_to_the_left_is_one_base_step(self):
        assert _window(left_bound=20, base_step=5).step_out_left() == 15

    def test_a_step_out_to_the_left_stops_at_the_first_frame(self):
        assert _window(left_bound=2, base_step=5).step_out_left() == 0

    def test_a_step_out_to_the_right_is_one_base_step(self):
        assert _window(right_bound=60, base_step=5, total_frames=100).step_out_right() == 65

    def test_a_step_out_to_the_right_stops_at_the_last_frame(self):
        assert _window(right_bound=97, base_step=5, total_frames=100).step_out_right() == 99


class TestWiden:
    def test_it_moves_the_left_edge_out(self):
        window = _window(left_bound=20)

        window.widen_left_to(15)

        assert window.left_bound == 15

    def test_a_left_edge_already_further_out_stands_a_loader_that_came_back_short_cannot_narrow_the_window_under_the_cursor(self):
        window = _window(left_bound=20)

        window.widen_left_to(25)

        assert window.left_bound == 20

    def test_it_moves_the_right_edge_out(self):
        window = _window(right_bound=60)

        window.widen_right_to(65)

        assert window.right_bound == 65

    def test_a_right_edge_already_further_out_stands_a_loader_that_came_back_short_cannot_narrow_the_window_under_the_cursor(self):
        window = _window(right_bound=60)

        window.widen_right_to(55)

        assert window.right_bound == 60


class TestTheEdgeIsOnlyEverWidenedToAFrame:
    def test_nothing_reaches_the_edge_to_a_bare_number(self):
        assert not hasattr(_window(right_bound=60), "reach_right_to")


class TestStepCursor:
    def test_stepping_back_moves_one_frame(self):
        window = _window(cursor=30)

        window.step_cursor_back(10, 60)

        assert window.cursor == 29

    def test_stepping_back_off_the_floor_wraps_to_the_ceiling(self):
        window = _window(cursor=10)

        window.step_cursor_back(10, 60)

        assert window.cursor == 60

    def test_stepping_forward_moves_one_frame(self):
        window = _window(cursor=30)

        window.step_cursor_forward(10, 60)

        assert window.cursor == 31

    def test_stepping_forward_off_the_ceiling_wraps_to_the_floor(self):
        window = _window(cursor=60)

        window.step_cursor_forward(10, 60)

        assert window.cursor == 10


class TestCarryAndJump:
    def test_carrying_moves_the_cursor_with_the_range_it_sits_in(self):
        window = _window(cursor=30)

        window.carry_cursor(10)

        assert window.cursor == 40

    def test_jumping_puts_the_cursor_where_it_was_asked(self):
        window = _window(cursor=30)

        window.jump_to(47)

        assert window.cursor == 47
