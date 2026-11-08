from __future__ import annotations

# Qt calls these from its event loop.
_.paintEvent
_.mousePressEvent

# Read only by the tests, which vulture does not scan.
_.last_saved_payload
_.render_rev

# Held and never read: a QThread whose last Python reference goes is collected mid-export.
_._export_worker

# Read outside what vulture scans.
RIFE_EXE
