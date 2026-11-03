from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ClipRange:
    start: int
    end: int
    anchor_in: int | None = None
    anchor_out: int | None = None

    @property
    def span(self) -> int:
        return self.end - self.start

    def mark_in(self, at: int) -> bool:
        if at >= self.end:
            return False
        self.start = at
        self.anchor_in = at
        return True

    def mark_out(self, at: int) -> bool:
        if at <= self.start:
            return False
        self.end = at
        self.anchor_out = at
        return True

    def shift(self, by: int) -> None:
        self.start += by
        self.end += by
        self.anchor_in = self.start
        self.anchor_out = self.end
