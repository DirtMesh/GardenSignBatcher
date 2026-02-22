from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict


APP_NAME = "ModularGardenSignBatch"


def _config_dir() -> Path:
    base = os.environ.get("APPDATA")
    if not base:
        # Fallback, extremely rare on Windows
        base = str(Path.home())
    return Path(base) / APP_NAME


def config_path() -> Path:
    return _config_dir() / "config.json"


def load_config() -> Dict[str, Any]:
    path = config_path()
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # Corrupt config should never crash the app
        return {}


def save_config(cfg: Dict[str, Any]) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, sort_keys=True)

    tmp.replace(path)
