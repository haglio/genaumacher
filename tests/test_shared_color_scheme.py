from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication
from shared_ui.colors import dress_application

_GUI = Path(__file__).resolve().parent.parent / "genaumacher" / "gui"

_HEX = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")


def _sources() -> list[Path]:
    files = sorted(_GUI.glob("*.py"))
    assert files, "no GUI modules found to check"
    return files


@pytest.mark.repo_check
def test_no_color_is_spelled_out_in_a_stylesheet():
    offenders = []
    for path in _sources():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                offenders.extend(f"{path.name}:{node.lineno} {match}" for match in _HEX.findall(node.value))
    assert not offenders, (
        "colors written in place instead of taken from shared_ui.colors: "
        + ", ".join(offenders)
    )


@pytest.mark.repo_check
def test_no_color_is_built_from_raw_channel_numbers():
    offenders = []
    for path in _sources():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = (node.func.attr if isinstance(node.func, ast.Attribute)
                    else getattr(node.func, "id", None))
            if name != "QColor" or not node.args:
                continue
            if all(isinstance(arg, ast.Constant) and isinstance(arg.value, (int, float))
                   for arg in node.args):
                offenders.append(f"{path.name}:{node.lineno}")
    assert not offenders, (
        "colors built from raw channels instead of taken from shared_ui.colors: "
        + ", ".join(offenders)
    )


@pytest.mark.repo_check
def test_the_chrome_reads_the_family_palette():
    importers = [
        path.name for path in _sources()
        if "shared_ui.colors" in path.read_text(encoding="utf-8")
    ]
    assert "main_window.py" in importers
    assert "button_bar.py" in importers


_PUSHBUTTON_RULE = re.compile(
    r"QPushButton(?P<state>:\w+)?\s*\{(?P<body>[^}]*)\}"
)
_BACKGROUND = re.compile(r"background(?:-color)?\s*:\s*(#[0-9a-fA-F]{3,6})")


def _button_backgrounds(sheet: str) -> dict[str, QColor]:
    found = {}
    for rule in _PUSHBUTTON_RULE.finditer(sheet):
        color = _BACKGROUND.search(rule.group("body"))
        if color:
            found[rule.group("state") or ""] = QColor(color.group(1))
    return found


def test_a_control_that_is_on_sits_on_a_lighter_ground():
    app = QApplication.instance()
    dress_application(app)

    backgrounds = _button_backgrounds(app.styleSheet())

    assert ":checked" in backgrounds, "no rule paints a button that is switched on"
    assert "" in backgrounds, "no rule paints a button at rest"
    assert backgrounds[":checked"].lightness() > backgrounds[""].lightness()
