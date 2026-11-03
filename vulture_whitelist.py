from __future__ import annotations

# Qt calls these from its event loop.
_.paintEvent
_.mousePressEvent

# Written through setattr, which vulture cannot follow.
_._export_worker
_.last_saved_payload
_.render_rev

# Read outside what vulture scans.
RIFE_EXE
