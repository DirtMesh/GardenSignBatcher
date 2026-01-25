from __future__ import annotations

from pathlib import Path
from typing import Tuple, List, Optional

from .models import InputRow, ValidationIssue
from .excel import list_sheets, read_rows_from_sheet
from .csv_input import read_rows_from_csv


def read_input_rows(
    path: Path,
    *,
    sheet: Optional[str] = None,
) -> Tuple[List[InputRow], List[ValidationIssue], Optional[str]]:
    """
    Returns: (rows, issues, resolved_sheet_name)

    resolved_sheet_name is only meaningful for xlsx, otherwise None.
    """
    suffix = path.suffix.lower()

    if suffix == ".csv":
        rows, issues = read_rows_from_csv(path)
        return rows, issues, None

    if suffix in (".xlsx", ".xlsm"):
        sheets = list_sheets(path)
        if not sheets:
            return [], [ValidationIssue(row_num=1, reason="No sheets found in workbook")], None

        resolved = sheet or sheets[0]
        if resolved not in sheets:
            return [], [ValidationIssue(row_num=1, reason=f"Sheet not found: {resolved}")], None

        rows, issues = read_rows_from_sheet(path, resolved)
        return rows, issues, resolved

    return [], [ValidationIssue(row_num=1, reason=f"Unsupported input type: {suffix}")], None
