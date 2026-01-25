from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class InputRow:
    row_num: int                 # Excel row number (1-based, as seen by humans)
    crop_name: str
    cultivar: str


@dataclass(frozen=True)
class PlannedJob:
    row: InputRow
    part: str                    # "a" or "b"
    out_path: Path
    defs: dict                   # OpenSCAD -D definitions for this job


@dataclass(frozen=True)
class ValidationIssue:
    row_num: int
    reason: str


@dataclass(frozen=True)
class RunSummary:
    total_rows: int
    valid_rows: int
    selected_rows: int
    jobs_planned: int
    jobs_succeeded: int
    jobs_failed: int
    jobs_skipped: int
    log_path: Optional[Path]
