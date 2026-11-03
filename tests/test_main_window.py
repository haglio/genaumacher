from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import QPoint, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QKeyEvent
from PyQt6.QtWidgets import QApplication, QPushButton, QWidget
from shared_ui.colors import dress_application
from shared_ui.fonts import FONT_UI
from shared_ui.preview import Preview
from shared_ui.spacing import BUTTON_SIZE

from genaumacher.gui.floating_controls import FloatingControlLayout
from genaumacher.gui.hotkeys import HOTKEYS
from genaumacher.gui.main_window import GenaumacherMainWindow, _WrapRow
from genaumacher.gui.scrubber_colors import SCRUBBER_BOUNDS
from genaumacher.gui.scrubber_controls import ScrubberControls
from genaumacher.gui.scrubber_widget import ScrubberWidget
from genaumacher.loop_modes import LoopMode
from genaumacher.wrap_modes import WrapMode


@pytest.fixture
def mock_state():
    state = MagicMock()
    state.session_name = "test_session"
    state.path = "/video.mp4"
    state.fps = 30.0
    state.total_frames = 300
    state.left_bound = 0
    state.right_bound = 100
    state.in_point = 20
    state.out_point = 80
    state.cursor = 50
    state.loop_mode = LoopMode.BASE_TIP_BASE
    state.wrap_mode = WrapMode.OVER_BOUNDS
    state.speed = 1.0
    state.loop_paused = False
    state.suggested_in = None
    state.suggested_out = None
    state.session_warning = ""
    return state


@pytest.fixture
def window(mock_state):
    return GenaumacherMainWindow(mock_state)


class TestConstruction:
    def test_has_video_panes(self, window):
        assert window.frame_at_cursor_pane is not None
        assert window.loop_preview_pane is not None

    def test_has_scrubber(self, window):
        assert window.scrubber is not None

    def test_has_button_bar(self, window):
        assert window.button_bar is not None

    def test_has_scrubber_controls(self, window):
        assert window.scrubber_controls is not None

    def test_has_legend(self, window):
        assert window.hotkey_reference is not None

    def test_window_title(self, window):
        assert window.windowTitle() == "Genaumacher"

    def test_a_preview_is_titled_for_the_feature_it_demos(self, mock_state):
        window = GenaumacherMainWindow(mock_state, preview=Preview(feature="the new loop"))

        assert window.windowTitle() == "Genaumacher — preview of the new loop"

    def test_the_compact_controls_all_come_out_the_same_size(self, window):
        tc, bb = window.scrubber_controls, window.button_bar
        compact = {
            (btn.width(), btn.height())
            for btn in (tc.shift_left_btn, tc.shift_right_btn,
                        tc.extend_left_btn, tc.contract_left_btn,
                        tc.contract_right_btn, tc.extend_right_btn,
                        tc.mark_in_btn, tc.mark_out_btn)
        }

        assert len(compact) == 1, compact
        narrow = compact.pop()[0]
        for wider in (bb.export_btn, tc.wrap_btn):
            assert wider.width() > narrow

    def test_the_transport_buttons_keep_the_familys_square(self, window):
        bb = window.button_bar

        for button in (bb.speed_down_btn, bb.speed_up_btn, bb.play_pause_btn):
            assert button.size() == QSize(BUTTON_SIZE, BUTTON_SIZE)

    def test_all_buttons_have_no_focus_policy(self, window):
        buttons = window.findChildren(QPushButton)
        assert len(buttons) > 0
        for btn in buttons:
            assert btn.focusPolicy() == Qt.FocusPolicy.NoFocus, (
                f"Button '{btn.text()}' has focus policy {btn.focusPolicy()}, expected NoFocus"
            )


_WINDOWS_MESSAGE_FACE = Path(os.environ["WINDIR"], "Fonts", "segoeui.ttf")


