# Garden Sign Batch Generator

Garden Sign Batch Generator is a Windows desktop application for
batch-generating STL files using OpenSCAD.

Data can be loaded from Excel or CSV files, or entered manually directly
in the application. No Python or OpenSCAD scripting knowledge is required.

---

## Requirements

- Windows 10 or Windows 11 (64-bit)
- OpenSCAD installed

Download OpenSCAD from:  
https://openscad.org/downloads.html

On launch, the application attempts to auto-detect OpenSCAD.
If it is not found, use the **Browse...** button to locate `openscad.exe`
manually.

---

## How to Run

1. Unzip the application folder
2. Double-click `GardenSign.exe`

The application is portable and does not require installation.

---

## Adding Data

You can add data in two ways.

---

### Option 1: Load an Excel or CSV File

1. Click **Browse** under *Input*
2. Select an Excel (`.xlsx`, `.xlsm`) or CSV (`.csv`) file
3. If using Excel, select the worksheet
4. Click **Reload Preview** if needed

Rows loaded from files are **appended** to the preview table.
Existing rows are not removed.

---

### Option 2: Enter Rows Manually

- The preview table always contains an empty row at the bottom
- Double-click the **Crop** or **Cultivar** cell to edit
- Press **Enter** to save, **Escape** to cancel
- When a row becomes valid, a new empty row is added automatically

Manual rows and file-loaded rows can be mixed freely.

---


## How to Run

1. Unzip the downloaded folder
2. Double-click `GardenSign.exe`
3. Select an input spreadsheet or CSV file
4. If using Excel, select the worksheet to use
5. Review the preview table
6. Select an output folder
7. Click **Generate**

---
## Input Data Rules

Fields:

- `crop_name` (required)
- `cultivar` (optional)

Rules:

- Leading and trailing spaces are ignored
- `crop_name` must not be blank
- Rows with missing required data are marked invalid
- Invalid rows cannot be generated

---

## Input File Format

Supported file types:
- Excel: `.xlsx`, `.xlsm`
- CSV: `.csv`

Required columns (case-insensitive):

- `crop_name` (required)
- `cultivar` (optional)

### Examples

Excel:

| crop_name | cultivar   |
|----------|------------|
| Broccoli | Waltham 29 |
| Basil   |            |

CSV:

crop_name,cultivar  
Broccoli,Waltham 29  
Basil,

Notes:
- Leading and trailing spaces are ignored
- Blank `crop_name` rows are skipped
- Invalid rows are shown in the preview with a reason
- Row numbers shown match the original file

---

## Preview Table

The preview table displays:

- Row number (file row number or generated number for manual rows)
- `crop_name`
- `cultivar`
- Valid status (`Yes` or `No`)
- Reason for invalid rows

Only rows marked **Valid = Yes** can be generated.

---

## Editing and Deleting Rows

### Editing
- Double-click **Crop** or **Cultivar** to edit
- Validity updates automatically after edits

### Deleting
- Select one or more rows
- Click **Delete Selected** or press the **Delete** key
- The final empty row cannot be deleted

---

## Selecting Rows

- **Select Valid** selects all valid rows
- **Select None** clears the selection
- Invalid rows cannot be generated even if selected

---

## Generating Output

1. Select an output folder
2. Ensure OpenSCAD is detected
3. Select one or more valid rows
4. Click **Generate**

The **Generate** button is enabled only when:
- OpenSCAD is found
- An output folder is selected
- At least one valid row is selected

An input file is **not required** when entering rows manually.

## Output Files

For each selected row, the application generates STL files using
OpenSCAD.

Default filename format:

`<index>_<crop>_<cultivar>_a.stl`  
`<index>_<crop>_<cultivar>_b.stl`

Examples:

`001_BROCCOLI_WALTHAM_29_a.stl`  
`001_BROCCOLI_WALTHAM_29_b.stl`

If cultivar is blank:

`002_BASIL_a.stl`  
`002_BASIL_b.stl`

Filename rules:
- Spaces are replaced with underscores
- Illegal characters are removed or replaced
- Duplicate names are auto-suffixed unless **Overwrite** is enabled

---

## Options

- **Export A / Export B**  
  Control which output variants are generated

- **Overwrite**  
  Allows existing output files to be replaced

- **Stop on error**  
  Stops the batch if any job fails

- **Start index**  
  Sets the starting number for output filenames

---

## Progress and Logging

- A progress bar shows overall batch progress
- Log messages appear live in the application
- Logs can be copied to the clipboard

Each run also writes a log file to the output folder:

`run_YYYYMMDD_HHMMSS.log`

The log file includes:
- OpenSCAD path used
- Input file and sheet name
- Commands executed
- Errors and warnings
- Final success and failure counts

---

## Settings

The application automatically remembers:
- Last output folder
- OpenSCAD path
- Export options
- Start index

Settings are saved to:

`%APPDATA%\ModularGardenSignBatch\config.json`

---

## Troubleshooting

If OpenSCAD is not found:
- Confirm OpenSCAD is installed
- Use the **Browse...** button to select `openscad.exe` manually

If **Generate** is disabled:
- Ensure OpenSCAD is detected
- Ensure an input file is selected
- Ensure an output folder is selected
- Ensure at least one valid row is selected

If nothing is generated:
- Check the preview **Reason** column
- Review the log file in the output folder

---

## License / Source

This application is open source.

Source code and updates are available on GitHub.


