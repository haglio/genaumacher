from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FrameWindow:
    total_frames: int
    left_bound: int
    right_bound: int
    cursor: int
    base_step: int

    @property
    def count(self) -> int:
        return self.right_bound - self.left_bound + 1

    def hold_within(self, low: int, high: int) -> None:
        self.cursor = max(low, min(high, self.cursor))

    def contract_left(self, in_point: int) -> bool:
        if in_point - self.left_bound < self.base_step:
            return False
        self.left_bound += self.base_step
        self.cursor = max(self.cursor, self.left_bound)
        return True

    def contract_right(self, out_point: int) -> bool:
        if self.right_bound - out_point < self.base_step:
            return False
        self.right_bound -= self.base_step
        self.cursor = min(self.cursor, self.right_bound)
        return True

    def step_out_left(self) -> int:
        return max(0, self.left_bound - self.base_step)

    def step_out_right(self) -> int:
        return min(self.total_frames - 1, self.right_bound + self.base_step)

    def widen_left_to(self, start: int) -> None:
        self.left_bound = min(self.left_bound, start)

    def widen_right_to(self, end: int) -> None:
        self.right_bound = max(self.right_bound, end)

    def step_cursor_back(self, low: int, high: int) -> None:
        self.cursor = high if self.cursor <= low else self.cursor - 1

    def step_cursor_forward(self, low: int, high: int) -> None:
        self.cursor = low if self.cursor >= high else self.cursor + 1

    def carry_cursor(self, shift: int) -> None:
        self.cursor += shift

    def jump_to(self, idx: int) -> None:
        self.cursor = idx
