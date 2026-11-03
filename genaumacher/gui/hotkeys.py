from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt

from genaumacher.bounds import contract_left, contract_right, extend_left, extend_right
from genaumacher.editing import (
    accept_suggested_in,
    accept_suggested_out,
    cycle_loop_mode,
    set_mark_in,
    set_mark_out,
    shift_in_out,
)
from genaumacher.navigation import move_cursor_left, move_cursor_right, toggle_wrap_mode
from genaumacher.playback import change_speed, toggle_loop_pause

if TYPE_CHECKING:
    from .main_window import GenaumacherMainWindow

Action = Callable[["GenaumacherMainWindow"], None]

HotkeyReferenceEntry = tuple[tuple[str, ...], str, str]


def _edits(fn: Callable[..., None], *args: object) -> Action:
    def act(window: GenaumacherMainWindow) -> None:
        fn(window.state, *args)

    return act


@dataclass(frozen=True)
class Hotkey:
    name: str
    action: Action
    keycaps: tuple[str, ...]
    keys: tuple[str, ...] = ()
    qt_keys: tuple[Qt.Key, ...] = ()


HOTKEYS: tuple[Hotkey, ...] = (
    Hotkey("speed_down", _edits(change_speed, -0.25), ("-",), keys=("-", "_")),
    Hotkey("speed_up", _edits(change_speed, 0.25), ("+",), keys=("+", "=")),
    Hotkey("play_pause", _edits(toggle_loop_pause), ("space",),
             qt_keys=(Qt.Key.Key_Space,)),
    Hotkey("export", lambda window: window.start_export(), ("enter",),
             qt_keys=(Qt.Key.Key_Return, Qt.Key.Key_Enter)),
    Hotkey("extend_left", _edits(extend_left), ("a",), keys=("a",)),
    Hotkey("contract_left", _edits(contract_left), ("s",), keys=("s",)),
    Hotkey("shift_left", _edits(shift_in_out, -1), ("<",), keys=(",", "<")),
    Hotkey("shift_right", _edits(shift_in_out, 1), (">",), keys=(".", ">")),
    Hotkey("cursor_left", _edits(move_cursor_left), ("left",),
             qt_keys=(Qt.Key.Key_Left,)),
    Hotkey("cursor_right", _edits(move_cursor_right), ("right",),
             qt_keys=(Qt.Key.Key_Right,)),
    Hotkey("mark_in", _edits(set_mark_in), ("i", "["), keys=("i", "[")),
    Hotkey("mark_out", _edits(set_mark_out), ("o", "]"), keys=("o", "]")),
    Hotkey("contract_right", _edits(contract_right), ("d",), keys=("d",)),
    Hotkey("extend_right", _edits(extend_right), ("f",), keys=("f",)),
    Hotkey("accept_in", _edits(accept_suggested_in), ("(",), keys=("9", "(")),
    Hotkey("accept_out", _edits(accept_suggested_out), (")",), keys=("0", ")")),
    Hotkey("toggle_wrap", _edits(toggle_wrap_mode), ("w",), keys=("w",)),
    Hotkey("cycle_loop_mode", _edits(cycle_loop_mode), ("l",), keys=("l",)),
    Hotkey("quit", lambda window: window.close(), ("q",), keys=("q",)),
)

HOTKEY_REFERENCE_ROWS: tuple[tuple[HotkeyReferenceEntry, ...], ...] = (
    (
        (("speed_down", "speed_up"), " or ", "speed"),
        (("play_pause",), "", "play or pause preview"),
        (("export",), "", "export"),
        (("quit",), "", "quit"),
        (("cycle_loop_mode",), "", "cycle loop mode"),
    ),
    (
        (("extend_left", "contract_left"), " or ", "adjust left bound"),
        (("cursor_left", "cursor_right"), " or ", "move cursor"),
        (("contract_right", "extend_right"), " or ", "adjust right bound"),
        (("toggle_wrap",), "", "toggle cursor wrap mode"),
    ),
    (
        (("shift_left", "shift_right"), " or ", "shift in-out"),
        (("mark_in",), "/", "mark in"),
        (("mark_out",), "/", "mark out"),
        (("accept_in", "accept_out"), " or ", "accept in or out suggestion"),
    ),
)

BY_NAME: dict[str, Hotkey] = {s.name: s for s in HOTKEYS}
_BY_TEXT: dict[str, Hotkey] = {key: s for s in HOTKEYS for key in s.keys}
_BY_CODE: dict[int, Hotkey] = {code: s for s in HOTKEYS for code in s.qt_keys}


def hotkey_for(key: int, text: str) -> Hotkey | None:
    return _BY_CODE.get(key) or _BY_TEXT.get(text)


def hotkey_reference_rows() -> tuple[tuple[HotkeyReferenceEntry, ...], ...]:
    return tuple(
        tuple(
            (
                tuple(cap for name in names for cap in BY_NAME[name].keycaps),
                joiner,
                label,
            )
            for names, joiner, label in row
        )
        for row in HOTKEY_REFERENCE_ROWS
    )
