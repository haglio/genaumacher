from __future__ import annotations

import hashlib
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

RELEASE = "20221029"
ASSET = f"rife-ncnn-vulkan-{RELEASE}-windows.zip"
URL = f"https://github.com/nihui/rife-ncnn-vulkan/releases/download/{RELEASE}/{ASSET}"
SHA256 = "d8e4d772d26cd8006ef0ad0bc82eb191b53c68677d1ae2f42506d74cbbbea606"

TOOLS_DIR = Path(__file__).resolve().parent
DEST = TOOLS_DIR / f"rife-ncnn-vulkan-{RELEASE}-windows"
RIFE_EXE = DEST / "rife-ncnn-vulkan.exe"
ZIP_PATH = TOOLS_DIR / ASSET

_THE_C_RUNTIME_THE_EXECUTABLE_LOADS = "vcomp140.dll"
_WHAT_THE_APP_RUNS = ("rife-ncnn-vulkan.exe", _THE_C_RUNTIME_THE_EXECUTABLE_LOADS)
_THE_ONE_MODEL_THE_APP_OPENS = ("rife-v4.6/flownet.bin", "rife-v4.6/flownet.param")
_WHAT_THE_MIT_LICENSE_REQUIRES_TO_TRAVEL_WITH_THE_BINARIES = ("LICENSE", "README.md")
FILES = (*_WHAT_THE_MIT_LICENSE_REQUIRES_TO_TRAVEL_WITH_THE_BINARIES, *_WHAT_THE_APP_RUNS, *_THE_ONE_MODEL_THE_APP_OPENS)

_DOWNLOAD_TIMEOUT = 120


def is_present() -> bool:
    return all(
        (DEST / name).is_file() and (DEST / name).stat().st_size > 0
        for name in FILES
    )


def runs() -> bool:
    # A Windows machine with no Vulkan device starts it and gets no frame back: called with no
    # arguments, upstream prints its usage and exits before it touches Vulkan.
    if not is_present():
        return False
    interpolate = _the_production_call_imported_here_so_fetching_needs_no_app_installed()
    try:
        return interpolate() is not None
    except Exception:
        return False


def _the_production_call_imported_here_so_fetching_needs_no_app_installed():
    import numpy as np  # noqa: PLC0415

    from genaumacher.normalize_transforms import build_rife_bridge  # noqa: PLC0415

    y, x = (a.astype(np.uint8) for a in np.mgrid[0:64, 0:64])
    return lambda: build_rife_bridge(np.dstack([x, y, x]), np.dstack([y, x, y]), 1)


def sha256_of(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def download(target: Path = ZIP_PATH) -> Path:
    if target.exists() and sha256_of(target) == SHA256:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"fetching {URL}")
    with urllib.request.urlopen(URL, timeout=_DOWNLOAD_TIMEOUT) as response, target.open("wb") as handle:  # noqa: S310
        shutil.copyfileobj(response, handle)
    actual = sha256_of(target)
    if actual != SHA256:
        target.unlink(missing_ok=True)
        raise SystemExit(f"sha256 mismatch for {ASSET}: expected {SHA256}, got {actual}")
    return target


def extract(archive: Path, dest: Path = DEST) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        for name in FILES:
            out = dest / name
            out.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(f"rife-ncnn-vulkan-{RELEASE}-windows/{name}") as src:
                out.write_bytes(src.read())


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    require = "--require" in argv

    if not is_present():
        archive = download()
        extract(archive)
        archive.unlink(missing_ok=True)

    if not is_present():
        print(f"RIFE is still not at {DEST}", file=sys.stderr)
        return 1

    if runs():
        print(f"RIFE is at {DEST} and interpolates here")
        return 0

    print(
        f"RIFE is at {DEST} but produced no frame here — expected off Windows, "
        "where it is a PE that cannot be executed; on Windows it means the "
        "binary ran and the interpolation did not (no usable Vulkan device)."
    )
    if require:
        print(
            "--require was given, so this is a failure: the merge gate depends on "
            "the interpolator actually running.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
