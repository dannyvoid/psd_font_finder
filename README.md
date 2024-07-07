
# PSD Font Finder

This script finds and logs fonts used in PSD files under a specified directory.

## Features

- **Font Extraction**: Extracts font names from PSD files.
- **Error Handling**: Handles errors related to file operations and PSD parsing.
- **Output**: Saves found fonts into a specified location (`psd_fonts.db` by default).
- **Recursive Search**: Optionally performs a recursive search through subdirectories.

## Requirements

- Python 3.x
- sqlite3
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
- `--sort-paths`: Sorts Sort PSD paths before processing (optional, alphabetically).

```
python psd_font_finder.py --root-dir /path/to/psd_files --output-file psd_fonts.db --recursive --sort-paths
```

### Notes
-   PSD files should have `.psd` or `.psb` extensions.
-   Error messages may occur due to unsupported PSD features.
