from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


COMMON_PATHS = [
    Path(r"C:\Program Files\OpenSCAD\openscad.exe"),
    Path(r"C:\Program Files (x86)\OpenSCAD\openscad.exe"),
]


def detect_openscad(user_path: Optional[Path] = None) -> Optional[Path]:
    if user_path and user_path.exists():
        return user_path

    which = shutil.which("openscad")
    if which:
        p = Path(which)
        if p.exists():
            return p

    for p in COMMON_PATHS:
        if p.exists():
            return p

    return None


@dataclass(frozen=True)
class OpenScadResult:
    returncode: int
    stdout: str
    stderr: str
    cmd: list[str]


def run_openscad(openscad_exe: Path, scad_file: Path, out_path: Path, defs: dict) -> OpenScadResult:
    args: list[str] = [str(openscad_exe), "-o", str(out_path)]

    for k, v in defs.items():
        if isinstance(v, str):
            # Let subprocess handle arg quoting; just ensure embedded quotes are escaped
            v2 = v.replace('"', r'\"')
            args += ["-D", f'{k}="{v2}"']
        else:
            args += ["-D", f"{k}={v}"]

    args.append(str(scad_file))

    cp = subprocess.run(args, capture_output=True, text=True)
    return OpenScadResult(
        returncode=cp.returncode,
        stdout=cp.stdout or "",
        stderr=cp.stderr or "",
        cmd=args,
    )
