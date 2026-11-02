"""Tests for genaumacher.gui.hotkeys — the one keymap.

It was written out four times in three modules and the copies had drifted; the
tests here are the guards that stop that happening again.
"""
from __future__ import annotations

import pytest
from PyQt6.QtCore import Qt

from genaumacher.gui.hotkeys import (
    HOTKEY_REFERENCE_ROWS,
    HOTKEYS,
    hotkey_for,
    hotkey_reference_rows,
)


class TestTheTableIsWellFormed:
    def test_no_two_shortcuts_claim_the_same_typed_key(self):
        claimed: dict[str, str] = {}
        for hotkey in HOTKEYS:
            for key in hotkey.keys:
                assert key not in claimed, f"{key!r}: {claimed.get(key)} and {hotkey.name}"
                claimed[key] = hotkey.name

    def test_no_two_shortcuts_claim_the_same_key_code(self):
        claimed: dict[int, str] = {}
        for hotkey in HOTKEYS:
            for code in hotkey.qt_keys:
                assert code not in claimed
                claimed[code] = hotkey.name

    def test_every_shortcut_can_be_reached_by_something(self):
        for hotkey in HOTKEYS:
            assert hotkey.keys or hotkey.qt_keys, hotkey.name

    def test_every_printed_keycap_is_a_key_that_reaches_the_action(self):
        """The hotkey reference cannot advertise a key the handler does not accept."""
        for hotkey in HOTKEYS:
            for keycap in hotkey.keycaps:
                assert keycap in hotkey.keys or keycap in _named_codes(hotkey), hotkey.name


def _named_codes(hotkey) -> set[str]:
    """Keycaps for the keys that carry no text: `left`, `space`, `enter`."""
    return {code.name.removeprefix("Key_").lower() for code in hotkey.qt_keys}


class TestTheLegendComesFromTheTable:
    def test_every_shortcut_appears_in_exactly_one_legend_entry(self):
        """The drift this closes: `q` was bound and the hotkey reference never said so."""
        listed = [name for row in HOTKEY_REFERENCE_ROWS for names, _, _ in row for name in names]

        assert sorted(listed) == sorted(s.name for s in HOTKEYS)

    def test_a_legend_entry_prints_the_keycaps_of_the_shortcuts_it_names(self):
        rendered = hotkey_reference_rows()
        speed = rendered[0][0]

        assert speed == (("-", "+"), " or ", "speed")

    def test_the_loop_mode_entry_says_loop_mode_as_the_launcher_does(self):
        entry = next(label for row in HOTKEY_REFERENCE_ROWS for names, _, label in row
                     if names == ("cycle_loop_mode",))

        assert entry == "cycle loop mode"

    def test_the_rendered_legend_has_the_shape_the_widget_paints(self):
        for row in hotkey_reference_rows():
            for keys, joiner, label in row:
                assert isinstance(keys, tuple)
                assert keys
                assert isinstance(joiner, str)
                assert isinstance(label, str)
                assert label


class TestLookup:
    @pytest.mark.parametrize("text, name", [
        ("a", "extend_left"),
        ("[", "mark_in"),
        ("_", "speed_down"),
        ("=", "speed_up"),
        ("9", "accept_in"),
        ("q", "quit"),
    ])
    def test_a_typed_key_finds_its_shortcut(self, text, name):
        found = hotkey_for(0, text)

        assert found is not None
        assert found.name == name

    def test_a_key_code_finds_its_shortcut(self):

        found = hotkey_for(Qt.Key.Key_Left, "")

        assert found is not None
        assert found.name == "cursor_left"

    def test_an_unbound_key_finds_nothing(self):
        assert hotkey_for(0, "z") is None
