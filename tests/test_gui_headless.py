from __future__ import annotations


def test_the_suite_renders_offscreen(qapp):
    assert qapp.platformName() == "offscreen"
