from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Tuple

from .models import InputRow, ValidationIssue


def read_rows_from_csv(csv_path: Path) -> Tuple[List[InputRow], List[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    rows: list[InputRow] = []

    # We treat "row_num" as the physical file line number (1-based)
    # Header is line 1, first data row is line 2
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        if not reader.fieldnames:
            issues.append(ValidationIssue(row_num=1, reason="CSV has no header row"))
            return [], issues

        fields = [h.strip().lower() for h in reader.fieldnames]

        if "crop_name" not in fields:
            issues.append(ValidationIssue(row_num=1, reason="Missing required column: crop_name"))
            return [], issues

        # Optional column
        has_cultivar = ("cultivar" in fields)

        for i, row in enumerate(reader, start=2):
            # DictReader keys are original header strings, so map case-insensitively
            # Build a lowercase-keyed dict for reliable access
            row_lc = { (k.strip().lower() if k else ""): (v if v is not None else "") for k, v in row.items() }

            crop = (row_lc.get("crop_name") or "").strip()
            cultivar = (row_lc.get("cultivar") or "").strip() if has_cultivar else ""

            if not crop:
                issues.append(ValidationIssue(row_num=i, reason="Missing crop_name"))
                continue

            rows.append(InputRow(row_num=i, crop_name=crop, cultivar=cultivar))

    return rows, issues