@pytest.fixture(params=[12, 18], ids=["windows_own_message_font", "this_computers_message_font"])
def window_in_windows_message_font(request, qapp, mock_state):
    face = QFontDatabase.addApplicationFont(str(_WINDOWS_MESSAGE_FACE))
    assert face != -1, _WINDOWS_MESSAGE_FACE
    font_before, sheet_before = qapp.font(), qapp.styleSheet()
    message_font = QFont(FONT_UI)
    message_font.setPixelSize(request.param)
    qapp.setFont(message_font)
    dress_application(qapp)
    window = GenaumacherMainWindow(mock_state)
    window.show()
    QApplication.processEvents()
    window.update_button_positions()
    yield window
    window.close()
    qapp.setStyleSheet(sheet_before)
    qapp.setFont(font_before)
    QFontDatabase.removeApplicationFont(face)


def _label_ink(button: QPushButton) -> QSize:
    drawn = button.grab().toImage()
    label = button.text()
    button.setText("")
    bare = button.grab().toImage()
    button.setText(label)
    xs, ys = zip(*((x, y) for y in range(drawn.height()) for x in range(drawn.width())
                   if drawn.pixel(x, y) != bare.pixel(x, y)), strict=True)
    return QSize(max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)


def _label_ink_with_room_to_spare(button: QPushButton) -> QSize:
    fixed = button.size()
    button.setFixedSize(fixed * 2)
    try:
        return _label_ink(button)
    finally:
        button.setFixedSize(fixed)


def test_a_fixed_size_button_shows_its_whole_label_in_the_font_windows_gives_it(
        window_in_windows_message_font):
    fixed_with_a_label = [button for button in window_in_windows_message_font.findChildren(QPushButton)
                          if button.text() and button.minimumSize() == button.maximumSize()]

    cut_off = sorted({button.text() for button in fixed_with_a_label
                      if _label_ink(button) != _label_ink_with_room_to_spare(button)})

    assert {"[", "]"} <= {button.text() for button in fixed_with_a_label}
    assert cut_off == []


class TestExportWiring:
    def test_export_creates_dialog_and_worker(self, window, mock_state):
        mock_worker = MagicMock()
        mock_dialog = MagicMock()

        with patch("genaumacher.gui.export_worker.ExportWorker", return_value=mock_worker) as MockWorker, \
             patch("genaumacher.gui.main_window.ExportDialog", return_value=mock_dialog) as MockDialog:
            window.start_export()

        MockDialog.assert_called_once_with(window)
        MockWorker.assert_called_once_with(mock_state)
        mock_dialog.show.assert_called_once()
        mock_worker.start.assert_called_once()


_DISPATCH_STATE = {
    "total_frames": 100, "left_bound": 10, "right_bound": 60,
    "in_point": 20, "out_point": 40, "cursor": 30, "base_step": 5,
}


def _press(window, key, text=""):
    window.keyPressEvent(
        QKeyEvent(QKeyEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier, text)
    )


def _no_prep(state):
    pass


def _with_suggestions(state):
    state.suggestions.offer(25, 35)


