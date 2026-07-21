#!/usr/bin/env python3
"""Extract user files from a Moodle .mbz backup using files.xml metadata.

Moodle stores file bytes under files/<first 2 hash chars>/<next 2>/<contenthash>.
This script reconstructs original filenames and Moodle file paths, and writes a
CSV manifest so every extracted file can be traced back to its backup record.

Python 3.9+; standard library only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import shutil
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET


MANIFEST_FIELDS = [
    "file_id", "original_filename", "original_filepath", "component",
    "filearea", "itemid", "contextid", "contenthash", "mimetype",
    "filesize", "author", "license", "source", "timecreated",
    "timemodified", "extracted_path", "status", "note",
]


def safe_part(value: str | None, fallback: str = "unknown") -> str:
    """Return a filesystem-safe single path component."""
    value = (value or "").strip().replace("\x00", "")
    value = re.sub(r"[\\/:*?\"<>|]", "_", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return value or fallback


def safe_moodle_path(value: str | None) -> Path:
    """Convert Moodle's POSIX filepath to a safe relative Path."""
    parts = []
    for part in PurePosixPath(value or "/").parts:
        if part not in ("/", "", ".", ".."):
            parts.append(safe_part(part))
    return Path(*parts) if parts else Path()


def unique_path(path: Path, file_id: str) -> tuple[Path, str]:
    if not path.exists():
        return path, ""
    candidate = path.with_name(f"{path.stem}__file-{safe_part(file_id)}{path.suffix}")
    counter = 2
    while candidate.exists():
        candidate = path.with_name(
            f"{path.stem}__file-{safe_part(file_id)}-{counter}{path.suffix}"
        )
        counter += 1
    return candidate, f"Name collision; saved as {candidate.name}"


