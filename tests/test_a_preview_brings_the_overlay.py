from __future__ import annotations

import sys
from pathlib import Path

import pytest
from app_support.launcher import dry_run

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(sys.platform != "win32", reason="the Windows script host")
def test_a_branch_preview_brings_the_primary_checkouts_overlay_across():
    overlay = "content.local.json"

    assert dry_run(REPO_ROOT / "launch_preview_branch.vbs").value("copy") == (
        f"{REPO_ROOT.parents[2] / overlay} > {REPO_ROOT / overlay}")