_KEY_BINDINGS = [
    ("left", Qt.Key.Key_Left, "", _no_prep, lambda s: s.cursor, 29),
    ("right", Qt.Key.Key_Right, "", _no_prep, lambda s: s.cursor, 31),
    ("space", Qt.Key.Key_Space, "", _no_prep, lambda s: s.loop_paused, True),
    ("a extends left", Qt.Key.Key_A, "a", _no_prep, lambda s: s.left_bound, 5),
    ("s contracts left", Qt.Key.Key_S, "s", _no_prep, lambda s: s.left_bound, 15),
    ("d contracts right", Qt.Key.Key_D, "d", _no_prep, lambda s: s.right_bound, 55),
    ("f extends right", Qt.Key.Key_F, "f", _no_prep, lambda s: s.right_bound, 65),
    ("i marks in", Qt.Key.Key_I, "i", _no_prep, lambda s: s.in_point, 30),
    ("[ marks in", Qt.Key.Key_BracketLeft, "[", _no_prep, lambda s: s.in_point, 30),
    ("o marks out", Qt.Key.Key_O, "o", _no_prep, lambda s: s.out_point, 30),
    ("] marks out", Qt.Key.Key_BracketRight, "]", _no_prep, lambda s: s.out_point, 30),
    ("9 accepts the suggested in", Qt.Key.Key_9, "9", _with_suggestions, lambda s: s.in_point, 25),
    ("( accepts the suggested in", Qt.Key.Key_ParenLeft, "(", _with_suggestions, lambda s: s.in_point, 25),
    ("0 accepts the suggested out", Qt.Key.Key_0, "0", _with_suggestions, lambda s: s.out_point, 35),
    (") accepts the suggested out", Qt.Key.Key_ParenRight, ")", _with_suggestions, lambda s: s.out_point, 35),
    (", shifts left", Qt.Key.Key_Comma, ",", _no_prep, lambda s: (s.in_point, s.out_point), (0, 20)),
    ("< shifts left", Qt.Key.Key_Less, "<", _no_prep, lambda s: (s.in_point, s.out_point), (0, 20)),
    (". shifts right", Qt.Key.Key_Period, ".", _no_prep, lambda s: (s.in_point, s.out_point), (40, 60)),
    ("> shifts right", Qt.Key.Key_Greater, ">", _no_prep, lambda s: (s.in_point, s.out_point), (40, 60)),
    ("w toggles the wrap range", Qt.Key.Key_W, "w", _no_prep, lambda s: s.wrap_mode, "yellow"),
    ("l cycles the loop mode", Qt.Key.Key_L, "l", _no_prep, lambda s: s.loop_mode, "tip-base-tip"),
    ("- slows down", Qt.Key.Key_Minus, "-", _no_prep, lambda s: s.speed, 0.75),
    ("_ slows down", Qt.Key.Key_Underscore, "_", _no_prep, lambda s: s.speed, 0.75),
    ("+ speeds up", Qt.Key.Key_Plus, "+", _no_prep, lambda s: s.speed, 1.25),
    ("= speeds up", Qt.Key.Key_Equal, "=", _no_prep, lambda s: s.speed, 1.25),
]


class TestKeyDispatch:
    @pytest.mark.parametrize(
        ("key", "text", "prepare", "observe", "expected"),
        [pytest.param(k, t, p, o, e, id=label) for label, k, t, p, o, e in _KEY_BINDINGS],
    )
    def test_a_key_makes_its_edit(self, make_state, key, text, prepare, observe, expected):
        state = make_state(**_DISPATCH_STATE)
        prepare(state)
        window = GenaumacherMainWindow(state)

        _press(window, key, text)

        assert observe(state) == expected

    def test_every_key_the_table_binds_has_a_case(self):
        exercised = {text or key for _, key, text, *_ in _KEY_BINDINGS}
        exercised |= {Qt.Key.Key_Return, Qt.Key.Key_Enter, "q"}

        bound = {key for s in HOTKEYS for key in s.keys}
        bound |= {code for s in HOTKEYS for code in s.qt_keys}

        assert bound == exercised

    def test_an_unbound_key_changes_nothing(self, make_state):
        state = make_state(**_DISPATCH_STATE)
        window = GenaumacherMainWindow(state)
        before = (state.cursor, state.in_point, state.out_point,
                  state.left_bound, state.right_bound, state.wrap_mode,
                  state.loop_mode, state.speed, state.persist_session.calls)

        _press(window, Qt.Key.Key_Z, "z")

        assert (state.cursor, state.in_point, state.out_point,
                state.left_bound, state.right_bound, state.wrap_mode,
                state.loop_mode, state.speed, state.persist_session.calls) == before

    @pytest.mark.parametrize("key", [Qt.Key.Key_Return, Qt.Key.Key_Enter])
    def test_enter_starts_an_export(self, make_state, key):
        state = make_state(**_DISPATCH_STATE)
        window = GenaumacherMainWindow(state)

        with patch("genaumacher.gui.export_worker.ExportWorker") as worker_cls, \
             patch("genaumacher.gui.main_window.ExportDialog") as dialog_cls:
            _press(window, key)

        dialog_cls.return_value.show.assert_called_once()
        worker_cls.return_value.start.assert_called_once()

    def test_q_closes_the_window(self, make_state):
        state = make_state(**_DISPATCH_STATE)
        window = GenaumacherMainWindow(state)
        window.show()
        assert window.isVisible()

        _press(window, Qt.Key.Key_Q, "q")

        assert not window.isVisible()


