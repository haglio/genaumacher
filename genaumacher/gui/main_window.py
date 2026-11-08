from __future__ import annotations

import contextlib
import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QPainter, QPen
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)
from shared_ui.colors import BORDER_DEFAULT
from shared_ui.fonts import FONT_UI, SIZE_HEADING, make_font
from shared_ui.preview import Preview, window_title
from shared_ui.spacing import BUTTON_GAP, GAP_MEDIUM, GAP_SMALL, MARGIN_STANDARD

from genaumacher.frame_store import safe_frame
from genaumacher.playback import current_loop_frame_index, loop_preview_indices
from genaumacher.timecode import format_seconds
from genaumacher.wrap_modes import WrapMode, wrap_bounds

from .button_bar import ButtonBar
from .export_dialog import ExportDialog
from .export_worker import connect_export
from .floating_controls import FloatingControlLayout, FloatingMarks
from .frame_converter import bgr_to_qimage, scale_to_fit
from .hotkey_reference import HotkeyReferenceWidget
from .hotkeys import BY_NAME, hotkey_for, hotkey_reference_rows
from .main_window_style import (
    LABEL_STYLE,
    WARNING_STYLE,
    dress_controls,
    refuse_focus,
    small_font,
)
from .scrubber_colors import SCRUBBER_BOUNDS, SCRUBBER_IN_OUT
from .scrubber_controls import ScrubberControls
from .scrubber_widget import ScrubberWidget
from .video_pane import VideoPane

if TYPE_CHECKING:
    from genaumacher.state import VideoState

_A_FRAME_THE_CACHE_LACKS = (KeyError, IndexError)
_A_FRAME_THE_DECODER_NEVER_PRODUCED = (RuntimeError,)
_UNDECODABLE = _A_FRAME_THE_CACHE_LACKS + _A_FRAME_THE_DECODER_NEVER_PRODUCED


