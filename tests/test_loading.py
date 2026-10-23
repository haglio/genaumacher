from __future__ import annotations

from unittest.mock import patch

from shared_ui import loading_process
from shared_ui.loading_window import Loading, LoadingCanceled

from genaumacher import app
from genaumacher.window_icons import genaumacher_icon_path


class _Loading:
    def __init__(self, happened: list[str], *, canceled: bool = False):
        self._happened = happened
        self._canceled = canceled

    def say(self, step: str) -> None:
        self._happened.append(f"said {step}")
        if self._canceled:
            raise LoadingCanceled

    def done(self) -> None:
        self._happened.append("done")


def _launch(happened: list[str], loading: _Loading) -> int:
    with patch.object(Loading, "at_the_click", return_value=loading) as opened, \
         patch.object(app, "launch_state", side_effect=lambda: happened.append("launcher") or None), \
         patch.object(app, "_set_windows_app_user_model_id"), \
         patch.object(app, "_name_this_process"), \
         patch.object(app, "_init_logger"):
        result = app.main()
    happened.append(f"opened with {opened.call_count}")
    return result


def test_the_loading_screen_comes_up_at_the_click_and_goes_before_the_launcher_opens():
    happened: list[str] = []

    assert _launch(happened, _Loading(happened)) == 0
    assert happened == [*(f"said {step}" for step, _weight in app.STEPS), "done", "launcher", "opened with 1"]


def test_esc_on_the_loading_screen_opens_no_launcher():
    happened: list[str] = []

    assert _launch(happened, _Loading(happened, canceled=True)) == 0
    assert "launcher" not in happened


def test_the_loading_screen_runs_in_a_process_of_its_own_wearing_genaumachers_taskbar_button(
        monkeypatch):
    monkeypatch.setattr(app.sys, "platform", "win32")

    with patch.object(loading_process.LoadingProcess, "open") as opened:
        app.open_the_loading_screen(None)

    opened.assert_called_once_with(
        caption="Genaumacher Loading", wordmark="Genaumacher", icon=genaumacher_icon_path(), preview=None,
        steps=app.STEPS, cancel_hint="Press Esc to cancel opening Genaumacher",
        app_id=app.APP_USER_MODEL_ID)


def test_off_windows_the_loading_screen_wears_no_taskbar_identity(monkeypatch):
    monkeypatch.setattr(app.sys, "platform", "linux")

    with patch.object(loading_process.LoadingProcess, "open") as opened:
        app.open_the_loading_screen(None)

    assert opened.call_args.kwargs["app_id"] is None
