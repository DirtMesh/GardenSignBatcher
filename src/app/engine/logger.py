from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable, Optional


class RunLogger:
    def __init__(self, outdir: Path, *, prefix: str = "run"):
        outdir = Path(outdir)
        outdir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = outdir / f"{prefix}_{ts}.log"
        self._fh = self.path.open("w", encoding="utf-8")

    def close(self) -> None:
        if not self._fh.closed:
            self._fh.flush()
            self._fh.close()

    def write(self, msg: str) -> None:
        self._fh.write(msg.rstrip() + "\n")
        self._fh.flush()

    def log(self, msg: str) -> None:
        self.write(msg)

    def tee(self, console_fn: Optional[Callable[[str], None]] = None) -> Callable[[str], None]:
        """
        Returns a function suitable for on_log that writes to file
        and optionally mirrors to console or GUI.
        """
        def _log(msg: str) -> None:
            self.write(msg)
            if console_fn:
                console_fn(msg)
        return _log
