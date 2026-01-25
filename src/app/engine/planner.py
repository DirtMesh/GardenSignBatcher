from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Set, Tuple

from .models import InputRow, PlannedJob
from .sanitize import sanitize_filename


def _base_name(index: int, crop: str, cultivar: str) -> str:
    n = f"{index:03d}"
    crop_safe = sanitize_filename(crop)
    cult_safe = sanitize_filename(cultivar)

    base = f"{n}_{crop_safe}"
    if cultivar.strip():
        base += f"_{cult_safe}"
    return base


def plan_jobs(
    rows: list[InputRow],
    outdir: Path,
    *,
    export_a: bool = True,
    export_b: bool = True,
    start_index: int = 1,
    overwrite: bool = False,
) -> list[PlannedJob]:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    planned: list[PlannedJob] = []
    used_names: Set[str] = set()

    idx = start_index - 1

    for row in rows:
        idx += 1
        base = _base_name(idx, row.crop_name, row.cultivar)

        # Determine unique base if overwrite is False
        unique_base = base
        if not overwrite:
            # Check against current plan and also existing files
            suffix = 1
            while True:
                # We consider both parts when checking collisions
                candidates = []
                if export_a:
                    candidates.append(f"{unique_base}_a.stl")
                if export_b:
                    candidates.append(f"{unique_base}_b.stl")

                collision = any(
                    (c in used_names) or (outdir / c).exists()
                    for c in candidates
                )
                if not collision:
                    break
                suffix += 1
                unique_base = f"{base}_{suffix:02d}"

        if export_a:
            out_a = outdir / f"{unique_base}_a.stl"
            planned.append(
                PlannedJob(
                    row=row,
                    part="a",
                    out_path=out_a,
                    defs={"crop_name": row.crop_name, "cultivar": row.cultivar, "export_part": "a"},
                )
            )
            used_names.add(out_a.name)

        if export_b:
            out_b = outdir / f"{unique_base}_b.stl"
            planned.append(
                PlannedJob(
                    row=row,
                    part="b",
                    out_path=out_b,
                    defs={"crop_name": row.crop_name, "cultivar": row.cultivar, "export_part": "b"},
                )
            )
            used_names.add(out_b.name)

    return planned
