import os
import sys
import argparse
from pathlib import Path
from psd_tools import PSDImage
from contextlib import contextmanager


@contextmanager
def suppress_console_output():
    devnull = open(os.devnull, "w")
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    try:
        sys.stdout = devnull
        sys.stderr = devnull
        yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        devnull.close()


def write_font_to_file(font, output_file, allow_duplicates=False):
    output_file = Path(output_file)

    if not output_file.exists():
        try:
            output_file.touch()
        except IOError as e:
            print(f"Error creating file {output_file}: {e}")
            return

    known_fonts = read_fonts_from_file(output_file)

    if not allow_duplicates and font in known_fonts:
        return

    try:
        with open(output_file, "a") as f:
            f.write(f"{font}\n")
    except IOError as e:
        print(f"Error writing to file {output_file}: {e}")


def read_fonts_from_file(output_file):
    try:
        with open(output_file, "r") as f:
            return set(f.read().splitlines())
    except FileNotFoundError:
        print(f"File {output_file} not found")
        return set()
    except IOError as e:
        print(f"Error reading file {output_file}: {e}")
        return set()


def find_fonts_in_psd(psd_path: Path, output_file, allow_duplicates=False):
    fonts_found = set()

    # We're suppressing the console output because of some ugly errors that get thrown
    #
    # Example:
    # Unknown image resource 1092
    # Unknown key: b'CAI '
    # Unknown tagged block: b'CAI ', b'\x00\x00\x00\x03\x00\x00\x00\x10\x00\x00\x00\x01\x00\x00\x00\x00 ... =77'
    # Unknown key: b'OCIO'
    # Unknown tagged block: b'OCIO', b'\x00\x00\x00\x10\x00\x00\x00\x01\x00\x00\x00\x00\x00\x1bdo ... =170'
    # Unknown key: b'GenI'
    # Unknown tagged block: b'GenI', b'\x00\x00\x00\x10\x00\x00\x00\x01\x00\x00\x00\x00\x00\x0bge ... =55'
    #
    # Cause:
    # New resources introduced in the recent versions of Photoshop that have no known documentation
    # https://github.com/psd-tools/psd-tools/issues/415#issuecomment-2172064533

    with suppress_console_output():
        try:
            psd = PSDImage.open(psd_path)

            for layer in psd.descendants():
                if layer.kind == "type":
                    fontset = layer.resource_dict["FontSet"]
                    runlength = layer.engine_dict["StyleRun"]["RunLengthArray"]
                    rundata = layer.engine_dict["StyleRun"]["RunArray"]

                    for length, style in zip(runlength, rundata):
                        stylesheet = style["StyleSheet"]["StyleSheetData"]
                        font = fontset[stylesheet["Font"]]
                        font_name = font["Name"]

                        if isinstance(font_name, bytes):
                            font_name = font_name.decode("utf-8")
                        found_font = font_name

                        try:
                            found_font = str(found_font).strip("'")
                        except Exception:
                            pass

                        fonts_found.add(found_font)
                        write_font_to_file(found_font, output_file, allow_duplicates)

        except Exception as e:
            print(f"Error processing PSD {psd_path}: {e}")

    return fonts_found


def build_psd_paths(root_dir: Path, recursive: bool = False):
    psd_extensions = {".psd", ".psb"}
    psd_paths = set()

    if recursive:
        for path in root_dir.glob("**/*"):
            if path.suffix.lower() in psd_extensions:
                psd_paths.add(path.resolve())
    else:
        for path in root_dir.glob("*"):
            if path.suffix.lower() in psd_extensions:
                psd_paths.add(path.resolve())

    return psd_paths


def main(root_dir=None, output_file=None, recursive=False, allow_duplicates=False):
    if root_dir is None:
        root_dir = input("Enter root directory path: ").strip()
        while not os.path.isdir(root_dir):
            print("Invalid directory path. Please try again.")
            root_dir = input("Enter root directory path: ").strip()

    if output_file is None:
        output_file = "found_fonts.txt"

    psd_paths = build_psd_paths(Path(root_dir), recursive=recursive)
    all_fonts = set()

    for idx, psd_path in enumerate(psd_paths, start=1):
        print(f"Processing PSD {idx} of {len(psd_paths)}: {psd_path}")
        fonts_found = find_fonts_in_psd(psd_path, output_file, allow_duplicates)
        all_fonts.update(fonts_found)

    if not all_fonts:
        print("\nNo fonts found.")
        return

    all_fonts = sorted(all_fonts)

    print("\nFonts found:")
    for font in all_fonts:
        print(font)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Find fonts used in PSD files under a directory."
    )
    parser.add_argument(
        "--root-dir",
        type=str,
        help="Root directory containing PSD files",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        help="File to save found fonts",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Search subdirectories recursively",
    )
    parser.add_argument(
        "--allow-duplicates",
        action="store_true",
        help="Allow the same font to be saved multiple times",
    )

    args = parser.parse_args()

    if args.root_dir:
        main(args.root_dir, args.output_file, args.recursive, args.allow_duplicates)
    else:
        main()
