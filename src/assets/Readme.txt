OpenSCAD Sign Batch Generator
=============================

OpenSCAD Sign Batch Generator is a Windows desktop application for
batch-generating STL files using OpenSCAD from a simple spreadsheet
or CSV file.

It provides a graphical interface for previewing, validating, and
selectively generating sign models without requiring any Python or
OpenSCAD scripting knowledge.


REQUIREMENTS
------------

1. Windows 10 or Windows 11
2. OpenSCAD installed

Download OpenSCAD from:
https://openscad.org/downloads.html

On first launch, the application will attempt to auto-detect OpenSCAD.
If it is not found, use the "Browse..." button to locate openscad.exe
manually.


HOW TO RUN
----------

1. Unzip the downloaded folder
2. Double-click GardenSign.exe
3. Select an input spreadsheet or CSV file
4. (If using Excel) Select the worksheet to use
5. Review the preview table
6. Select an output folder
7. Click Generate


INPUT FILE FORMAT
-----------------

Supported file types:
- Excel: .xlsx, .xlsm
- CSV: .csv

Required columns (case-insensitive):

crop_name   (required)
cultivar    (optional)

Examples:

Excel:
+-----------+-------------+
| crop_name | cultivar    |
+-----------+-------------+
| Broccoli  | Waltham 29  |
| Basil     |             |
+-----------+-------------+

CSV:
crop_name,cultivar
Broccoli,Waltham 29
Basil,

Notes:
- Leading and trailing spaces are ignored
- Blank crop_name rows are skipped
- Invalid rows are shown in the preview with a reason
- Row numbers shown match the original file


PREVIEW TABLE
-------------

The preview table displays:
- Row number from the input file
- crop_name and cultivar values
- Whether the row is valid
- A reason for invalid rows

Only valid rows can be generated.

By default:
- All valid rows are automatically selected
- Invalid rows cannot be selected

Use the buttons above the table to:
- Select all valid rows
- Clear the current selection


OUTPUT FILES
------------

For each selected row, the application generates STL files using
OpenSCAD.

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


OPTIONS
-------

Export A / Export B
- Control which output variants are generated

Overwrite
- Allows existing output files to be replaced

Stop on error
- Stops the batch if any job fails

Start index
- Sets the starting number for output filenames


PROGRESS AND LOGGING
-------------------

- A progress bar shows overall batch progress
- Log messages appear live in the application
- Logs can be copied to the clipboard

Each run also writes a log file to the output folder:

run_YYYYMMDD_HHMMSS.log

The log file includes:
- OpenSCAD path used
- Input file and sheet name
- Commands executed
- Errors and warnings
- Final success and failure counts


SETTINGS
--------

The application automatically remembers:
- Last output folder
- OpenSCAD path
- Export options
- Start index

Settings are saved to:

%APPDATA%\OpenSCAD Sign Batch Generator\config.json


TROUBLESHOOTING
---------------

If OpenSCAD is not found:
- Confirm OpenSCAD is installed
- Use the Browse button to select openscad.exe manually

If Generate is disabled:
- Ensure OpenSCAD is detected
- Ensure an input file is selected
- Ensure an output folder is selected
- Ensure at least one valid row is selected

If nothing is generated:
- Check the preview Reason column
- Review the log file in the output folder


LICENSE / SOURCE
----------------

This application is open source.

Source code and updates are available on GitHub.
See the LICENSE file included with this distribution.
