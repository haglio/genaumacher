from __future__ import annotations

import logging
import sys

from app_support.logging_utils import configure_logging, install_exception_logging
from app_support.process_identity import ProcessNamer
from app_support.win32 import set_app_user_model_id, stamp_pinned_shortcuts
from shared_ui.preview import Preview, preview_of, taskbar_identity, window_title
from shared_ui.preview_icon import app_icon

from .interpolator_environment import complaints
from .paths import PROJECT_DIR
from .session_launch import launch_state
from .window_icons import genaumacher_icon_path

APP_USER_MODEL_ID = "FunTime.Genaumacher"
STEPS = (("Loading Genaumacher...", 1.0),)


def open_the_loading_screen(preview: Preview | None):
    from shared_ui.loading_process import LoadingProcess  # noqa: PLC0415

    return LoadingProcess.open(
        caption="Genaumacher Loading", wordmark="Genaumacher", icon=genaumacher_icon_path(), preview=preview,
        steps=STEPS, cancel_hint="Press Esc to cancel opening Genaumacher",
        app_id=taskbar_identity(APP_USER_MODEL_ID, preview) if sys.platform == "win32" else None,
    )


def _set_windows_app_user_model_id(preview: Preview | None) -> None:
    if sys.platform != "win32":
        return
    try:
        set_app_user_model_id(taskbar_identity(APP_USER_MODEL_ID, preview))
    except OSError:
        logging.getLogger(__name__).debug(
            "Could not set the AppUserModelID", exc_info=True)
    stamp_pinned_shortcuts(APP_USER_MODEL_ID, ["Genaumacher"])


def _init_logger() -> logging.Logger:
    log_path = PROJECT_DIR / "state" / "genaumacher.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = configure_logging("genaumacher", log_path, console=False)
    install_exception_logging(logger)
    return logger


def _report_interpolator_environment(logger: logging.Logger) -> None:
    for said in complaints():
        logger.warning("Frame interpolator: %s", said)


def _name_this_process() -> None:
    ProcessNamer("Genaumacher", icon=PROJECT_DIR / "genaumacher.ico").name_this_process(
        "Genaumacher", interpreter="python.exe")


def main() -> int:
    preview = preview_of(PROJECT_DIR)
    _set_windows_app_user_model_id(preview)
    _name_this_process()
    logger = _init_logger()
    _report_interpolator_environment(logger)
    try:
        # Qt loads here, so a failure to load it reaches the handler below.
        from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: PLC0415

        _app = QApplication.instance() or QApplication(sys.argv)
        _app.setWindowIcon(app_icon(genaumacher_icon_path(), preview))
        from shared_ui.loading_window import Loading, LoadingCanceled  # noqa: PLC0415

        loading = Loading.at_the_click(_app, logger, lambda: open_the_loading_screen(preview))
        try:
            for step, _weight in STEPS:
                loading.say(step)
        except LoadingCanceled:
            return 0
        loading.done()
        state = launch_state()
        if state is None:
            return 0

        from .gui.app import GenaumacherApp  # noqa: PLC0415

        genaumacher_app = GenaumacherApp(state, preview=preview)
        return genaumacher_app.run()
    except Exception as exc:
        logger.exception("Genaumacher crashed")
        try:
            # What failed may be the import of Qt itself.
            from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: PLC0415

            _app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, window_title("Genaumacher", preview), f"ERROR: {exc}")
        except Exception:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1
