from __future__ import annotations

import ast
import inspect
import re
import textwrap
from pathlib import Path, PureWindowsPath

import pytest
from app_support import haglio_settings
from app_support.flick_folder import flat_flicks_in

from genaumacher import paths
from genaumacher.paths import (
    FORBIDDEN_NAME_CHARS,
    audio_dir,
    ensure_runtime_dirs,
    flicks_dir,
    library_is_configured,
    library_root,
    sanitize_name,
    vr_flicks_dir,
    vr_video_dir,
)

_RUNTIME_DIRS = (
    "SESSIONS_DIR",
    "RAW_CLIPS_DIR",
    "flicks_dir",
    "vr_flicks_dir",
    "audio_dir",
)


def _names_ensure_runtime_dirs_creates() -> set[str]:
    tree = ast.parse(textwrap.dedent(inspect.getsource(ensure_runtime_dirs)))
    return {
        leaf.id
        for node in ast.walk(tree)
        if isinstance(node, ast.For)
        for leaf in ast.walk(node.iter)
        if isinstance(leaf, ast.Name)
    }


@pytest.fixture
def checkout_dirs(tmp_path: Path, monkeypatch):
    names = ("SESSIONS_DIR", "RAW_CLIPS_DIR")
    for name in names:
        monkeypatch.setattr(paths, name, tmp_path / name.lower())
    return {name: tmp_path / name.lower() for name in names}


@pytest.fixture
def runtime_dirs(library, checkout_dirs):
    genau = Path(haglio_settings.value("genau_dir"))
    return {
        **checkout_dirs,
        "flicks_dir": genau / "flicks" / "2D" / "non_AI",
        "vr_flicks_dir": genau / "flicks" / "VR",
        "audio_dir": Path(haglio_settings.value("genau_audio_dir")),
    }


class TestWhereTheLibraryFoldersAre:
    def test_the_clip_folders_are_in_the_genau_folder_the_settings_name_wherever_that_is(
        self, tmp_path: Path, shared_settings
    ):
        genau = tmp_path / "somewhere else" / "genau-here"
        flat_flicks_in(genau / "flicks").mkdir(parents=True)
        shared_settings({"library_root": str(tmp_path / "library"), "genau_dir": str(genau)})

        assert (flicks_dir(), vr_flicks_dir()) == (
            genau / "flicks" / "2D" / "non_AI", genau / "flicks" / "VR")

    def test_the_sounds_go_to_the_audio_folder_the_settings_name_wherever_that_is(
        self, tmp_path: Path, shared_settings
    ):
        sounds = tmp_path / "somewhere else" / "sounds-here"
        shared_settings({
            "library_root": str(tmp_path / "library"),
            "genau_dir": str(tmp_path / "genau-here"),
            "genau_audio_dir": str(sounds),
        })

        assert audio_dir() == sounds

    @pytest.mark.usefixtures("library")
    def test_a_cut_goes_where_genau_keeps_the_flicks_cut_from_real_videos(self):
        genau = Path(haglio_settings.value("genau_dir"))

        assert (flicks_dir(), vr_flicks_dir(), audio_dir()) == (
            genau / "flicks" / "2D" / "non_AI", genau / "flicks" / "VR",
            Path(haglio_settings.value("genau_audio_dir")))

    def test_genaus_flicks_folder_is_found_by_its_shape_whatever_it_is_called(self, library: Path):
        genau = Path(haglio_settings.value("genau_dir"))
        (genau / "flicks").rename(genau / "example-flicks")
        flicks = genau / "example-flicks"

        assert (flicks_dir(), vr_flicks_dir()) == (flicks / "2D" / "non_AI", flicks / "VR")

    def test_with_no_folder_shaped_like_genaus_flicks_a_cut_has_nowhere_to_go(
        self, tmp_path: Path, shared_settings
    ):
        genau = tmp_path / "empty library" / "genau-here"
        shared_settings({"library_root": str(tmp_path / "empty library"), "genau_dir": str(genau)})

        with pytest.raises(FileNotFoundError, match=re.escape(str(genau))):
            flicks_dir()

    def test_settings_written_after_the_import_are_the_ones_that_answer(
        self, tmp_path: Path, shared_settings
    ):
        written = tmp_path / "written just now"
        genau = written / "videos" / "videos" / "genau"
        flat_flicks_in(genau / "flicks").mkdir(parents=True)
        shared_settings({"library_root": str(written), "genau_dir": str(genau)})

        assert flicks_dir().is_relative_to(written)

    def test_settings_with_no_library_root_say_so_and_name_their_file(self, shared_settings):
        settings = shared_settings({"project_roots": []})

        with pytest.raises(LookupError, match="library_root"):
            library_root()

        with pytest.raises(LookupError, match=settings.name):
            library_root()

    @pytest.mark.parametrize("missing, asked", [("genau_dir", flicks_dir), ("genau_audio_dir", audio_dir)])
    def test_settings_with_no_genau_place_say_which_and_name_their_file(
        self, shared_settings, missing, asked
    ):
        settings = shared_settings({"library_root": "D:/example-suite"})

        with pytest.raises(LookupError, match=missing):
            asked()

        with pytest.raises(LookupError, match=settings.name):
            asked()


