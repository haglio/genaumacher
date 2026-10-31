"""Seconds to and from the hh:mm:ss.sss the user types and the labels show."""

from __future__ import annotations


def parse_timestamp(ts: str) -> float:
    match ts.strip().split(":"):
        case [hours, minutes, seconds]:
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    raise ValueError("Timestamp must be hh:mm:ss or hh:mm:ss.sss")


def format_seconds(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    remaining = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{remaining:06.3f}"
