
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_each_name_whitelisted_as_read_only_by_the_tests_is_read_by_one():
    whitelist = (REPO_ROOT / "vulture_whitelist.py").read_text(encoding="utf-8")
    group = whitelist.split("# Read only by the tests, which vulture does not scan.\n", 1)[1].split("\n\n", 1)[0]
    names = [line.split(".", 1)[1] for line in group.splitlines() if line.startswith("_.")]
    tests = "\n".join(p.read_text(encoding="utf-8") for p in (REPO_ROOT / "tests").glob("*.py"))

    assert names
    assert [name for name in names if not re.search(rf"\b{re.escape(name)}\b", tests)] == []
