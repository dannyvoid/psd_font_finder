
# PSD Font Finder

This script finds and logs fonts used in PSD files under a specified directory.

## Features

- **Font Extraction**: Extracts font names from PSD files.
- **Error Handling**: Handles errors related to file operations and PSD parsing.
- **Output**: Saves found fonts into a specified output file (`found_fonts.txt` by default).
- **Recursive Search**: Optionally performs a recursive search through subdirectories.

## Requirements

- Python 3.x
- `psd_tools` library (install via `pip install psd-tools`)

## Usage

### Running the Script

You can run the script with optional arguments:

```bash
python psd_font_finder.py --root-dir <directory_path> --output-file <output_file_path>
```

### Arguments
- `--root-dir`: Root directory containing PSD files to search (mandatory).
- `--output-file`: File path to save found fonts (optional, default: `found_fonts.txt`).
- `--recursive`: Perform a recursive search through subdirectories (optional).
- `--allow-duplicates`: Allows the same font to be logged more than once (optional).

```
python psd_font_finder.py --root-dir /path/to/psd_files --output-file output_fonts.txt --recursive --allow-duplicates
```

### Notes
-   PSD files should have `.psd` or `.psb` extensions.
-   Error messages may occur due to unsupported PSD features.
