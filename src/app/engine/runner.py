from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from .models import PlannedJob
from .openscad import run_openscad


ProgressFn = Callable[[int, int, PlannedJob], None]   # (done, total, job)
LogFn = Callable[[str], None]
CancelFn = Callable[[], bool]


@dataclass
class JobResult:
    job: PlannedJob
    ok: bool
    returncode: int
    stdout: str
    stderr: str
    cmd: list[str]


def run_jobs(
    jobs: list[PlannedJob],
    *,
    openscad_exe: Path,
    scad_file: Path,
    stop_on_error: bool = False,
    on_progress: Optional[ProgressFn] = None,
    on_log: Optional[LogFn] = None,
    should_cancel: Optional[CancelFn] = None,
) -> list[JobResult]:
    results: list[JobResult] = []
    total = len(jobs)

    for i, job in enumerate(jobs, start=1):
        if should_cancel and should_cancel():
            if on_log:
                on_log("Cancel requested. Stopping run.")
            break

        if on_progress:
            on_progress(i - 1, total, job)

        if on_log:
            on_log(f"Running {i}/{total}: {job.out_path.name}")

        r = run_openscad(openscad_exe, scad_file, job.out_path, job.defs)



        ok = (r.returncode == 0)
        results.append(
            JobResult(
                job=job,
                ok=ok,
                returncode=r.returncode,
                stdout=r.stdout,
                stderr=r.stderr,
                cmd=r.cmd,
            )
        )

        if on_log:
            if ok:
                on_log("OK")
            else:
                on_log(f"FAILED (code {r.returncode})")

        if (not ok) and stop_on_error:
            if on_log:
                on_log("Stop-on-error enabled. Aborting.")
            break

        if on_progress:
            on_progress(i, total, job)

    return results
