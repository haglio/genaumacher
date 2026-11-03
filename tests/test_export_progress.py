from __future__ import annotations

import pytest

from genaumacher.export_progress import fraction_in, progress_line


class TestTheLineTheSubprocessPrints:
    @pytest.mark.parametrize("fraction", [0.0, 0.2, 0.605, 1.0])
    def test_what_is_written_is_what_is_read(self, fraction):
        assert fraction_in(progress_line(fraction)) == pytest.approx(fraction, abs=1e-4)

    @pytest.mark.parametrize("line", [
        "Input FPS: 24.000000",
        "Wrote: D:/example-suite/videos/videos/genau/clips/seaside walk.mp4",
        "Traceback (most recent call last):",
        "",
        "progress",
    ])
    def test_anything_else_the_script_prints_is_not_a_fraction(self, line):
        assert fraction_in(line) is None

    def test_a_line_that_starts_right_and_ends_wrong_is_not_a_fraction(self):
        assert fraction_in(progress_line(0.5).split()[0] + " most of it") is None
