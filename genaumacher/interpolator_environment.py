from __future__ import annotations

import shutil
from pathlib import Path

from genaumacher.paths import PROJECT_DIR

VENDORED_EXE = Path("tools") / "rife-ncnn-vulkan-20221029-windows" / "rife-ncnn-vulkan.exe"
MODEL_DIR_NAME = "rife-v4.6"
MODEL_FILES = ("flownet.bin", "flownet.param")

_FETCH_THE_17_MB_THE_REPO_LEAVES_UNTRACKED_THE_17_MB_THE_REPO_LEAVES_UNTRACKED = "run `python tools/fetch_rife.py` -- see CLAUDE.md, Fetching RIFE"
_FALLBACK = "normalizing falls back to its geometric seam"


def _find_exe() -> Path | None:
    on_path = shutil.which(VENDORED_EXE.stem)
    candidates = (PROJECT_DIR / VENDORED_EXE, Path(on_path) if on_path else None)
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return candidate
    return None


def _missing_weights(exe: Path) -> list[str]:
    model_dir = exe.parent / MODEL_DIR_NAME
    return [name for name in MODEL_FILES
            if not (model_dir / name).is_file() or (model_dir / name).stat().st_size == 0]


def locate() -> tuple[Path, Path] | None:
    exe = _find_exe()
    if exe is None or _missing_weights(exe):
        return None
    return exe, exe.parent / MODEL_DIR_NAME


def complaints() -> list[str]:
    exe = _find_exe()
    if exe is None:
        return [f"there is none in this checkout, so {_FALLBACK}; {_FETCH_THE_17_MB_THE_REPO_LEAVES_UNTRACKED_THE_17_MB_THE_REPO_LEAVES_UNTRACKED}"]
    missing = _missing_weights(exe)
    if missing:
        return [f"{exe} has no {' or '.join(missing)} beside it, so {_FALLBACK}; {_FETCH_THE_17_MB_THE_REPO_LEAVES_UNTRACKED_THE_17_MB_THE_REPO_LEAVES_UNTRACKED}"]
    return []
