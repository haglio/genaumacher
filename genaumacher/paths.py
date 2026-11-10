from __future__ import annotations

from pathlib import Path, PureWindowsPath

from app_support import haglio_settings
from app_support.flick_folder import flat_flicks_in, flicks_folder_in, vr_flicks_in

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent
SESSIONS_DIR = PROJECT_DIR / "sessions"
RAW_CLIPS_DIR = PROJECT_DIR / "raw_clips"
LAST_SESSION_FILE = SESSIONS_DIR / ".last_session.txt"
NORMALIZE_SCRIPT = PACKAGE_DIR / "normalize.py"


def library_root() -> Path:
    return Path(haglio_settings.value("library_root"))


def _placeholder_library_root() -> Path:
    return Path(haglio_settings.EXAMPLE["library_root"])


def _genau_dir() -> Path:
    return Path(haglio_settings.value("genau_dir"))


def _genau_flicks_dir() -> Path:
    flicks = flicks_folder_in(_genau_dir())
    if flicks is None:
        raise FileNotFoundError(f"No folder in {_genau_dir()} is laid out as Genau's "
                                f"{haglio_settings.value('genau_flick_words', 'many')} are")
    return flicks


def flicks_dir() -> Path:
    return flat_flicks_in(_genau_flicks_dir()) / "non_AI"


def vr_flicks_dir() -> Path:
    return vr_flicks_in(_genau_flicks_dir())


def audio_dir() -> Path:
    return Path(haglio_settings.value("genau_audio_dir"))


def metadata_dir() -> Path:
    return library_root() / "videos" / "metadata"


def vr_video_dir() -> PureWindowsPath:
    return PureWindowsPath(library_root()) / "videos" / "videos" / "VR"


def library_is_configured() -> bool:
    return library_root() != _placeholder_library_root()


def ensure_runtime_dirs() -> None:
    for directory in (SESSIONS_DIR, RAW_CLIPS_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    if not library_is_configured() or flicks_folder_in(_genau_dir()) is None:
        return
    for directory in (flicks_dir(), vr_flicks_dir(), audio_dir()):
        directory.mkdir(parents=True, exist_ok=True)


FORBIDDEN_NAME_CHARS = '<>:"/\\|?*'


def sanitize_name(name: str) -> str:
    name = name.strip()
    for ch in FORBIDDEN_NAME_CHARS:
        name = name.replace(ch, "_")
    return name.strip().rstrip(".")
