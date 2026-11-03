from __future__ import annotations

from itertools import product
from typing import TYPE_CHECKING

from .loop_modes import LoopMode
from .suggestion_search import (
    best_duplicate_match_index,
    best_turning_point_index,
    pair_transition_score,
)

if TYPE_CHECKING:
    from .state import VideoState


def _out_point_for_the_in_point(state: VideoState, use_turning_point: bool) -> int | None:
    if use_turning_point:
        candidate = best_turning_point_index(state, state.in_point, direction=+1)
    else:
        match_idx = best_duplicate_match_index(state, state.in_point, direction=+1)
        candidate = None if match_idx is None else match_idx - 1
    if candidate is not None and state.in_point < candidate <= state.right_bound:
        return candidate
    return None


def _in_point_for_the_out_point(state: VideoState, use_turning_point: bool) -> int | None:
    if use_turning_point:
        candidate = best_turning_point_index(state, state.out_point, direction=-1)
    else:
        match_idx = best_duplicate_match_index(state, state.out_point, direction=-1)
        candidate = None if match_idx is None else match_idx + 1
    if candidate is not None and state.left_bound <= candidate < state.out_point:
        return candidate
    return None


def _best_pair_around_the_anchors(state: VideoState) -> tuple[int, int]:
    anchor_in = state.clip.anchor_in if state.clip.anchor_in is not None else state.in_point
    anchor_out = state.clip.anchor_out if state.clip.anchor_out is not None else state.out_point
    best_pair = (state.in_point, state.out_point)
    best_score = pair_transition_score(state, *best_pair)
    for start, end in product(range(anchor_in - 2, anchor_in + 3), range(anchor_out - 2, anchor_out + 3)):
        if not state.left_bound <= start < end <= state.right_bound:
            continue
        score = pair_transition_score(state, start, end)
        if score > best_score + 1e-6:
            best_score = score
            best_pair = (start, end)
    return best_pair


def update_loop_suggestions(state: VideoState) -> None:
    start_changed, end_changed = state.suggestions.moved(state.in_point, state.out_point)
    use_turning_point = state.loop_mode in {LoopMode.BASE_TIP, LoopMode.TIP_BASE}

    suggested_out = _out_point_for_the_in_point(state, use_turning_point) if start_changed else None
    suggested_in = _in_point_for_the_out_point(state, use_turning_point) if end_changed else None
    if start_changed and end_changed and not use_turning_point:
        suggested_in, suggested_out = _best_pair_around_the_anchors(state)

    if state.suggestions.offer(suggested_in, suggested_out):
        state.bump_render()