class TestTheVrVideoFolder:
    def test_it_is_the_vr_folder_under_the_librarys_own_root(self, shared_settings):
        shared_settings({"library_root": "D:/example-suite"})

        assert vr_video_dir() == PureWindowsPath(
            r"D:\example-suite\videos\videos\VR"
        )

    def test_it_matches_a_windows_path_wherever_the_test_is_run(self, shared_settings):
        shared_settings({"library_root": "D:/example-suite"})

        typed = PureWindowsPath(r"D:\example-suite\videos\videos\VR\seaside walk.mp4")

        assert typed.is_relative_to(vr_video_dir())


class TestEnsureRuntimeDirs:
    def test_creates_every_directory_the_app_writes_into(self, runtime_dirs):
        ensure_runtime_dirs()

        missing = sorted(name for name, path in runtime_dirs.items() if not path.is_dir())
        assert missing == []

    def test_the_directories_it_creates_are_the_ones_named_here(self):
        assert _names_ensure_runtime_dirs_creates() == set(_RUNTIME_DIRS)

    def test_a_second_run_keeps_what_the_first_one_left(self, runtime_dirs):
        ensure_runtime_dirs()
        (runtime_dirs["SESSIONS_DIR"] / "demo.json").write_text("{}", encoding="utf-8")

        ensure_runtime_dirs()

        assert (runtime_dirs["SESSIONS_DIR"] / "demo.json").read_text(encoding="utf-8") == "{}"
        assert all(path.is_dir() for path in runtime_dirs.values())


class TestAMachineWithNoLibraryYet:
    def test_a_library_root_of_its_own_is_what_makes_a_library(
        self, tmp_path: Path, shared_settings
    ):
        shared_settings({"library_root": str(tmp_path / "library")})

        assert library_is_configured() is True

    def test_a_machine_with_no_settings_has_no_library(self, shared_settings):
        shared_settings()

        assert library_is_configured() is False

    def test_settings_still_holding_the_example_are_not_a_library_either(
        self, shared_settings
    ):
        shared_settings(haglio_settings.EXAMPLE)

        assert library_is_configured() is False

    def test_a_placeholder_library_gets_no_folders_though_its_tree_is_laid_out(
        self, tmp_path: Path, checkout_dirs, shared_settings
    ):
        genau = tmp_path / "genau"
        flat_flicks_in(genau / "flicks").mkdir(parents=True)
        audio = tmp_path / "audio"
        shared_settings({**haglio_settings.EXAMPLE, "genau_dir": str(genau), "genau_audio_dir": str(audio)})

        ensure_runtime_dirs()

        assert not audio.exists()

    def test_the_repos_own_directories_are_still_made(self, checkout_dirs, shared_settings):
        shared_settings()

        ensure_runtime_dirs()

        assert checkout_dirs["SESSIONS_DIR"].is_dir()
        assert checkout_dirs["RAW_CLIPS_DIR"].is_dir()

    def test_no_library_directory_is_made(self, checkout_dirs, shared_settings):
        shared_settings()
        genau = Path(haglio_settings.value("genau_dir"))
        already = genau.is_dir()

        ensure_runtime_dirs()

        assert genau.is_dir() == already


class TestSanitizeName:
    def test_clean_name_unchanged(self):
        assert sanitize_name("clean name") == "clean name"

    def test_strips_leading_trailing_spaces(self):
        assert sanitize_name("  hello  ") == "hello"

    @pytest.mark.parametrize("forbidden", list(FORBIDDEN_NAME_CHARS))
    def test_every_character_a_filename_cannot_hold_becomes_an_underscore(self, forbidden):
        assert sanitize_name(f"take{forbidden}one") == "take_one"

    def test_the_list_is_the_nine_windows_refuses(self):
        assert sanitize_name('a<b>c:d"e/f\\g|h?i*j') == "a_b_c_d_e_f_g_h_i_j"

    def test_strips_trailing_dots(self):
        result = sanitize_name("filename.")
        assert not result.endswith(".")

    def test_a_name_of_only_spaces_becomes_the_empty_string(self):
        assert sanitize_name("   ") == ""
