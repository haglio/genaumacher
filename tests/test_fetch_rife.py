from __future__ import annotations

import hashlib
import io
import subprocess
import zipfile
from pathlib import Path

import pytest

from genaumacher import interpolator_environment
from tools import fetch_rife

_RELEASE_BYTES = b"pretend release"


def _release_zip(path: Path) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        for name in fetch_rife.FILES:
            zf.writestr(
                f"rife-ncnn-vulkan-{fetch_rife.RELEASE}-windows/{name}",
                f"contents of {name}\n",
            )
        zf.writestr(
            f"rife-ncnn-vulkan-{fetch_rife.RELEASE}-windows/rife-anime/flownet.bin",
            "a model nothing opens\n",
        )
    return path


def _never_called(*_args, **_kwargs):
    raise AssertionError("nothing here should have gone to the network")


class TestWhereItLands:
    def test_the_app_looks_where_the_fetch_step_extracts(self):
        assert (fetch_rife.RIFE_EXE.relative_to(fetch_rife.TOOLS_DIR.parent)
                == interpolator_environment.VENDORED_EXE)

    def test_the_fetch_step_brings_the_weights_the_app_asks_for(self):
        wanted = {f"{interpolator_environment.MODEL_DIR_NAME}/{name}"
                  for name in interpolator_environment.MODEL_FILES}

        assert wanted <= set(fetch_rife.FILES)


class TestExtract:
    def test_it_writes_every_file_it_names(self, tmp_path: Path):
        dest = tmp_path / "out"

        fetch_rife.extract(_release_zip(tmp_path / "release.zip"), dest)

        written = sorted(
            p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file()
        )
        assert written == sorted(fetch_rife.FILES)

    def test_it_leaves_the_models_the_code_never_opens(self, tmp_path: Path):
        dest = tmp_path / "out"

        fetch_rife.extract(_release_zip(tmp_path / "release.zip"), dest)

        assert not (dest / "rife-anime").exists()

    def test_the_bytes_are_the_archives(self, tmp_path: Path):
        dest = tmp_path / "out"

        fetch_rife.extract(_release_zip(tmp_path / "release.zip"), dest)

        assert (dest / "rife-v4.6" / "flownet.bin").read_text(encoding="utf-8") == (
            "contents of rife-v4.6/flownet.bin\n"
        )


