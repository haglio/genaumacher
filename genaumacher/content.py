"""Content overlay — the private values this checkout needs at runtime.

The status file the Main Funestra publishes into is machine-specific, so it
comes from ``content.local.json`` (git-ignored) rather than from source.  A
committed ``content.example.json`` documents the shape and is what a fresh or
public checkout loads.  Where the library is belongs to the settings all of
Haglio shares (``app_support.haglio_settings``), not to this file.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app_support.overlay import overlay_path

from genaumacher.paths import PROJECT_DIR

LOCAL_CONTENT = PROJECT_DIR / "content.local.json"
EXAMPLE_CONTENT = PROJECT_DIR / "content.example.json"


def load_content(
    local_path: Path | None = None,
    example_path: Path | None = None,
) -> dict[str, Any]:
    """The local overlay's content when present, else the committed example."""
    return json.loads(overlay_path(
        LOCAL_CONTENT if local_path is None else local_path,
        EXAMPLE_CONTENT if example_path is None else example_path,
    ).read_text(encoding="utf-8"))
