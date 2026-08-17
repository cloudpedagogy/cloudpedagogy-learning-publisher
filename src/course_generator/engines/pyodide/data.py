"""Course-local data staging helpers for Pyodide."""

import base64
from pathlib import Path


PYODIDE_DATA_MAX_FILE_BYTES = 2 * 1024 * 1024
PYODIDE_DATA_MAX_BLOCK_BYTES = 8 * 1024 * 1024


def resolve_pyodide_data_files(
    data_values: list[str],
    course_source_dir: Path,
) -> list[dict]:
    """
    Resolve and embed course-local data files for a Pyodide code block.

    Authoring paths must be relative to the course folder, for example:
        Data :: resources/data/example.csv

    Files are staged inside Pyodide under:
        data/<filename>

    Multiple Data :: lines are supported.
    """
    if not data_values:
        return []

    course_root = course_source_dir.resolve()
    embedded = []
    total_bytes = 0
    seen_targets = set()

    for raw_value in data_values:
        source = (raw_value or "").strip().rstrip("\\").strip()
        if not source:
            raise ValueError("Data :: cannot be empty.")

        relative_path = Path(source)
        if relative_path.is_absolute():
            raise ValueError(
                f"Data path must be relative to the course folder: {source}"
            )

        source_path = (course_root / relative_path).resolve()

        try:
            source_path.relative_to(course_root)
        except ValueError as exc:
            raise ValueError(
                f"Data file must remain inside the course folder: {source}"
            ) from exc

        if not source_path.is_file():
            raise FileNotFoundError(f"Data file not found: {source_path}")

        size = source_path.stat().st_size
        if size > PYODIDE_DATA_MAX_FILE_BYTES:
            raise ValueError(
                f"Pyodide data file is too large ({size} bytes): {source}. "
                f"Maximum is {PYODIDE_DATA_MAX_FILE_BYTES} bytes."
            )

        total_bytes += size
        if total_bytes > PYODIDE_DATA_MAX_BLOCK_BYTES:
            raise ValueError(
                "Combined Pyodide data files exceed the per-block limit of "
                f"{PYODIDE_DATA_MAX_BLOCK_BYTES} bytes."
            )

        target_name = source_path.name
        target_path = f"data/{target_name}"

        if target_path in seen_targets:
            raise ValueError(
                f"Multiple Data :: files would use the same Pyodide path: "
                f"{target_path}"
            )
        seen_targets.add(target_path)

        payload = base64.b64encode(source_path.read_bytes()).decode("ascii")

        embedded.append(
            {
                "source": source,
                "target": target_path,
                "base64": payload,
            }
        )

    return embedded
