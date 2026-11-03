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
    return json.loads(overlay_path(
        LOCAL_CONTENT if local_path is None else local_path,
        EXAMPLE_CONTENT if example_path is None else example_path,
    ).read_text(encoding="utf-8"))