def _brace_ink(row, rendered) -> list[int]:
    image = rendered(row)
    background = image.pixelColor(row.width() - 2, 1).name()
    mid = row.height() // 2
    return [x for x in range(row.width()) if image.pixelColor(x, mid).name() != background]


def _brace_width(window, rendered) -> int:
    ink = _brace_ink(window.findChild(_WrapRow), rendered)
    return (max(ink) - min(ink)) if ink else 0


@pytest.fixture
def shown_window(mock_state):
    w = GenaumacherMainWindow(mock_state)
    w.resize(1520, 960)
    w.show()
    QApplication.processEvents()
    yield w
    w.close()


class TestDynamicPositioning:
    def test_shift_buttons_center_on_in_out(self, shown_window, mock_state):
        w = shown_window
        mock_state.in_point = 20
        mock_state.out_point = 80
        w.scrubber.set_bounds(0, 100)
        w.scrubber.set_in_out(20, 80)
        QApplication.processEvents()

        w.update_button_positions()

        tl = w.scrubber
        tc = w.scrubber_controls
        in_x = tl.mapToGlobal(QPoint(tl.x_for_index(20), 0)).x()
        out_x = tl.mapToGlobal(QPoint(tl.x_for_index(80), 0)).x()
        expected_center = (in_x + out_x) // 2

        left_global = tc.shift_left_btn.mapToGlobal(QPoint(tc.shift_left_btn.width(), 0)).x()
        right_global = tc.shift_right_btn.mapToGlobal(QPoint(0, 0)).x()
        actual_center = (left_global + right_global) // 2

        assert abs(actual_center - expected_center) < 10

    def test_shift_buttons_move_when_in_out_changes(self, shown_window, mock_state):
        w = shown_window
        tl = w.scrubber
        tc = w.scrubber_controls
        tl.set_bounds(0, 100)

        mock_state.in_point = 0
        mock_state.out_point = 20
        tl.set_in_out(0, 20)
        QApplication.processEvents()
        w.update_button_positions()
        left_pos = tc.shift_left_btn.mapToGlobal(QPoint(0, 0)).x()

        mock_state.in_point = 60
        mock_state.out_point = 80
        tl.set_in_out(60, 80)
        QApplication.processEvents()
        w.update_button_positions()
        right_pos = tc.shift_left_btn.mapToGlobal(QPoint(0, 0)).x()

        assert right_pos > left_pos + 100

    def test_mark_buttons_straddle_cursor_inside_active(self, shown_window, mock_state):
        w = shown_window
        mock_state.in_point = 20
        mock_state.out_point = 80
        mock_state.cursor = 50
        w.scrubber.set_bounds(0, 100)
        w.scrubber.set_in_out(20, 80)
        QApplication.processEvents()
        w.update_button_positions()

        tc = w.scrubber_controls
        in_right = tc.mark_in_btn.mapToGlobal(
            QPoint(tc.mark_in_btn.width(), 0)
        ).x()
        out_left = tc.mark_out_btn.mapToGlobal(QPoint(0, 0)).x()

        assert out_left >= in_right
        assert out_left - in_right < 20

    def test_mark_buttons_split_when_cursor_outside_active(self, shown_window, mock_state):
        w = shown_window
        mock_state.in_point = 40
        mock_state.out_point = 60
        mock_state.cursor = 10
        w.scrubber.set_bounds(0, 100)
        w.scrubber.set_in_out(40, 60)
        QApplication.processEvents()
        w.update_button_positions()

        tc = w.scrubber_controls
        in_x = tc.mark_in_btn.mapToGlobal(QPoint(0, 0)).x()
        out_x = tc.mark_out_btn.mapToGlobal(QPoint(0, 0)).x()
        assert out_x > in_x + 50

    def test_mark_in_disabled_at_active_end(self, shown_window, mock_state):
        w = shown_window
        mock_state.in_point = 20
        mock_state.out_point = 80
        mock_state.cursor = 80
        w.scrubber.set_bounds(0, 100)
        QApplication.processEvents()
        w.update_button_positions()

        assert not w.scrubber_controls.mark_in_btn.isEnabled()
        assert w.scrubber_controls.mark_out_btn.isEnabled()

    def test_wrap_button_color_changes_with_mode(self, shown_window, mock_state):
        w = shown_window
        w.scrubber.set_bounds(0, 100)
        w.scrubber.set_in_out(20, 80)
        QApplication.processEvents()

        mock_state.wrap_mode = WrapMode.OVER_BOUNDS
        w.update_button_positions()
        blue_style = w.scrubber_controls.wrap_btn.styleSheet()

        mock_state.wrap_mode = WrapMode.OVER_IN_OUT
        w.update_button_positions()
        yellow_style = w.scrubber_controls.wrap_btn.styleSheet()

        assert blue_style != yellow_style

    def test_a_tick_that_keeps_the_wrap_color_does_not_restyle_the_wrap_button(self, shown_window, mock_state):
        w = shown_window
        mock_state.wrap_mode = WrapMode.OVER_BOUNDS
        w.update_button_positions()
        button = w.scrubber_controls.wrap_btn
        restyled = []
        button.setStyleSheet = restyled.append

        w.update_button_positions()
        w.update_button_positions()

        assert restyled == []

    def test_wrap_brace_spans_loaded_range_in_blue_mode(self, shown_window, mock_state, rendered):
        w = shown_window
        mock_state.wrap_mode = WrapMode.OVER_BOUNDS
        mock_state.left_bound = 0
        mock_state.right_bound = 100
        w.scrubber.set_bounds(0, 100)
        QApplication.processEvents()
        w.update_button_positions()

        assert _brace_width(w, rendered) > w.scrubber.width() * 0.8

    def test_wrap_brace_narrows_to_in_out_in_yellow_mode(self, shown_window, mock_state, rendered):
        w = shown_window
        mock_state.wrap_mode = WrapMode.OVER_IN_OUT
        mock_state.in_point = 40
        mock_state.out_point = 60
        mock_state.left_bound = 0
        mock_state.right_bound = 100
        w.scrubber.set_bounds(0, 100)
        w.scrubber.set_in_out(40, 60)
        QApplication.processEvents()
        w.update_button_positions()

        brace_width = _brace_width(w, rendered)
        assert brace_width < w.scrubber.width() * 0.4


