from __future__ import annotations

from typing import TYPE_CHECKING

from .loop_modes import LoopMode
from .suggestion_search import (
    best_duplicate_match_index,
    best_turning_point_index,
    pair_transition_score,
)

if TYPE_CHECKING:
    from .state import VideoState


def update_loop_suggestions(state: VideoState) -> None:
    start_changed, end_changed = state.suggestions.moved(state.in_point, state.out_point)
    use_turning_point = state.loop_mode in {LoopMode.BASE_TIP, LoopMode.TIP_BASE}

    suggested_in: int | None = None
    suggested_out: int | None = None

    if start_changed:
        if use_turning_point:
            candidate = best_turning_point_index(state, state.in_point, direction=+1)
            if candidate is not None and state.in_point < candidate <= state.right_bound:
                suggested_out = candidate
        else:
            match_idx = best_duplicate_match_index(state, state.in_point, direction=+1)
            if match_idx is not None:
                candidate = match_idx - 1
                if state.in_point < candidate <= state.right_bound:
                    suggested_out = candidate

    if end_changed:
        if use_turning_point:
            candidate = best_turning_point_index(state, state.out_point, direction=-1)
            if candidate is not None and state.left_bound <= candidate < state.out_point:
                suggested_in = candidate
        else:
            match_idx = best_duplicate_match_index(state, state.out_point, direction=-1)
            if match_idx is not None:
                candidate = match_idx + 1
                if state.left_bound <= candidate < state.out_point:
                    suggested_in = candidate

    if start_changed and end_changed and not use_turning_point:
        anchor_in = state.clip.anchor_in if state.clip.anchor_in is not None else state.in_point
        anchor_out = state.clip.anchor_out if state.clip.anchor_out is not None else state.out_point
        best_pair = (state.in_point, state.out_point)
        best_score = pair_transition_score(state, *best_pair)
        for start_shift in range(-2, 3):
            candidate_start = anchor_in + start_shift
            if candidate_start < state.left_bound or candidate_start > state.right_bound:
                continue
            for end_shift in range(-2, 3):
                candidate_end = anchor_out + end_shift
                if candidate_end < state.left_bound or candidate_end > state.right_bound:
                    continue
                if candidate_start >= candidate_end:
                    continue
                score = pair_transition_score(state, candidate_start, candidate_end)
                if score > best_score + 1e-6:
                    best_score = score
                    best_pair = (candidate_start, candidate_end)
        suggested_in, suggested_out = best_pair

    if state.suggestions.offer(suggested_in, suggested_out):
        state.bump_render()
