from pathlib import Path


def resolve_r_code_source(source: str, course_source_dir: Path) -> str:
    """Read a safe, course-relative external R source file."""
    source = source.strip().rstrip("\\").strip()
    if not source:
        raise ValueError("Source :: in an R Code block cannot be empty.")

    relative_source = Path(source)
    if relative_source.is_absolute():
        raise ValueError(f"R source must be relative to the course folder: {source}")
    if relative_source.suffix.lower() != ".r":
        raise ValueError(f"R source must be an .R file: {source}")

    course_root = course_source_dir.resolve()
    source_path = (course_root / relative_source).resolve()
    try:
        source_path.relative_to(course_root)
    except ValueError as exc:
        raise ValueError(f"R source must remain inside the course folder: {source}") from exc

    if not source_path.is_file():
        raise FileNotFoundError(f"R source file not found: {source_path}")
    return source_path.read_text(encoding="utf-8")
