OpenSCAD Sign Batch Generator
=============================

This application batch-generates STL files using OpenSCAD from a simple
spreadsheet or CSV file.

No Python knowledge is required.


REQUIREMENTS
------------

1. Windows 10 or Windows 11
2. OpenSCAD installed

Download OpenSCAD from:
https://openscad.org/downloads.html

During first launch, the app will try to auto-detect OpenSCAD.
If it is not found, use the "Browse..." button to locate openscad.exe.


HOW TO RUN
----------

1. Unzip the downloaded folder
2. Double-click GardenSign.exe
3. Select an input spreadsheet or CSV file
4. Select an output folder
5. Review the preview table
6. Click Generate


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


PREVIEW TABLE
-------------

The preview shows:
- Row number from the input file
- crop_name and cultivar
- Whether the row is valid
- Reason for invalid rows

Only valid rows can be generated.
By default, all valid rows are selected.


OUTPUT FILES
------------

For each selected row, the app generates STL files:

<index>_<crop>_<cultivar>_a.stl
<index>_<crop>_<cultivar>_b.stl

Examples:
001_BROCCOLI_WALTHAM_29_a.stl
001_BROCCOLI_WALTHAM_29_b.stl

If cultivar is blank:
002_BASIL_a.stl

Filename rules:
- Spaces become underscores
- Illegal characters are replaced
- Duplicate names are auto-suffixed unless Overwrite is enabled


LOG FILES
---------

Each run writes a log file to the output folder:

run_YYYYMMDD_HHMMSS.log

The log includes:
- OpenSCAD path used
- Input file and sheet
- Commands executed
- Errors and warnings

You can also view logs live in the app and copy them to the clipboard.


SETTINGS
--------

The app remembers:
- Last output folder
- OpenSCAD path
- Export options
- Start index

Settings are stored in:
%APPDATA%\OpenSCAD Sign Batch Generator\config.json


TROUBLESHOOTING
---------------

If OpenSCAD is not found:
- Make sure OpenSCAD is installed
- Use the Browse button to select openscad.exe

If nothing generates:
- Ensure at least one valid row is selected
- Check the preview Reason column
- Review the log file in the output folder


LICENSE / SOURCE
----------------

This application is open source.
See the GitHub repository for updates and source code.
