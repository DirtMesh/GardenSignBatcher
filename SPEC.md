# OpenSCAD Sign Batch Generator

## Product Summary

**Name:** OpenSCAD Sign Batch Generator

**Goal:**  
A desktop app that batch-generates STL files from an Excel list by invoking OpenSCAD with parameter overrides.

**Target users:**  
People who can handle a simple spreadsheet but may have zero Python knowledge.

---

## Primary User Journey

1. User downloads a zip from GitHub Releases and unzips it.
2. User launches the app.
3. App checks for OpenSCAD availability and shows status.
4. User selects an Excel file (`.xlsx`).
5. App loads the sheet, previews rows, and flags invalid entries with reasons.
6. User selects an output folder.
7. User optionally adjusts settings (exports A/B, start index, stop-on-error).
8. User clicks **Generate**.
9. App shows progress, logs output, and allows cancel.
10. App shows a completion summary and writes a run log to the output folder.

---

## Non-goals (v1)

- No editing of the SCAD design inside the app.
- No cross-platform support in v1 (Windows 10/11 only).
- No bundling of OpenSCAD in v1.
- No cloud features, telemetry, or auto-updating.

---

## Inputs and Outputs

### Input File Type

- Excel workbook: `.xlsx`

### Required Columns

- `crop_name` (required, non-empty after trimming)
- `cultivar` (optional)

**Column matching rules:**
- Case-insensitive match.
- Leading and trailing whitespace ignored.
- Accept common variants optionally (future): `crop`, `cult` (not required for v1).

---

### Output Files

For each selected valid row, produce up to two STL files:

- **Part A:** `<index>_<crop>_<cultivar>_a.stl`
- **Part B:** `<index>_<crop>_<cultivar>_b.stl`

**Rules:**
- Index is 3 digits, 1-based by default: `001`, `002`, ...
- If `cultivar` is blank, omit it from filename:  
  `<index>_<crop>_a.stl`
- Filenames are sanitized:
  - Spaces become `_`
  - Illegal characters `\ / : * ? " < > |` replaced with `_`
  - Multiple `_` collapsed
  - Leading and trailing `_` removed

**Duplicate filename handling:**
- If an output filename already exists in the output folder from the current run plan, append a deterministic suffix.
- Example:  
  `003_BROCCOLI_WALTHAM_29_a.stl`  
  `003_BROCCOLI_WALTHAM_29_02_a.stl`
- The suffix applies before `_a` or `_b` if that simplifies parsing.

---

### Run Log

- Always write a run log file to the output folder:
  - `run_YYYYMMDD_HHMMSS.log`

**Log includes:**
- App version
- OpenSCAD path used
- SCAD resource path used
- Input workbook path and sheet name
- Row counts: total, valid, selected, skipped, failed
- Command line used per job (copyable format)
- `stdout` and `stderr` from OpenSCAD when available

---

## OpenSCAD Dependency Detection

### Detection Order

1. User-configured OpenSCAD path (persisted setting) if present and valid.
2. `openscad.exe` found via PATH.
3. Common install paths:
   - `C:\Program Files\OpenSCAD\openscad.exe`
   - `C:\Program Files (x86)\OpenSCAD\openscad.exe`
4. If not found, the UI shows **OpenSCAD not found** and offers:
   - Browse to select `openscad.exe`
   - Link or instructions on where to install OpenSCAD

### Preconditions to Enable Generate

The **Generate** button is disabled unless:
- OpenSCAD is found and executable
- SCAD file resource is available
- Excel input is loaded
- Output folder is selected and writable
- At least one valid row is selected

---

## SCAD File Handling (Bundled)

- The `sign_generator.scad` file ships with the app.
- The app resolves it at runtime using a resource-path helper that works for:
  - Running from source
  - PyInstaller builds (`sys._MEIPASS`)

**Optional advanced behavior (v1.1+):**
- Allow user to override the SCAD path with a custom file.

---

## UI Requirements

### Main Window Sections

#### OpenSCAD Status
- Status text: Found or Not Found, plus resolved path
- Buttons:
  - Auto-detect
  - Browse

#### Input
- Button: Select Excel
- After load: Sheet dropdown
- Table preview:
  - Columns: Row#, `crop_name`, `cultivar`, Valid (Yes or No), Reason
  - Invalid rows highlighted
- Selection controls:
  - Select All
  - Select Valid
  - Select None

#### Output
- Button: Select output folder
- Display selected folder path

#### Options
- Export Part A (default on)
- Export Part B (default on)
- Start index (default 1)
- Stop on first error (default off)
- Overwrite existing files:
  - Default off
  - If off, use suffixing as described
  - If on, overwrite without suffix

#### Run Controls
- Progress bar
- Current job label, example: `12/84: Broccoli / Waltham 29`
- Buttons:
  - Generate (disabled until ready)
  - Cancel (enabled only while running)

#### Log Panel
- Scrollable text area showing recent log lines
- Button: Copy log to clipboard (optional)

---

### Responsiveness

- The UI must remain responsive during generation.
- OpenSCAD invocations happen in a background worker.
- UI updates via a thread-safe queue.

---

### Completion Summary

At end of run, show:
- Completed count
- Failed count
- Skipped count
- Output folder path
- Log file path

---

## Error Handling Requirements

- If OpenSCAD returns non-zero for a job:
  - Mark that row or job as failed
  - Capture `stdout` and `stderr`
  - Continue unless Stop-on-error is enabled

- Any crash-worthy exception must be caught and displayed:
  - User-friendly message
  - Expandable technical details (stack trace)
  - Pointer to log file

---

## Persistence

Persist these settings:
- Last OpenSCAD path (if user set it)
- Last input folder
- Last output folder
- Export A/B toggles
- Stop-on-error toggle
- Overwrite toggle
- Start index

**Storage location:**

    %APPDATA%<AppName>\config.json


---

## Packaging and Distribution (v1)

- Distribution artifact: zipped PyInstaller build for Windows
- Include the bundled SCAD file
- Include a short `README.txt` in the release zip:
  - How to run
  - How to install OpenSCAD
  - Minimal spreadsheet format
  - Where logs are saved

---

## Acceptance Criteria (v1)

A release is considered v1-ready when:
- A new user can generate STLs from the example workbook without reading code.
- The app blocks Generate when prerequisites are missing and clearly explains why.
- The UI stays responsive and supports cancel.
- Logs are written reliably and contain enough data to troubleshoot.
- The packaged build includes the SCAD file and runs on a clean Windows machine with OpenSCAD installed.
