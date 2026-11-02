"""The stretch of the video that is loaded, and where the cursor sits in it."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FrameWindow:
    """Owns `left_bound <= right_bound` and the cursor that roams inside it."""

    total_frames: int
    left_bound: int
    right_bound: int
    current: int
    base_step: int

    @property
    def count(self) -> int:
        return self.right_bound - self.left_bound + 1

    def hold_within(self, low: int, high: int) -> None:
        """Pull the cursor back inside `[low, high]`."""
        self.current = max(low, min(high, self.current))

    def contract_left(self, in_point: int) -> bool:
        """Drop one step off the left, unless that would eat the in-out.

        Returns whether the window moved, so the caller knows whether there is
        anything to prune, re-suggest or save.
        """
        if in_point - self.left_bound < self.base_step:
            return False
        self.left_bound += self.base_step
        self.current = max(self.current, self.left_bound)
        return True

    def contract_right(self, out_point: int) -> bool:
        """Drop one step off the right, unless that would eat the in-out."""
        if self.right_bound - out_point < self.base_step:
            return False
        self.right_bound -= self.base_step
        self.current = min(self.current, self.right_bound)
        return True

    def step_out_left(self) -> int:
        """Where a step further left would put `left_bound`."""
        return max(0, self.left_bound - self.base_step)

    def step_out_right(self) -> int:
        """Where a step further right would put `right_bound`."""
        return min(self.total_frames - 1, self.right_bound + self.base_step)

    def widen_left_to(self, start: int) -> None:
        """Take in `start`, once its frames are loaded.  Never narrows."""
        self.left_bound = min(self.left_bound, start)

    def widen_right_to(self, end: int) -> None:
        """Take in `end`, once its frames are loaded.  Never narrows."""
        self.right_bound = max(self.right_bound, end)

    def step_cursor_back(self, low: int, high: int) -> None:
        """One frame back, wrapping to `high` at `low`."""
        self.current = high if self.current <= low else self.current - 1

    def step_cursor_forward(self, low: int, high: int) -> None:
        """One frame on, wrapping to `low` at `high`."""
        self.current = low if self.current >= high else self.current + 1

    def carry_cursor(self, shift: int) -> None:
        """Move the cursor by the same amount the in-out just moved."""
        self.current += shift

    def jump_to(self, idx: int) -> None:
        """Put the cursor on `idx` -- what a click on the scrubber asks for."""
        self.current = idx
