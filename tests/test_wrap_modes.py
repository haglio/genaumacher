from __future__ import annotations

from pathlib import Path

import pytest

from genaumacher.wrap_modes import WrapMode, wrap_bounds


class TestWrapBounds:
    def test_over_the_loaded_range_the_cursor_roams_everything_loaded(self, make_state):
        state = make_state(left_bound=10, right_bound=60, in_point=20,
                           out_point=40, wrap_mode=WrapMode.OVER_BOUNDS)

        assert wrap_bounds(state) == (10, 60)

    def test_over_the_in_out_it_is_held_to_the_clip(self, make_state):
        state = make_state(left_bound=10, right_bound=60, in_point=20,
                           out_point=40, wrap_mode=WrapMode.OVER_IN_OUT)

        assert wrap_bounds(state) == (20, 40)

    def test_the_two_modes_are_the_colors_the_session_file_carries(self):
        assert (WrapMode.OVER_BOUNDS, WrapMode.OVER_IN_OUT) == ("blue", "yellow")


@pytest.mark.repo_check
def test_nothing_else_spells_the_wrap_mode_out_as_a_color():
    package = Path(__file__).resolve().parents[1] / "genaumacher"
    offenders = [
        f"{path.relative_to(package.parent).as_posix()}:{n}"
        for path in sorted(package.rglob("*.py"))
        if path.name != "wrap_modes.py"
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if '"blue"' in line or '"yellow"' in line
    ]

    assert offenders == []
