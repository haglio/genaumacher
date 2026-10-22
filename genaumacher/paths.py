from __future__ import annotations

from pathlib import Path, PureWindowsPath

from app_support import haglio_settings
from app_support.flick_folder import flat_flicks_in, flicks_folder_in, vr_flicks_in

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent
SESSIONS_DIR = PROJECT_DIR / "sessions"
RAW_CLIPS_DIR = PROJECT_DIR / "raw_clips"
LAST_SESSION_FILE = SESSIONS_DIR / ".last_session.txt"
CLIP_POSTPROCESS_SCRIPT = PACKAGE_DIR / "clip_postprocess.py"


def library_root() -> Path:
    """Where the media library lives, as the Haglio settings name it.

    Asked at the call rather than read into a constant at import: a module that
    reads its settings to be imported makes every consumer -- a test, a tool,
    another app's smoke check -- pay for the file and inherit whichever copy
    happened to be on disk first.
    """
    return Path(haglio_settings.value("library_root"))


def _placeholder_library_root() -> Path:
    return Path(haglio_settings.EXAMPLE["library_root"])


def _genau_dir() -> Path:
    """The output tree genau reads, which is what genaumacher exports into."""
    return Path(haglio_settings.value("genau_dir"))


def _genau_flicks_dir() -> Path:
    flicks = flicks_folder_in(_genau_dir())
    if flicks is None:
        raise FileNotFoundError(f"No folder in {_genau_dir()} is laid out as Genau's flicks are")
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
    """The library folder whose videos are VR, which is what the launcher's
    checkbox reads to decide whether an export lands in Genau's VR folder.

    A pure Windows path: what it is compared against is whatever the file
    dialog handed the launcher on the machine the app runs on, and that machine
    is a Windows one.  A native path would make the comparison a no-op
    everywhere else, which is where the tests run.
    """
    return PureWindowsPath(library_root()) / "videos" / "videos" / "VR"


def library_is_configured() -> bool:
    """Whether ``library_root`` names a real library or the example's placeholder.

    The value, not whether a settings file exists: one still holding
    ``C:/path/to/library-root`` names no library either.
    """
    return library_root() != _placeholder_library_root()


def ensure_runtime_dirs() -> None:
    """Create what genaumacher writes into, as far as this machine has somewhere.

    The first two are inside the checkout and always made.  The library folders
    are the ones the Haglio settings name, placeholders under ``library_root``
    until the settings name a library: on POSIX ``C:/path/to/library-root`` is a
    *relative* path, so making them put a literal ``C:`` tree inside the repo,
    and on Windows it put ``C:\\path\\to\\library-root`` on the system drive.  A
    machine with no settings has no library to export into, so it gets no
    folders pretending otherwise.
    """
    for directory in (SESSIONS_DIR, RAW_CLIPS_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    if not library_is_configured() or flicks_folder_in(_genau_dir()) is None:
        return
    for directory in (flicks_dir(), vr_flicks_dir(), audio_dir()):
        directory.mkdir(parents=True, exist_ok=True)


# The characters Windows will not take in a filename.  Named rather than inline
# so a test can walk the list instead of carrying its own copy of it.
FORBIDDEN_NAME_CHARS = '<>:"/\\|?*'


def sanitize_name(name: str) -> str:
    """The session name as a filename this app can find again.

    Lives here because every path this module builds out of a session name is
    built from the sanitized form; keeping the two apart is what let
    `create_session` write one file and the rest of the app look for another.
    """
    name = name.strip()
    for ch in FORBIDDEN_NAME_CHARS:
        name = name.replace(ch, "_")
    return name.strip().rstrip(".")
