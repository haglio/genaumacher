from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QPushButton, QWidget
from shared_ui.colors import RED, TEXT_SECONDARY
from shared_ui.fonts import FONT_UI, SIZE_SMALL, make_font
from shared_ui.spacing import BUTTON_PAD_H_TIGHT, BUTTON_PAD_V

LABEL_STYLE = f"color: {TEXT_SECONDARY.name()}; background: transparent;"
WARNING_STYLE = f"color: {RED.name()}; background: transparent;"
_FIXED_SIZE = "fixedSize"

_CHROME_STYLE = f"""
    QPushButton {{
        padding: {BUTTON_PAD_V}px {BUTTON_PAD_H_TIGHT}px;
    }}
    QPushButton[{_FIXED_SIZE}="true"] {{
        padding: 0px {BUTTON_PAD_H_TIGHT}px;
    }}
"""

SMALL_BUTTON = (32, 28)
EXPORT_BUTTON = (72, 28)
WRAP_BUTTON = (64, 28)


def small_font() -> QFont:
    # Qt refuses a QFont before a QGuiApplication exists, so never at import.
    return make_font(FONT_UI, SIZE_SMALL)


def dress_controls(central: QWidget, button_bar, scrubber_controls) -> None:
    tc, bb = scrubber_controls, button_bar
    for button in (tc.shift_left_btn, tc.shift_right_btn,
                   tc.extend_left_btn, tc.contract_left_btn,
                   tc.contract_right_btn, tc.extend_right_btn,
                   tc.mark_in_btn, tc.mark_out_btn):
        _fix_size(button, SMALL_BUTTON)
    _fix_size(bb.export_btn, EXPORT_BUTTON)
    _fix_size(tc.wrap_btn, WRAP_BUTTON)
    central.setStyleSheet(_CHROME_STYLE)


def _fix_size(button: QPushButton, size: tuple[int, int]) -> None:
    button.setFixedSize(*size)
    button.setProperty(_FIXED_SIZE, True)


def refuse_focus(window: QWidget) -> None:
    for button in window.findChildren(QPushButton):
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