def is_within(base: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def extract_archive_safely(archive: Path, destination: Path) -> None:
    """Extract ZIP or TAR Moodle backups without path traversal or links."""
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                target = destination / info.filename
                if not is_within(destination, target):
                    raise ValueError(f"Unsafe archive path: {info.filename}")
                # Reject Unix symlinks stored in ZIP metadata.
                if (info.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError(f"Archive contains a symbolic link: {info.filename}")
            zf.extractall(destination)
        return

    try:
        with tarfile.open(archive, "r:*") as tf:
            for member in tf.getmembers():
                target = destination / member.name
                if not is_within(destination, target):
                    raise ValueError(f"Unsafe archive path: {member.name}")
                if member.issym() or member.islnk() or member.isdev():
                    raise ValueError(f"Archive contains an unsafe link/device: {member.name}")
            tf.extractall(destination, filter="data")
    except tarfile.ReadError as exc:
        raise ValueError("Input is not a supported ZIP or TAR-based Moodle backup") from exc


def find_backup_root(root: Path) -> Path:
    matches = list(root.rglob("files.xml"))
    if not matches:
        raise FileNotFoundError("files.xml was not found in the backup")
    if len(matches) > 1:
        raise ValueError(f"More than one files.xml found: {len(matches)}")
    return matches[0].parent


def text_of(element: ET.Element, name: str) -> str:
    child = element.find(name)
    return (child.text or "").strip() if child is not None else ""


def source_path(backup_root: Path, contenthash: str) -> Path | None:
    """Locate content in either Moodle backup or Moodledata-style storage."""
    candidates = (
        # Standard Moodle backup layout.
        backup_root / "files" / contenthash,
        # Common Moodle .mbz layout: first two hash characters, then full hash.
        backup_root / "files" / contenthash[:2] / contenthash,
        # Moodledata filedir layout, supported for extracted/nonstandard inputs.
        backup_root / "files" / contenthash[:2] / contenthash[2:4] / contenthash,
    )
    return next((path for path in candidates if path.is_file()), None)


def destination_path(output: Path, record: dict[str, str], flat: bool) -> Path:
    filename = safe_part(record["original_filename"], f"file-{record['file_id']}")
    if flat:
        return output / "files" / filename
    return (
        output / "files"
        / safe_part(record["component"])
        / safe_part(record["filearea"])
        / safe_part(record["itemid"], "0")
        / safe_moodle_path(record["original_filepath"])
        / filename
    )


def sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_files(backup_root: Path, output: Path, flat: bool,
                  include_directories: bool, verify_hashes: bool) -> tuple[int, int, int]:
    output.mkdir(parents=True, exist_ok=True)
    manifest = output / "moodle_file_manifest.csv"
    extracted = missing = skipped = 0

    with manifest.open("w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        for _event, elem in ET.iterparse(backup_root / "files.xml", events=("end",)):
            if elem.tag.rsplit("}", 1)[-1] != "file":
                continue
            record = {
                "file_id": elem.get("id", ""),
                "original_filename": text_of(elem, "filename"),
                "original_filepath": text_of(elem, "filepath"),
                "component": text_of(elem, "component"),
                "filearea": text_of(elem, "filearea"),
                "itemid": text_of(elem, "itemid"),
                "contextid": text_of(elem, "contextid"),
                "contenthash": text_of(elem, "contenthash"),
                "mimetype": text_of(elem, "mimetype"),
                "filesize": text_of(elem, "filesize"),
                "author": text_of(elem, "author"),
                "license": text_of(elem, "license"),
                "source": text_of(elem, "source"),
                "timecreated": text_of(elem, "timecreated"),
                "timemodified": text_of(elem, "timemodified"),
                "extracted_path": "", "status": "", "note": "",
            }

            # Moodle represents directories as filename='.'.
            if record["original_filename"] == ".":
                if include_directories:
                    dest = destination_path(output, {**record, "original_filename": "directory"}, flat).parent
                    dest.mkdir(parents=True, exist_ok=True)
                record["status"] = "directory_record"
                skipped += 1
                writer.writerow(record)
                elem.clear()
                continue

            contenthash = record["contenthash"]
            source = source_path(backup_root, contenthash) if len(contenthash) >= 4 else None
            if not contenthash or source is None:
                record["status"] = "missing"
                record["note"] = "Content-hash file is absent from the backup"
                missing += 1
            else:
                dest, note = unique_path(destination_path(output, record, flat), record["file_id"])
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
                record["extracted_path"] = str(dest.relative_to(output))
                record["status"] = "extracted"
                record["note"] = note
                if verify_hashes and sha1(dest) != contenthash:
                    record["status"] = "hash_mismatch"
                    record["note"] = (note + "; " if note else "") + "Extracted SHA-1 differs from files.xml"
                extracted += 1
            writer.writerow(record)
            elem.clear()
    return extracted, missing, skipped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract files with original filenames from a Moodle .mbz backup."
    )
    parser.add_argument("backup", type=Path, help="Moodle .mbz file or extracted backup directory")
    parser.add_argument("--output", "-o", type=Path, default=Path("moodle_extracted_files"))
    parser.add_argument("--flat", action="store_true", help="Put all files in one folder (duplicates are renamed)")
    parser.add_argument("--include-directories", action="store_true", help="Recreate empty Moodle directory records")
    parser.add_argument("--verify-hashes", action="store_true", help="Recalculate SHA-1 for each extracted file")
    parser.add_argument("--overwrite-output", action="store_true", help="Allow use of a non-empty output directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    backup = args.backup.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not backup.exists():
        print(f"Error: backup not found: {backup}", file=sys.stderr)
        return 2
    if output.exists() and any(output.iterdir()) and not args.overwrite_output:
        print(f"Error: output directory is not empty: {output}\nUse --overwrite-output or choose another directory.", file=sys.stderr)
        return 2

    try:
        if backup.is_dir():
            root = find_backup_root(backup)
            counts = extract_files(root, output, args.flat, args.include_directories, args.verify_hashes)
        else:
            with tempfile.TemporaryDirectory(prefix="moodle_mbz_") as temp:
                temp_path = Path(temp)
                extract_archive_safely(backup, temp_path)
                root = find_backup_root(temp_path)
                counts = extract_files(root, output, args.flat, args.include_directories, args.verify_hashes)
    except (OSError, ValueError, ET.ParseError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    extracted, missing, skipped = counts
    print(f"Extracted {extracted} files; {missing} missing; {skipped} directory records skipped.")
    print(f"Files:    {output / 'files'}")
    print(f"Manifest: {output / 'moodle_file_manifest.csv'}")
    return 0 if missing == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
