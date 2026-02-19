OpenSCAD Sign Batch Generator
============================

OpenSCAD Sign Batch Generator is a Windows desktop application for
batch-generating STL files using OpenSCAD.

You can load data from Excel or CSV files, or enter rows manually
directly in the application. No Python or OpenSCAD scripting knowledge
is required.

----------------------------------------------------------------------
REQUIREMENTS
----------------------------------------------------------------------

- Windows 10 or Windows 11 (64-bit)
- OpenSCAD installed

Download OpenSCAD from:
https://openscad.org/downloads.html

On launch, the application will attempt to auto-detect OpenSCAD.
If it is not found, use the "Browse..." button to locate openscad.exe
manually.

----------------------------------------------------------------------
HOW TO RUN
----------------------------------------------------------------------

1. Unzip the application folder
2. Double-click GardenSign.exe

The application is portable and does not require installation.

----------------------------------------------------------------------
ADDING DATA
----------------------------------------------------------------------

You can add data in two ways.

----------------------------------------------------------------------
OPTION 1: LOAD AN EXCEL OR CSV FILE
----------------------------------------------------------------------

1. Click "Browse" under Input
2. Select an Excel (.xlsx, .xlsm) or CSV (.csv) file
3. If using Excel, select a worksheet
4. Click "Reload Preview" if needed

Rows from files are APPENDED to the preview table.
Existing rows are not removed.

----------------------------------------------------------------------
OPTION 2: ENTER ROWS MANUALLY
----------------------------------------------------------------------

- The preview table always contains an empty row at the bottom
- Double-click the Crop or Cultivar cell to edit
- Press Enter to save, Escape to cancel
- When a row becomes valid, a new empty row is added automatically

Manual rows and file-loaded rows can be mixed freely.

----------------------------------------------------------------------
INPUT DATA RULES
----------------------------------------------------------------------

Fields:

- crop_name (required)
- cultivar (optional)

Rules:

- Leading and trailing spaces are ignored
- crop_name must not be blank
- Rows with missing required data are marked invalid
- Invalid rows cannot be generated

----------------------------------------------------------------------
PREVIEW TABLE
----------------------------------------------------------------------

The preview table shows:

- Row number (file row number or generated number for manual rows)
- crop_name
- cultivar
- Valid status (Yes or No)
- Reason for invalid rows

Only rows marked "Valid = Yes" can be generated.

----------------------------------------------------------------------
EDITING AND DELETING ROWS
----------------------------------------------------------------------

Editing:
- Double-click Crop or Cultivar to edit
- Validity updates automatically

Deleting:
- Select one or more rows
- Click "Delete Selected" or press Delete
- The final empty row cannot be deleted

----------------------------------------------------------------------
SELECTING ROWS
----------------------------------------------------------------------

- "Select Valid" selects all valid rows
- "Select None" clears the selection
- Invalid rows cannot be generated even if selected

----------------------------------------------------------------------
GENERATING OUTPUT
----------------------------------------------------------------------

1. Select an output folder
2. Ensure OpenSCAD is detected
3. Select one or more valid rows
4. Click "Generate"

The Generate button is enabled only when:
- OpenSCAD is found
- An output folder is selected
- At least one valid row is selected

An input file is NOT required if entering rows manually.

----------------------------------------------------------------------
OUTPUT FILES
----------------------------------------------------------------------

For each selected row, STL files are generated using OpenSCAD.

Default filename format:

<index>_<crop>_<cultivar>_a.stl
<index>_<crop>_<cultivar>_b.stl

Examples:

001_BROCCOLI_WALTHAM_29_a.stl
001_BROCCOLI_WALTHAM_29_b.stl

If cultivar is blank:

002_BASIL_a.stl
002_BASIL_b.stl

Filename rules:
- Spaces are replaced with underscores
- Illegal characters are removed or replaced
- Duplicate names are auto-suffixed unless Overwrite is enabled

----------------------------------------------------------------------
OPTIONS
----------------------------------------------------------------------

Export A / Export B
  Control which output variants are generated

Overwrite
  Allows existing output files to be replaced

Stop on error
  Stops the batch if any job fails

Start index
  Sets the starting number for output filenames

----------------------------------------------------------------------
PROGRESS AND LOGGING
----------------------------------------------------------------------

- A progress bar shows overall batch progress
- Log messages appear live in the application
- Logs can be copied to the clipboard

Each run also writes a log file to the output folder:

run_YYYYMMDD_HHMMSS.log

The log file includes:
- OpenSCAD path used
- Rows generated
- Commands executed
- Errors and warnings
- Final success and failure counts

----------------------------------------------------------------------
SETTINGS
----------------------------------------------------------------------

The application automatically remembers:
- Last output folder
- OpenSCAD path
- Export options
- Start index

Settings are stored in a user-specific configuration file.

----------------------------------------------------------------------
TROUBLESHOOTING
----------------------------------------------------------------------

If OpenSCAD is not found:
- Confirm OpenSCAD is installed
- Use the Browse button to select openscad.exe manually

If Generate is disabled:
- Ensure an output folder is selected
- Ensure at least one valid row is selected
- Ensure OpenSCAD is detected

If nothing is generated:
- Check the Reason column in the preview table
- Review the log file in the output folder

----------------------------------------------------------------------
LICENSE / SOURCE
----------------------------------------------------------------------

This application is open source.

Source code and updates are available from the project repository.
See the LICENSE file included with this distribution.
