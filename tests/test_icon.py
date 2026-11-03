from __future__ import annotations

from shared_ui.app_icon import assert_follows_the_family_spec

from genaumacher.window_icons import genaumacher_icon_path


def test_the_icon_is_the_familys_g():
    assert_follows_the_family_spec(genaumacher_icon_path(), "G")
