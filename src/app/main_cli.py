from __future__ import annotations

import argparse
from pathlib import Path
import sys
from datetime import datetime

from app.engine.input_reader import read_input_rows
from app.engine.openscad import detect_openscad
from app.engine.planner import plan_jobs
from app.engine.resources import resource_path
from app.engine.runner import run_jobs
from app.engine.logger import RunLogger
from app.engine.config import load_config, save_config


def write_run_header(
    log,
    *,
    input_path: Path,
    sheet: str | None,
    outdir: Path,
    openscad: Path,
    scad: Path,
    options: dict,
) -> None:
    log("=== OpenSCAD Sign Batch Generator ===")
    log(f"Timestamp: {datetime.now().isoformat(timespec='seconds')}")
    log(f"Input file: {input_path}")
    if sheet:
        log(f"Sheet: {sheet}")
    log(f"Output dir: {outdir}")
    log(f"OpenSCAD: {openscad}")
    log(f"SCAD file: {scad}")
    for k, v in options.items():
        log(f"Option {k}: {v}")
    log("=" * 40)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Batch-generate STL files from an Excel (.xlsx) or CSV list using OpenSCAD."
    )

    p.add_argument("input", type=Path, help="Input file: .xlsx/.xlsm or .csv")
    p.add_argument("outdir", type=Path, help="Output directory")

    p.add_argument(
        "--sheet",
        help="Excel sheet name (Excel only; default: first sheet). Ignored for CSV.",
    )

    # Defaults intentionally None so config can apply
    p.add_argument("--start-index", type=int, default=None)

    p.add_argument("--export-a", dest="export_a", action="store_true", default=None)
    p.add_argument("--no-export-a", dest="export_a", action="store_false")

    p.add_argument("--export-b", dest="export_b", action="store_true", default=None)
    p.add_argument("--no-export-b", dest="export_b", action="store_false")

    p.add_argument("--overwrite", action="store_true", default=None)
    p.add_argument("--stop-on-error", action="store_true", default=None)

    p.add_argument(
        "--openscad",
        type=Path,
        help="Path to openscad.exe (override auto-detection)",
    )

    return p.parse_args()


def main() -> int:
    cfg = load_config()
    args = parse_args()

    # ---- early validation (no logger yet) ----

    if not args.input.exists():
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        return 2

    scad = resource_path("assets/sign_generator.scad")
    if not scad.exists():
        print(f"ERROR: SCAD file not found: {scad}", file=sys.stderr)
        return 2

    openscad_override = args.openscad or cfg.get("openscad_path")
    openscad = detect_openscad(Path(openscad_override) if openscad_override else None)

    if not openscad:
        print("ERROR: OpenSCAD not found.", file=sys.stderr)
        return 2

    # ---- merge config defaults ----

    if args.start_index is None:
        args.start_index = cfg.get("start_index", 1)

    if args.export_a is None:
        args.export_a = cfg.get("export_a", True)

    if args.export_b is None:
        args.export_b = cfg.get("export_b", True)

    if args.overwrite is None:
        args.overwrite = cfg.get("overwrite", False)

    if args.stop_on_error is None:
        args.stop_on_error = cfg.get("stop_on_error", False)

    # ---- logger lifecycle ----

    logger = RunLogger(args.outdir)
    log = logger.tee(print)

    try:
        # ---- read input ----

        rows, issues, resolved_sheet = read_input_rows(args.input, sheet=args.sheet)

        write_run_header(
            log,
            input_path=args.input,
            sheet=resolved_sheet,
            outdir=args.outdir,
            openscad=openscad,
            scad=scad,
            options={
                "export_a": args.export_a,
                "export_b": args.export_b,
                "start_index": args.start_index,
                "overwrite": args.overwrite,
                "stop_on_error": args.stop_on_error,
            },
        )

        if args.input.suffix.lower() == ".csv" and args.sheet:
            log("WARN: --sheet is ignored for CSV input.")

        log(f"Loaded {len(rows)} row(s), {len(issues)} issue(s)")

        if issues:
            for iss in issues[:20]:
                log(f"Issue at row {iss.row_num}: {iss.reason}")
            if len(issues) > 20:
                log(f"... and {len(issues) - 20} more issue(s)")

        if not rows:
            log("ERROR: No valid rows to process.")
            return 2

        # ---- plan and run ----

        jobs = plan_jobs(
            rows,
            args.outdir,
            export_a=args.export_a,
            export_b=args.export_b,
            start_index=args.start_index,
            overwrite=args.overwrite,
        )

        results = run_jobs(
            jobs,
            openscad_exe=openscad,
            scad_file=scad,
            stop_on_error=args.stop_on_error,
            on_log=log,
        )

        ok = sum(1 for r in results if r.ok)
        fail = sum(1 for r in results if not r.ok)

        # ---- persist config ----

        cfg["last_input_dir"] = str(args.input.parent)
        cfg["last_output_dir"] = str(args.outdir)
        if args.openscad:
            cfg["openscad_path"] = str(args.openscad)

        cfg["export_a"] = args.export_a
        cfg["export_b"] = args.export_b
        cfg["overwrite"] = args.overwrite
        cfg["stop_on_error"] = args.stop_on_error
        cfg["start_index"] = args.start_index

        save_config(cfg)

        log(f"Done. OK={ok} FAIL={fail}")
        log(f"Log file: {logger.path}")

        return 0 if fail == 0 else 1

    finally:
        logger.close()


if __name__ == "__main__":
    raise SystemExit(main())
