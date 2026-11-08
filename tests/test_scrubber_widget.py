from __future__ import annotations

import pytest
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QMouseEvent

from genaumacher.gui.scrubber_colors import (
    SCRUBBER_BOUNDS,
    SCRUBBER_CURSOR,
    SCRUBBER_IN_OUT,
    SCRUBBER_LOOP,
    SCRUBBER_SUGGESTED_IN,
    SCRUBBER_SUGGESTED_OUT,
)
from genaumacher.gui.scrubber_widget import ScrubberWidget


@pytest.fixture
def widget():
    w = ScrubberWidget()
    w.resize(800, 40)
    return w


class TestCoordinateMapping:
    def test_x_for_index_at_start(self, widget):
        widget.set_bounds(0, 100)
        x = widget.x_for_index(0)
        assert x == 0

    def test_x_for_index_at_end(self, widget):
        widget.set_bounds(0, 100)
        x = widget.x_for_index(100)
        assert x == widget.width()

    def test_x_for_index_midpoint(self, widget):
        widget.set_bounds(0, 100)
        x = widget.x_for_index(50)
        assert abs(x - widget.width() // 2) <= 1

    def test_index_for_x_at_start(self, widget):
        widget.set_bounds(0, 100)
        idx = widget.index_for_x(0)
        assert idx == 0

    def test_index_for_x_at_end(self, widget):
        widget.set_bounds(0, 100)
        idx = widget.index_for_x(widget.width())
        assert idx == 100

    def test_index_for_x_clamped(self, widget):
        widget.set_bounds(10, 50)
        idx = widget.index_for_x(-100)
        assert idx == 10
        idx = widget.index_for_x(9999)
        assert idx == 50


class TestSetState:
    def test_set_loaded_range(self, widget):
        widget.set_bounds(10, 200)
        assert widget.left_bound == 10
        assert widget.right_bound == 200

    def test_set_in_out(self, widget):
        widget.set_in_out(20, 80)
        assert widget.in_point == 20
        assert widget.out_point == 80

    def test_set_cursor(self, widget):
        widget.set_cursor_position(42)
        assert widget.cursor_pos == 42

    def test_set_loop_position(self, widget):
        widget.set_loop_position(55)
        assert widget.loop_pos == 55

    def test_set_suggestions(self, widget):
        widget.set_suggestions(10, 90)
        assert widget.suggested_in == 10
        assert widget.suggested_out == 90


class TestClickSignal:
    def test_click_emits_cursor_jumped(self, widget):
        widget.set_bounds(0, 100)
        results = []
        widget.cursor_jumped.connect(results.append)

        widget.mousePressEvent(QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(widget.width() / 2, widget.height() / 2),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        ))

        assert len(results) == 1
        assert abs(results[0] - 50) <= 1

    def test_a_right_click_moves_nothing(self, widget):
        widget.set_bounds(0, 100)
        results = []
        widget.cursor_jumped.connect(results.append)

        widget.mousePressEvent(QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(widget.width() / 2, widget.height() / 2),
            Qt.MouseButton.RightButton,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier,
        ))

        assert results == []


_MID_HEIGHT_CLEAR_OF_THE_TICK_DOTS_ALONG_BOTH_EDGES = 12


class TestPainting:
    @pytest.fixture
    def painted(self, widget, rendered):
        widget.set_bounds(0, 100)
        widget.set_in_out(20, 80)
        widget.set_cursor_position(50)
        widget.set_loop_position(30)
        widget.set_suggestions(10, 90)
        return rendered(widget)

    def _band(self, image, x):
        return image.pixelColor(x, _MID_HEIGHT_CLEAR_OF_THE_TICK_DOTS_ALONG_BOTH_EDGES).name()

    def test_the_loaded_range_is_drawn_outside_the_active_one(self, painted):
        assert self._band(painted, 40) == SCRUBBER_BOUNDS.name()
        assert self._band(painted, 700) == SCRUBBER_BOUNDS.name()

    def test_the_in_out_is_drawn_over_it(self, painted):
        assert self._band(painted, 300) == SCRUBBER_IN_OUT.name()
        assert self._band(painted, 500) == SCRUBBER_IN_OUT.name()

    def test_the_active_band_starts_and_ends_where_its_marks_are(self, painted, widget):
        just_inside = widget.x_for_index(20) + 3
        just_outside = widget.x_for_index(20) - 3

        assert self._band(painted, just_inside) == SCRUBBER_IN_OUT.name()
        assert self._band(painted, just_outside) == SCRUBBER_BOUNDS.name()

    def test_the_cursor_is_drawn_where_it_sits(self, painted, widget):
        assert self._band(painted, widget.x_for_index(50)) == SCRUBBER_CURSOR.name()

    def test_the_loop_position_is_drawn_where_it_sits(self, painted, widget):
        assert self._band(painted, widget.x_for_index(30)) == SCRUBBER_LOOP.name()

    def test_both_suggestions_are_drawn_where_they_sit(self, painted, widget):
        assert self._band(painted, widget.x_for_index(10)) == SCRUBBER_SUGGESTED_IN.name()
        assert self._band(painted, widget.x_for_index(90)) == SCRUBBER_SUGGESTED_OUT.name()

    def test_no_suggestion_lines_appear_when_there_are_none_and_their_hues_differ_from_both_ranges_a_suggestion_can_land_on_either(self, widget, rendered):
        widget.set_bounds(0, 100)
        widget.set_in_out(20, 80)
        widget.set_cursor_position(50)
        widget.set_loop_position(30)
        widget.set_suggestions(None, None)

        image = rendered(widget)

        drawn = {image.pixelColor(x, _MID_HEIGHT_CLEAR_OF_THE_TICK_DOTS_ALONG_BOTH_EDGES).name() for x in range(4, 796)}
        assert SCRUBBER_SUGGESTED_IN.name() not in drawn
        assert SCRUBBER_SUGGESTED_OUT.name() not in drawn

    def test_the_cursor_is_drawn_on_top_of_the_loop_position(self, widget, rendered):
        widget.set_bounds(0, 100)
        widget.set_in_out(20, 80)
        widget.set_loop_position(50)
        widget.set_cursor_position(50)

        image = rendered(widget)

        assert self._band(image, widget.x_for_index(50)) == SCRUBBER_CURSOR.name()