class TestWrapBrace:
    def test_it_draws_a_line_across_exactly_the_span_it_was_given(self, rendered):
        row = _WrapRow()
        row.resize(600, 30)

        row.set_brace(100, 400)

        ink = _brace_ink(row, rendered)
        assert (min(ink), max(ink)) == (100, 400)

    def test_an_empty_span_draws_nothing(self, rendered):
        row = _WrapRow()
        row.resize(600, 30)

        row.set_brace(300, 300)

        assert _brace_ink(row, rendered) == []


class TestFloatingControlsStandAlone:
    def test_it_places_the_wrap_button_over_the_range_it_is_given(self):
        host = QWidget()
        host.resize(600, 200)
        scrubber = ScrubberWidget(host)
        scrubber.resize(600, 24)
        scrubber.set_bounds(0, 100)
        controls = ScrubberControls(host)
        shift_row, mark_row = QWidget(host), QWidget(host)
        wrap_row = _WrapRow(host)
        for row in (shift_row, mark_row, wrap_row):
            row.resize(600, 32)
        layout = FloatingControlLayout(scrubber, controls, shift_row, mark_row, wrap_row)

        layout.place(in_point=20, out_point=80, cursor=50,
                     wrap_from=0, wrap_to=100, wrap_color=SCRUBBER_BOUNDS)

        center = controls.wrap_btn.x() + controls.wrap_btn.width() // 2
        assert abs(center - scrubber.width() // 2) <= 2
        assert SCRUBBER_BOUNDS.name() in controls.wrap_btn.styleSheet()


def test_no_floating_button_is_placed_before_the_scrubber_has_a_width():
    class _NoWidthYet:
        def __init__(self) -> None:
            self.asked: list[int] = []

        def width(self) -> int:
            return 0

        def x_for_index(self, index: int) -> int:
            self.asked.append(index)
            return 0

    scrubber = _NoWidthYet()
    layout = FloatingControlLayout(scrubber, None, None, None, None)

    layout.place(in_point=1, out_point=2, cursor=1, wrap_from=1, wrap_to=2, wrap_color=QColor())

    assert scrubber.asked == []
