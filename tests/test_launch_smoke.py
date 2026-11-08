from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from app_support.launch_smoke import (
    assert_an_unresolvable_import_is_caught,
    assert_every_import_resolves,
    assert_the_walk_reached,
    launch_imports,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "genaumacher"

LAUNCH_FILES = (
    REPO_ROOT / PACKAGE / "__main__.py",
    REPO_ROOT / PACKAGE / "app.py",
)

_REACHED_ONLY_FROM_INSIDE_MAIN = ("genaumacher.gui.app",)
_A_PUBLIC_CHECKOUT_AND_THE_GATE_HAVE_ONLY_THE_EXAMPLE_SO_THE_LAUNCH_COMES_UP_ON_IT = (
    "import genaumacher.content as _content",
    "_content.LOCAL_CONTENT = _content.EXAMPLE_CONTENT",
)


def _run_the_launchs_way(statements: list[str]) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["QT_QPA_PLATFORM"] = "offscreen"

    driver = "\n".join([*_A_PUBLIC_CHECKOUT_AND_THE_GATE_HAVE_ONLY_THE_EXAMPLE_SO_THE_LAUNCH_COMES_UP_ON_IT, *statements])
    return subprocess.run(
        [sys.executable, "-c", driver],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_launch_imports_everything_it_names_a_failed_launch_shows_nothing_but_a_line_in_the_launchers_log():
    assert_every_import_resolves(
        _run_the_launchs_way, launch_imports(PACKAGE, LAUNCH_FILES))


def test_the_walk_reaches_the_imports_buried_in_main():
    assert_the_walk_reached(
        launch_imports(PACKAGE, LAUNCH_FILES), _REACHED_ONLY_FROM_INSIDE_MAIN)


def test_a_launch_import_that_cannot_resolve_fails_here():
    assert_an_unresolvable_import_is_caught(
        _run_the_launchs_way, launch_imports(PACKAGE, LAUNCH_FILES),
        "genaumacher.state")


def _imports_in_a_fresh_interpreter(module: str, *watched: str) -> dict[str, bool]:
    done = _run_the_launchs_way([
        f"import sys, {module}",
        f"print({{name: name in sys.modules for name in {list(watched)!r}}})",
    ])
    assert done.returncode == 0, done.stderr
    return eval(done.stdout.strip())  # noqa: S307


def test_the_editor_window_is_imported_only_once_the_launcher_has_a_session_to_open():
    assert _imports_in_a_fresh_interpreter("genaumacher.app", "genaumacher.gui.app") == {
        "genaumacher.gui.app": False}


def test_the_export_steps_and_their_progress_import_without_qt_so_they_are_tested_with_no_thread_and_no_window():
    for module in ("genaumacher.export_pipeline", "genaumacher.export_progress", "genaumacher.export_steps"):
        assert _imports_in_a_fresh_interpreter(module, "PyQt6") == {"PyQt6": False}, module


def test_the_windows_dressing_knows_nothing_of_a_video_state():
    assert _imports_in_a_fresh_interpreter("genaumacher.gui.main_window_style", "genaumacher.state") == {
        "genaumacher.state": False}