class TestIsPresent:
    def test_all_six_extracted_is_present(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(fetch_rife, "DEST", tmp_path)
        fetch_rife.extract(_release_zip(tmp_path / "release.zip"), tmp_path)

        assert fetch_rife.is_present() is True

    def test_one_missing_file_is_not_present(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(fetch_rife, "DEST", tmp_path)
        fetch_rife.extract(_release_zip(tmp_path / "release.zip"), tmp_path)
        (tmp_path / "vcomp140.dll").unlink()

        assert fetch_rife.is_present() is False


def _bridge_returning(result):
    def _bridge(_a, _b, _n):
        if isinstance(result, Exception):
            raise result
        return result
    return _bridge


class TestRuns:
    @pytest.fixture
    def extracted(self, extracted_with_the_apps_own_lookup_pointed_at_the_fake_too_or_the_windows_runner_finds_the_real_exe):
        return extracted_with_the_apps_own_lookup_pointed_at_the_fake_too_or_the_windows_runner_finds_the_real_exe

    @pytest.fixture
    def extracted_with_the_apps_own_lookup_pointed_at_the_fake_too_or_the_windows_runner_finds_the_real_exe(self, tmp_path: Path, monkeypatch) -> Path:
        monkeypatch.setattr(fetch_rife, "DEST", tmp_path)
        monkeypatch.setattr(fetch_rife, "RIFE_EXE", tmp_path / "rife-ncnn-vulkan.exe")
        monkeypatch.setattr(
            "genaumacher.interpolator_environment._find_exe",
            lambda: fetch_rife.RIFE_EXE,
        )
        fetch_rife.extract(_release_zip(tmp_path / "release.zip"), tmp_path)
        return tmp_path

    def test_nothing_extracted_does_not_run(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(fetch_rife, "DEST", tmp_path / "empty")

        assert fetch_rife.runs() is False

    def test_a_file_this_machine_cannot_execute_does_not_run(self, extracted_with_the_apps_own_lookup_pointed_at_the_fake_too_or_the_windows_runner_finds_the_real_exe: Path):
        assert fetch_rife.runs() is False

    def test_a_bridge_frame_coming_back_is_what_running_means(
        self, extracted_with_the_apps_own_lookup_pointed_at_the_fake_too_or_the_windows_runner_finds_the_real_exe: Path, monkeypatch
    ):
        monkeypatch.setattr(
            "genaumacher.normalize_transforms.build_rife_bridge",
            _bridge_returning([object()]),
        )

        assert fetch_rife.runs() is True

    def test_a_binary_that_starts_and_interpolates_nothing_does_not_run(
        self, extracted_with_the_apps_own_lookup_pointed_at_the_fake_too_or_the_windows_runner_finds_the_real_exe: Path, monkeypatch
    ):
        monkeypatch.setattr(
            "genaumacher.normalize_transforms.build_rife_bridge",
            _bridge_returning(None),
        )

        assert fetch_rife.runs() is False

    def test_a_bridge_that_raises_does_not_run(self, extracted_with_the_apps_own_lookup_pointed_at_the_fake_too_or_the_windows_runner_finds_the_real_exe: Path, monkeypatch):
        monkeypatch.setattr(
            "genaumacher.normalize_transforms.build_rife_bridge",
            _bridge_returning(subprocess.TimeoutExpired(cmd="rife", timeout=1)),
        )

        assert fetch_rife.runs() is False


class TestMain:
    @pytest.fixture
    def fetched(self, tmp_path: Path, monkeypatch) -> Path:
        monkeypatch.setattr(fetch_rife, "DEST", tmp_path)
        fetch_rife.extract(_release_zip(tmp_path / "release.zip"), tmp_path)
        return tmp_path

    def _with_runs(self, monkeypatch, answer: bool) -> None:
        monkeypatch.setattr(fetch_rife, "runs", lambda: answer)

    def test_a_file_left_empty_does_not_count_as_fetched(self, fetched):
        (fetched / fetch_rife.FILES[0]).write_bytes(b"")

        assert fetch_rife.is_present() is False

    def test_it_reports_success_when_the_interpolator_works(self, fetched, monkeypatch):
        self._with_runs(monkeypatch, True)

        assert fetch_rife.main([]) == 0
        assert fetch_rife.main(["--require"]) == 0

    def test_a_binary_that_does_not_run_is_fine_without_require(self, fetched, monkeypatch):
        self._with_runs(monkeypatch, False)

        assert fetch_rife.main([]) == 0

    def test_a_binary_that_does_not_run_fails_under_require(self, fetched, monkeypatch):
        self._with_runs(monkeypatch, False)

        assert fetch_rife.main(["--require"]) == 1

    def test_a_fetch_that_lands_nothing_fails_either_way(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(fetch_rife, "DEST", tmp_path / "nothing")
        monkeypatch.setattr(fetch_rife, "download", lambda *a, **k: tmp_path / "absent.zip")
        monkeypatch.setattr(fetch_rife, "extract", lambda *a, **k: None)

        assert fetch_rife.main([]) == 1
        assert fetch_rife.main(["--require"]) == 1

    def test_it_fetches_only_when_something_is_missing(self, fetched, monkeypatch):
        self._with_runs(monkeypatch, True)
        monkeypatch.setattr(fetch_rife, "download", _never_called)

        assert fetch_rife.main([]) == 0


class TestDownload:
    def test_an_intact_copy_already_there_is_reused_the_asset_is_432_mb_for_the_six_files_taken(self, tmp_path: Path, monkeypatch):
        archive = tmp_path / fetch_rife.ASSET
        archive.write_bytes(_RELEASE_BYTES)
        monkeypatch.setattr(fetch_rife, "SHA256", hashlib.sha256(_RELEASE_BYTES).hexdigest())
        monkeypatch.setattr(fetch_rife.urllib.request, "urlopen", _never_called)

        assert fetch_rife.download(archive) == archive

    def test_a_truncated_copy_is_fetched_again(self, tmp_path: Path, monkeypatch):
        archive = tmp_path / fetch_rife.ASSET
        archive.write_bytes(b"half a download")
        fetched: list[str] = []

        def _open(url, timeout=None):
            fetched.append((url, timeout))
            return io.BytesIO(_RELEASE_BYTES)

        monkeypatch.setattr(fetch_rife, "SHA256", hashlib.sha256(_RELEASE_BYTES).hexdigest())
        monkeypatch.setattr(fetch_rife.urllib.request, "urlopen", _open)

        fetch_rife.download(archive)

        assert fetched == [(fetch_rife.URL, fetch_rife._DOWNLOAD_TIMEOUT)]


    def test_a_download_that_does_not_match_is_refused_and_removed(
        self, tmp_path: Path, monkeypatch
    ):
        archive = tmp_path / fetch_rife.ASSET

        def _open(_url, timeout=None):
            return io.BytesIO(b"something else entirely")

        monkeypatch.setattr(fetch_rife.urllib.request, "urlopen", _open)

        with pytest.raises(SystemExit, match="sha256 mismatch"):
            fetch_rife.download(archive)

        assert not archive.exists()


def test_the_release_is_fetched_not_tracked_a_clone_should_not_carry_a_windows_binary_most_machines_cannot_run():
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", fetch_rife.DEST.relative_to(fetch_rife.TOOLS_DIR.parent).as_posix() + "/"],
        cwd=fetch_rife.TOOLS_DIR.parent, check=False)

    assert ignored.returncode == 0
