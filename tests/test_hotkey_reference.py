from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from PyQt6.QtGui import QFont, QImage, QPainter
from shared_ui.colors import BG_KEYCAP, BG_PRIMARY
from shared_ui.fonts import FONT_UI, SIZE_SMALL, SIZE_TINY

from genaumacher.gui.hotkey_reference import HotkeyReferenceWidget
from genaumacher.gui.hotkeys import hotkey_reference_rows


@pytest.fixture
def hotkey_reference():
    widget = HotkeyReferenceWidget(hotkey_reference_rows())
    widget.resize(900, 120)
    return widget


def _keycap_pixels(image, upper: int, lower: int) -> int:
    return sum(
        1
        for x in range(image.width())
        for y in range(upper, lower)
        if image.pixelColor(x, y).name() == BG_KEYCAP.name()
    )


class TestPainting:
    def test_every_row_of_the_legend_gets_keycaps(self, hotkey_reference, rendered):
        image = rendered(hotkey_reference)
        row_height = hotkey_reference.height() // len(hotkey_reference_rows())

        drawn = [
            _keycap_pixels(image, row * row_height, (row + 1) * row_height)
            for row in range(len(hotkey_reference_rows()))
        ]

        assert all(count > 0 for count in drawn), drawn

    def test_a_legend_with_no_rows_is_bare_background(self, hotkey_reference, rendered):
        hotkey_reference.hotkey_reference_rows = ()

        image = rendered(hotkey_reference)

        assert _keycap_pixels(image, 0, image.height()) == 0
        assert image.pixelColor(450, 60).name() == BG_PRIMARY.name()

    def test_no_row_carries_more_than_two_fifths_of_the_legend_so_the_widest_fits_the_900_px_window_a_share_since_the_offscreen_font_widens_every_row_alike(self, hotkey_reference):
        hotkey_reference.resize(900, 80)
        image = QImage(900, 80, QImage.Format.Format_RGB32)
        painter = QPainter(image)
        keycap = QFont(FONT_UI, SIZE_SMALL)
        keycap.setBold(True)
        small = QFont(FONT_UI, SIZE_TINY)
        widths = [
            hotkey_reference._row_width(painter, row, keycap, small, small)
            for row in hotkey_reference.hotkey_reference_rows
        ]
        painter.end()

        assert max(widths) <= 0.4 * sum(widths), widths

    def test_a_wider_row_gets_more_keycap_ink_than_a_narrower_one(self, hotkey_reference, rendered):
        hotkey_reference.hotkey_reference_rows = ((((("x",), "", "one"),)),)
        one_key = _keycap_pixels(rendered(hotkey_reference), 0, hotkey_reference.height())

        hotkey_reference.hotkey_reference_rows = (((("x",), "", "one"), (("y",), "", "two")),)
        two_keys = _keycap_pixels(rendered(hotkey_reference), 0, hotkey_reference.height())

        assert two_keys > one_key


def test_the_legend_does_not_need_the_video_decoder_to_be_imported():
    probe = "import sys; sys.modules['cv2'] = None; import genaumacher.gui.hotkey_reference"
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}

    result = subprocess.run([sys.executable, "-c", probe],
                            cwd=Path(__file__).resolve().parents[1],
                            env=env, capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
