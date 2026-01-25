import csv
import subprocess
import re
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

# -------- CONFIG --------
OPENSCAD = r"C:\Program Files\OpenSCAD\openscad.exe"
SCAD     = r"C:\prints\job_test\sign_generator.scad"
OUTDIR   = r"C:\prints\job_test\out"
# ------------------------

def pick_csv_file() -> Path | None:
    root = tk.Tk()
    root.withdraw()  # hide empty tkinter window
    root.attributes("-topmost", True)

    path = filedialog.askopenfilename(
        title="Select crop CSV file",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )

    root.destroy()
    return Path(path) if path else None

def sanitize_filename(s: str) -> str:
    if not s:
        return ""
    s = s.strip()
    s = s.replace(" ", "_")
    s = re.sub(r'[\\/:*?"<>|]+', "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s

def openscad_export(out_path: Path, defs: dict):
    args = [OPENSCAD, "-o", str(out_path)]
    for k, v in defs.items():
        if isinstance(v, str):
            v = v.replace('"', r'\"')
            args += ["-D", f'{k}="{v}"']
        else:
            args += ["-D", f"{k}={v}"]
    args.append(SCAD)

    print(" ".join(args))
    subprocess.run(args, check=True)

def main():
    csv_path = pick_csv_file()
    if not csv_path:
        print("No CSV selected. Exiting.")
        return

    Path(OUTDIR).mkdir(parents=True, exist_ok=True)

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    index = 0

    for row in rows:
        crop = (row.get("crop_name") or "").strip()
        cultivar = (row.get("cultivar") or "").strip()

        if not crop:
            continue

        index += 1
        n = f"{index:03d}"

        crop_safe = sanitize_filename(crop)
        cult_safe = sanitize_filename(cultivar)

        base = f"{n}_{crop_safe}"
        if cultivar:
            base += f"_{cult_safe}"

        out_a = Path(OUTDIR) / f"{base}_a.stl"
        out_b = Path(OUTDIR) / f"{base}_b.stl"

        common_defs = {
            "crop_name": crop,
            "cultivar": cultivar
        }

        openscad_export(out_a, {**common_defs, "export_part": "a"})
        openscad_export(out_b, {**common_defs, "export_part": "b"})

    print(f"\nDone. Exported {index} sign set(s) to {OUTDIR}")

if __name__ == "__main__":
    main()
