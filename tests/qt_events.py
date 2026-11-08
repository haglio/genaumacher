
from __future__ import annotations

from PyQt6.QtWidgets import QApplication


def drain_a_tick_already_on_its_way() -> None:
    QApplication.processEvents()
