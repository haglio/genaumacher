from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Suggestions:
    initial_start: int | None = None
    initial_end: int | None = None
    suggested_in: int | None = None
    suggested_out: int | None = None

    def moved(self, start: int, end: int) -> tuple[bool, bool]:
        return (
            self.initial_start is not None and start != self.initial_start,
            self.initial_end is not None and end != self.initial_end,
        )

    def offer(self, suggested_in: int | None, suggested_out: int | None) -> bool:
        if (suggested_in, suggested_out) == (self.suggested_in, self.suggested_out):
            return False
        self.suggested_in = suggested_in
        self.suggested_out = suggested_out
        return True
