from __future__ import annotations

from pathlib import Path

from app_support.launcher import launchers
from app_support.process_identity import ProcessNamer
from app_support.process_identity_check import ProcessName, assert_the_process_is_named

from genaumacher.app import _name_this_process

PROJECT_DIR = Path(__file__).resolve().parent.parent
APP_NAME = "Genaumacher"
ROLE = "Genaumacher"

(LAUNCHER,) = [launcher for launcher in launchers(PROJECT_DIR)
               if launcher.file == "launch_genaumacher.vbs"]


def test_the_launcher_prefers_the_copy_named_for_this_app():
    assert LAUNCHER.named_interpreter == ProcessNamer(APP_NAME).exe_name(LAUNCHER.interpreter, ROLE)


def test_the_launcher_runs_the_console_interpreter_its_log_needs():
    assert LAUNCHER.interpreter == "python.exe"


def test_the_app_prepares_that_copy_for_next_time_its_row_the_apps_name_alone_one_app_one_window(tmp_path: Path):
    assert_the_process_is_named(
        _name_this_process, tmp_path,
        ProcessName(
            app_name=APP_NAME,
            role=ROLE,
            interpreter=LAUNCHER.interpreter,
            row=APP_NAME,
            icon=PROJECT_DIR / "genaumacher.ico",
        ),
    )