class _WrapRow(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._x1 = 0
        self._x2 = 0

    def set_brace(self, x1: int, x2: int) -> None:
        self._x1 = x1
        self._x2 = x2
        self.update()

    def paintEvent(self, event) -> None:
        if self._x2 <= self._x1:
            return
        p = QPainter(self)
        pen = QPen(BORDER_DEFAULT, 1)
        p.setPen(pen)
        y = self.height() // 2
        p.drawLine(self._x1, y, self._x2, y)
        p.drawLine(self._x1, y - 8, self._x1, y + 8)
        p.drawLine(self._x2, y - 8, self._x2, y + 8)
        p.end()


def _small_label(text: str = "") -> QLabel:
    label = QLabel(text)
    label.setFont(small_font())
    label.setStyleSheet(LABEL_STYLE)
    return label


def _pane_column(heading: str, pane: VideoPane) -> QVBoxLayout:
    header = QLabel(heading)
    header.setFont(make_font(FONT_UI, SIZE_HEADING))
    header.setStyleSheet(LABEL_STYLE)
    header.setAlignment(Qt.AlignmentFlag.AlignCenter)
    header.setContentsMargins(0, GAP_MEDIUM, 0, GAP_MEDIUM)

    column = QVBoxLayout()
    column.setSpacing(GAP_SMALL)
    column.addWidget(header)
    column.addWidget(pane, stretch=1)
    return column


def _button_row_of(*buttons: QWidget) -> QWidget:
    row = QWidget()
    row.setFixedHeight(32)
    for button in buttons:
        button.setParent(row)
    return row


class GenaumacherMainWindow(QMainWindow):
    closed = pyqtSignal()

    def __init__(self, state: VideoState, parent=None, *, preview: Preview | None = None):
        super().__init__(parent)
        self._state = state
        self.setWindowTitle(window_title("Genaumacher", preview))
        self.setMinimumSize(900, 600)
        self.resize(1520, 960)

        self.frame_at_cursor_pane = VideoPane()
        self.loop_preview_pane = VideoPane()

        self.scrubber = ScrubberWidget()

        self.button_bar = ButtonBar()
        self.scrubber_controls = ScrubberControls()
        self.hotkey_reference = HotkeyReferenceWidget(hotkey_reference_rows())

        self._make_labels(state)
        self._wire_controls()

        central = QWidget()
        self.setCentralWidget(central)
        self._lay_out(central)

        self._floating = FloatingControlLayout(
            self.scrubber, self.scrubber_controls, self._shift_row, self._mark_row, self._wrap_row
        )

        dress_controls(central, self.button_bar, self.scrubber_controls)
        refuse_focus(self)

    def _make_labels(self, state: VideoState) -> None:
        self.session_label = QLabel(state.session_name)
        self.session_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.session_label.setFont(make_font(FONT_UI, SIZE_HEADING, bold=True))

        self.file_info_label = _small_label(
            f"file: {os.path.basename(state.path)}    fps: {state.fps:.3f}"
        )
        self.file_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.cursor_label = _small_label()
        self.loop_label = _small_label()
        self.speed_label = _small_label()

        self.warning_label = QLabel()
        self.warning_label.setFont(small_font())
        self.warning_label.setStyleSheet(WARNING_STYLE)
        self.warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def _wire_controls(self) -> None:
        for signal, name in (
            (self.button_bar.speed_down_clicked, "speed_down"),
            (self.button_bar.speed_up_clicked, "speed_up"),
            (self.button_bar.play_pause_clicked, "play_pause"),
            (self.button_bar.export_clicked, "export"),
            (self.scrubber_controls.extend_left_clicked, "extend_left"),
            (self.scrubber_controls.contract_left_clicked, "contract_left"),
            (self.scrubber_controls.extend_right_clicked, "extend_right"),
            (self.scrubber_controls.contract_right_clicked, "contract_right"),
            (self.scrubber_controls.shift_left_clicked, "shift_left"),
            (self.scrubber_controls.shift_right_clicked, "shift_right"),
            (self.scrubber_controls.mark_in_clicked, "mark_in"),
            (self.scrubber_controls.mark_out_clicked, "mark_out"),
            (self.scrubber_controls.wrap_clicked, "toggle_wrap"),
            (self.scrubber_controls.loop_mode_clicked, "cycle_loop_mode"),
        ):
            signal.connect(self._runs(name))

        self.scrubber.cursor_jumped.connect(self._on_scrubber_click)

    def _lay_out(self, central: QWidget) -> None:
        panes_row = self._panes_row()
        info_row = self._info_row()
        scrubber_row = self._scrubber_row()
        mode_row = self._loop_mode_row()

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(MARGIN_STANDARD, GAP_SMALL, MARGIN_STANDARD, GAP_SMALL)
        main_layout.setSpacing(GAP_SMALL)
        main_layout.addWidget(self.session_label)
        main_layout.addWidget(self.file_info_label)
        main_layout.addLayout(panes_row, stretch=1)
        main_layout.addLayout(info_row)
        main_layout.addWidget(self._shift_row)
        main_layout.addLayout(scrubber_row)
        main_layout.addWidget(self._mark_row)
        main_layout.addWidget(self._wrap_row)
        main_layout.addLayout(mode_row)
        main_layout.addWidget(self.warning_label)
        main_layout.addWidget(self.hotkey_reference)

    def _panes_row(self) -> QHBoxLayout:
        panes_row = QHBoxLayout()
        panes_row.addLayout(_pane_column("frame at cursor", self.frame_at_cursor_pane), stretch=1)
        panes_row.addLayout(_pane_column("loop preview", self.loop_preview_pane), stretch=1)
        return panes_row

    def _info_row(self) -> QHBoxLayout:
        bb = self.button_bar

        left_info = QVBoxLayout()
        left_info.setSpacing(0)
        left_info.addWidget(self.cursor_label)
        left_info.addStretch()

        right_info = QVBoxLayout()
        right_info.setSpacing(0)
        right_info.addWidget(self.loop_label)
        right_info.addWidget(self.speed_label)

        btn_group = QHBoxLayout()
        btn_group.setSpacing(BUTTON_GAP)
        btn_group.addWidget(bb.speed_down_btn)
        btn_group.addWidget(bb.speed_up_btn)
        btn_group.addWidget(bb.play_pause_btn)
        btn_group.addWidget(bb.export_btn)

        right_side = QHBoxLayout()
        right_side.addLayout(right_info)
        right_side.addStretch()
        right_side.addLayout(btn_group)

        info_row = QHBoxLayout()
        info_row.addLayout(left_info, stretch=1)
        info_row.addLayout(right_side, stretch=1)
        return info_row

    def _scrubber_row(self) -> QHBoxLayout:
        tc = self.scrubber_controls

        self._shift_row = _button_row_of(tc.shift_left_btn, tc.shift_right_btn)

        scrubber_row = QHBoxLayout()
        scrubber_row.addWidget(tc.extend_left_btn)
        scrubber_row.addWidget(tc.contract_left_btn)
        scrubber_row.addWidget(self.scrubber, stretch=1)
        scrubber_row.addWidget(tc.contract_right_btn)
        scrubber_row.addWidget(tc.extend_right_btn)

        self._mark_row = _button_row_of(tc.mark_in_btn, tc.mark_out_btn)

        self._wrap_row = _WrapRow()
        self._wrap_row.setFixedHeight(36)
        tc.wrap_btn.setParent(self._wrap_row)
        return scrubber_row

    def _loop_mode_row(self) -> QHBoxLayout:
        mode_row = QHBoxLayout()
        mode_row.addStretch()
        mode_row.addWidget(self.scrubber_controls.loop_mode_btn)
        mode_row.addStretch()
        return mode_row

    @property
    def state(self) -> VideoState:
        return self._state

    def update_button_positions(self) -> None:
        state = self._state
        wrap_from, wrap_to = wrap_bounds(state)
        self._floating.place(FloatingMarks(
            in_point=state.in_point,
            out_point=state.out_point,
            cursor=state.cursor,
            wrap_from=wrap_from,
            wrap_to=wrap_to,
            wrap_color=(
                SCRUBBER_BOUNDS
                if state.wrap_mode is WrapMode.OVER_BOUNDS
                else SCRUBBER_IN_OUT
            ),
        ))

    def render(self, state: VideoState) -> None:
        loop_idx, loop_position = self._draw_frames(state)
        self._draw_scrubber(state, loop_idx)
        self._write_labels(state, loop_idx, loop_position)
        self.button_bar.set_playing(not state.loop_paused)
        self.scrubber_controls.set_loop_mode(state.loop_mode)
        self.warning_label.setText(state.session_warning)
        self.update_button_positions()

    def _draw_frames(self, state: VideoState) -> tuple[int, int | None]:
        loop_idx = state.in_point
        with contextlib.suppress(*_UNDECODABLE):
            loop_idx = current_loop_frame_index(state)
            self._fill(self.loop_preview_pane, safe_frame(state, loop_idx))
        with contextlib.suppress(*_UNDECODABLE):
            self._fill(self.frame_at_cursor_pane, safe_frame(state, state.cursor))
        return loop_idx, state.paused_loop_pos

    def _fill(self, pane: VideoPane, frame) -> None:
        image = bgr_to_qimage(frame)
        pane.set_frame(scale_to_fit(image, pane.width(), pane.height()))

    def _draw_scrubber(self, state: VideoState, loop_idx: int) -> None:
        self.scrubber.set_bounds(state.left_bound, state.right_bound)
        self.scrubber.set_in_out(state.in_point, state.out_point)
        self.scrubber.set_cursor_position(state.cursor)
        self.scrubber.set_loop_position(loop_idx)
        self.scrubber.set_suggestions(state.suggested_in, state.suggested_out)

    def _write_labels(self, state: VideoState, loop_idx: int, loop_position: int | None) -> None:
        cursor_max = state.loaded_count - 1
        width = max(2, len(str(max(0, cursor_max))))
        self.cursor_label.setText(
            f"cursor: {state.cursor - state.left_bound:0{width}d}/{cursor_max}"
            f" @ {format_seconds(state.cursor / state.fps)}"
        )

        preview_total = len(loop_preview_indices(state))
        width = max(2, len(str(max(0, preview_total))))
        self.loop_label.setText(
            f"loop frame: {loop_position:0{width}d}/{preview_total}"
            f" @ {format_seconds(loop_idx / state.fps)}"
        )

        playing = "playing" if not state.loop_paused else "paused"
        self.speed_label.setText(f"speed: {state.speed:.2f}x ({playing})")

    def closeEvent(self, event) -> None:
        super().closeEvent(event)
        self.closed.emit()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        hotkey = hotkey_for(event.key(), event.text().lower())
        if hotkey is None:
            super().keyPressEvent(event)
            return
        hotkey.action(self)

    def start_export(self) -> None:
        dialog = ExportDialog(self)
        worker = connect_export(self._state, dialog)
        self._export_worker = worker
        dialog.show()
        worker.start()

    def _runs(self, name: str):
        hotkey = BY_NAME[name]
        return lambda: hotkey.action(self)

    def _on_scrubber_click(self, idx: int) -> None:
        self._state.window.jump_to(idx)
        self._state.bump_render()
