from __future__ import annotations

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget
from shared_ui.colors import BORDER_SUBTLE
from shared_ui.spacing import BUTTON_GAP

GAP = BUTTON_GAP


class FloatingControlLayout:
    def __init__(self, scrubber, controls, shift_row: QWidget,
                 mark_row: QWidget, wrap_row) -> None:
        self._scrubber = scrubber
        self._controls = controls
        self._shift_row = shift_row
        self._mark_row = mark_row
        self._wrap_row = wrap_row
        self._wrap_color: QColor | None = None

    def place(self, *, in_point: int, out_point: int, cursor: int,
              wrap_from: int, wrap_to: int, wrap_color: QColor) -> None:
        if self._scrubber.width() <= 0:
            return
        self._place_shift(in_point, out_point)
        self._place_marks(in_point, out_point, cursor)
        self._place_wrap(wrap_from, wrap_to, wrap_color)

    def _offset_in(self, row: QWidget) -> int:
        return row.mapFromGlobal(self._scrubber.mapToGlobal(QPoint(0, 0))).x()

    def _place_shift(self, in_point: int, out_point: int) -> None:
        tl, tc = self._scrubber, self._controls
        center = self._offset_in(self._shift_row) + (
            tl.x_for_index(in_point) + tl.x_for_index(out_point)
        ) // 2
        width = tc.shift_left_btn.width()
        y = (self._shift_row.height() - tc.shift_left_btn.height()) // 2
        tc.shift_left_btn.move(center - GAP // 2 - width, y)
        tc.shift_right_btn.move(center + GAP // 2, y)
        tc.shift_left_btn.show()
        tc.shift_right_btn.show()

    def _place_marks(self, in_point: int, out_point: int, cursor: int) -> None:
        tl, tc = self._scrubber, self._controls
        offset = self._offset_in(self._mark_row)
        cursor_x = offset + tl.x_for_index(cursor)
        width = tc.mark_in_btn.width()
        y = (self._mark_row.height() - tc.mark_in_btn.height()) // 2

        if cursor < in_point:
            start_x = offset + tl.x_for_index(in_point)
            tc.mark_in_btn.move(cursor_x - width // 2, y)
            tc.mark_out_btn.move(start_x - width // 2, y)
        elif cursor > out_point:
            end_x = offset + tl.x_for_index(out_point)
            tc.mark_in_btn.move(end_x - width // 2, y)
            tc.mark_out_btn.move(cursor_x - width // 2, y)
        else:
            tc.mark_in_btn.move(cursor_x - GAP // 2 - width, y)
            tc.mark_out_btn.move(cursor_x + GAP // 2, y)
        tc.mark_in_btn.setEnabled(cursor < out_point)
        tc.mark_out_btn.setEnabled(cursor > in_point)
        tc.mark_in_btn.show()
        tc.mark_out_btn.show()

    def _place_wrap(self, wrap_from: int, wrap_to: int, color: QColor) -> None:
        tl, tc = self._scrubber, self._controls
        offset = self._offset_in(self._wrap_row)
        x1 = offset + tl.x_for_index(wrap_from)
        x2 = offset + tl.x_for_index(wrap_to)
        y = (self._wrap_row.height() - tc.wrap_btn.height()) // 2
        tc.wrap_btn.move((x1 + x2) // 2 - tc.wrap_btn.width() // 2, y)
        if color != self._wrap_color:
            tc.wrap_btn.setStyleSheet(
                f"background: {color.name()}; border: 1px solid {BORDER_SUBTLE.name()};"
            )
            self._wrap_color = QColor(color)
        tc.wrap_btn.show()
        self._wrap_row.set_brace(x1, x2)
