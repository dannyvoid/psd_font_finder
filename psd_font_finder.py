import os
import sys
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
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


@contextmanager
def db_connection(db_path):
    conn = sqlite3.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


def create_tables(conn):
    try:
        sql_create_psd_table = """CREATE TABLE IF NOT EXISTS psd_files (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    file_path TEXT UNIQUE,
                                    creation_date TEXT,
                                    modification_date TEXT
                                  );"""
        sql_create_fonts_table = """CREATE TABLE IF NOT EXISTS fonts (
                                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                                      font_name TEXT UNIQUE
                                    );"""
        sql_create_psd_fonts_table = """CREATE TABLE IF NOT EXISTS psd_fonts (
                                          psd_id INTEGER,
                                          font_id INTEGER,
                                          FOREIGN KEY (psd_id) REFERENCES psd_files (id),
                                          FOREIGN KEY (font_id) REFERENCES fonts (id),
                                          PRIMARY KEY (psd_id, font_id)
                                        );"""
        cursor = conn.cursor()
        cursor.execute(sql_create_psd_table)
        cursor.execute(sql_create_fonts_table)
        cursor.execute(sql_create_psd_fonts_table)
        conn.commit()
        print("Tables created successfully")
    except sqlite3.Error as e:
        print(f"Error creating tables: {e}")


def get_file_dates(file_path):
    file_stat = os.stat(file_path)
    creation_date = datetime.fromtimestamp(file_stat.st_ctime).isoformat()
    modification_date = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
    return creation_date, modification_date


def insert_psd_file(conn, psd_path):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM psd_files WHERE file_path = ?", (str(psd_path),))
        row = cursor.fetchone()
        if row:
            return row[0]
        else:
            creation_date, modification_date = get_file_dates(psd_path)
            sql_insert_psd = """INSERT INTO psd_files (file_path, creation_date, modification_date)
                                VALUES (?, ?, ?);"""
            cursor.execute(
                sql_insert_psd, (str(psd_path), creation_date, modification_date)
            )
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Error inserting or retrieving PSD file {psd_path}: {e}")
        return None


def update_psd_file(conn, psd_id, psd_path):
    _, modification_date = get_file_dates(psd_path)
    try:
        sql_update_psd = """UPDATE psd_files
                            SET modification_date = ?
                            WHERE id = ?;"""
        cursor = conn.cursor()
        cursor.execute(sql_update_psd, (modification_date, psd_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error updating PSD file {psd_path}: {e}")


def insert_font(conn, font_name):
    try:
        sql_insert_font = """INSERT OR IGNORE INTO fonts (font_name)
                             VALUES (?);"""
        cursor = conn.cursor()
        cursor.execute(sql_insert_font, (font_name,))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Error inserting font {font_name}: {e}")
        return None


def link_psd_font(conn, psd_id, font_id):
    try:
        sql_insert_psd_font = """INSERT OR IGNORE INTO psd_fonts (psd_id, font_id)
                                 VALUES (?, ?);"""
        cursor = conn.cursor()
        cursor.execute(sql_insert_psd_font, (psd_id, font_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error linking PSD {psd_id} with font {font_id}: {e}")


def sanitize_fontname(fontname: str) -> str:
    fontname = str(fontname)
    fontname = fontname.strip("'")
    fontname = fontname.strip('"')
    return fontname


def find_fonts_in_psd(conn, psd_id, psd_path):
    fonts_found = set()

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
                            found_font = sanitize_fontname(found_font)
                        except Exception:
                            pass

                        if found_font not in fonts_found:
                            fonts_found.add(found_font)
                            font_id = insert_font(conn, found_font)
                            if font_id:
                                link_psd_font(conn, psd_id, font_id)

        except Exception as e:
            print(f"Error processing PSD {psd_path}: {e}")

    return fonts_found


def build_psd_paths(
    root_dir: Path, recursive: bool = False, sort_paths: bool = False
) -> set:
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

    if sort_paths:
        psd_paths = sorted(psd_paths)

    return psd_paths


def main(root_dir=None, db_path=None, recursive=False, sort_paths=False) -> None:
    if root_dir is None:
        root_dir = input("Enter root directory path: ").strip()
        while not os.path.isdir(root_dir):
            print("Invalid directory path. Please try again.")
            root_dir = input("Enter root directory path: ").strip()

    if db_path is None:
        db_path = "psd_fonts.db"

    with db_connection(db_path) as conn:
        create_tables(conn)
        psd_paths = build_psd_paths(
            Path(root_dir), recursive=recursive, sort_paths=sort_paths
        )

        for idx, psd_path in enumerate(psd_paths, start=1):
            print(f"Processing PSD {idx} of {len(psd_paths)}: {psd_path}")

            # Check if the PSD file already exists in the database
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM psd_files WHERE file_path = ?", (str(psd_path),)
            )
            row = cursor.fetchone()

            if row:
                print(f"Skipping PSD {psd_path} as it's already processed.")
                continue  # Skip further processing

            psd_id = insert_psd_file(conn, psd_path)

            if psd_id is not None:
                update_psd_file(conn, psd_id, psd_path)
                find_fonts_in_psd(conn, psd_id, psd_path)
            else:
                print(f"Error processing PSD: {psd_path}")

    print("Processing complete.")


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
        "--db-path",
        type=str,
        help="Path to the SQLite database file",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Search subdirectories recursively",
    )
    parser.add_argument(
        "--sort-paths",
        action="store_true",
        help="Sort PSD paths before processing",
    )

    args = parser.parse_args()

    if args.root_dir:
        main(args.root_dir, args.db_path, args.recursive, args.sort_paths)
    else:
        main()
