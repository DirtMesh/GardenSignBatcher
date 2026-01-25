from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative: str) -> Path:
    """
    Resolve a resource path for both dev and PyInstaller builds.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).resolve().parents[2]  # src/app/...
    return base / relative
