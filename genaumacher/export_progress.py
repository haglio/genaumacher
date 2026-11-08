from __future__ import annotations

from typing import Protocol


class ExportProgressListener(Protocol):
    def stage(self, text: str) -> None: ...

    def clip(self, fraction: float) -> None: ...

    def normalize(self, fraction: float) -> None: ...

    def audio(self, fraction: float) -> None: ...


_PROGRESS_PREFIX = "normalize-progress"


def progress_line(fraction: float) -> str:
    return f"{_PROGRESS_PREFIX} {fraction:.4f}"


def fraction_in(line: str) -> float | None:
    prefix, _, rest = line.partition(" ")
    if prefix != _PROGRESS_PREFIX:
        return None
    try:
        return float(rest)
    except ValueError:
        return None
