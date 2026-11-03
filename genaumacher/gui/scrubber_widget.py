from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget
from shared_ui.colors import BG_PRIMARY

from .scrubber_colors import (
    BORDER_SCRUBBER,
    BORDER_TICK,
    SCRUBBER_BOUNDS,
    SCRUBBER_CURSOR,
    SCRUBBER_IN_OUT,
    SCRUBBER_LOOP,
    SCRUBBER_SUGGESTED_IN,
    SCRUBBER_SUGGESTED_OUT,
)


class ScrubberWidget(QWidget):
    cursor_jumped = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.left_bound: int = 0
        self.right_bound: int = 0
        self.in_point: int = 0
        self.out_point: int = 0
        self.cursor_pos: int = 0
        self.loop_pos: int = 0
        self.suggested_in: int | None = None
        self.suggested_out: int | None = None
        self.setMinimumHeight(24)
        self.setFixedHeight(24)

    def set_bounds(self, start: int, end: int) -> None:
        self.left_bound = start
        self.right_bound = end
        self.update()

    def set_in_out(self, start: int, end: int) -> None:
        self.in_point = start
        self.out_point = end
        self.update()

    def set_cursor_position(self, idx: int) -> None:
        self.cursor_pos = idx
        self.update()

    def set_loop_position(self, idx: int) -> None:
        self.loop_pos = idx
        self.update()

    def set_suggestions(self, in_idx: int | None, out_idx: int | None) -> None:
        self.suggested_in = in_idx
        self.suggested_out = out_idx
        self.update()

    def x_for_index(self, idx: int) -> int:
        count = max(1, self.right_bound - self.left_bound)
        frac = (idx - self.left_bound) / count
        return round(frac * self.width())

    def index_for_x(self, x: int) -> int:
        x = max(0, min(self.width(), x))
        count = max(1, self.right_bound - self.left_bound)
        frac = x / self.width() if self.width() > 0 else 0.0
        idx = self.left_bound + round(frac * count)
        return max(self.left_bound, min(self.right_bound, idx))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            idx = self.index_for_x(int(event.position().x()))
            self.cursor_jumped.emit(idx)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        p.fillRect(self.rect(), BG_PRIMARY)

        lx1 = self.x_for_index(self.left_bound)
        lx2 = self.x_for_index(self.right_bound)
        p.fillRect(lx1, 0, lx2 - lx1, h, SCRUBBER_BOUNDS)

        ax1 = self.x_for_index(self.in_point)
        ax2 = self.x_for_index(self.out_point)
        p.fillRect(ax1, 0, ax2 - ax1, h, SCRUBBER_IN_OUT)

        tick_pen = QPen(BORDER_TICK, 1)
        p.setPen(tick_pen)
        for i in range(self.left_bound, self.right_bound + 1):
            tx = self.x_for_index(i)
            p.drawPoint(tx, 2)
            p.drawPoint(tx, h - 3)

        if self.suggested_in is not None:
            self._draw_dotted_line(p, self.x_for_index(self.suggested_in), h, SCRUBBER_SUGGESTED_IN)
        if self.suggested_out is not None:
            self._draw_dotted_line(p, self.x_for_index(self.suggested_out), h, SCRUBBER_SUGGESTED_OUT)

        loop_x = self.x_for_index(self.loop_pos)
        p.fillRect(loop_x - 1, 0, 3, h, SCRUBBER_LOOP)

        cur_x = self.x_for_index(self.cursor_pos)
        p.fillRect(cur_x - 1, 0, 3, h, SCRUBBER_CURSOR)

        pen = QPen(BORDER_SCRUBBER, 1)
        p.setPen(pen)
        p.drawRect(0, 0, w - 1, h - 1)

        p.end()

    def _draw_dotted_line(self, p: QPainter, x: int, h: int, color: QColor) -> None:
        pen = QPen(color, 2, Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.drawLine(x, 0, x, h)
