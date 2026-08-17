import re
from pathlib import Path

import click

from .router import resolve_engine
from .pyodide.renderer import render_pyodide_widget
from .pyodide.data import resolve_pyodide_data_files
from .python.cleaning import clean_python_code


def resolve_python_source(source: str, course_source_dir: Path) -> str:
    """Read a safe, course-relative external Python source file."""
    source = source.strip().rstrip("\\").strip()
    if not source:
        raise ValueError("Source :: in a Python Code block cannot be empty.")

    relative_source = Path(source)
    if relative_source.is_absolute():
        raise ValueError(
            f"Python source must be relative to the course folder: {source}"
        )
    if relative_source.suffix.lower() != ".py":
        raise ValueError(f"Python source must be a .py file: {source}")

    course_root = course_source_dir.resolve()
    source_path = (course_root / relative_source).resolve()

    try:
        source_path.relative_to(course_root)
    except ValueError as exc:
        raise ValueError(
            f"Python source must remain inside the course folder: {source}"
        ) from exc

    if not source_path.is_file():
        raise FileNotFoundError(f"Python source file not found: {source_path}")

    return source_path.read_text(encoding="utf-8")


def parse_generic_code_blocks(
    content: str,
    course_source_dir: Path | None = None,
) -> tuple[str, int]:
    """
    Parse generic Learning Publisher Code blocks.

    Supported Stage 4B syntax:

        Code
        Language :: python
        Mode :: static

        print("Hello")

        END Code

    External source:

        Code
        Language :: python
        Mode :: static
        Source :: code/example.py
        END Code

    Pyodide mode renders an editable browser-side Python exercise and supports course-local Data :: files.
    """
    lines = content.split("\n")
    new_lines = []
    count = 0
    pyodide_index = 0
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()

        if not re.match(r"^(?:#+\s*)?Code\s*$", stripped, re.IGNORECASE):
            new_lines.append(lines[i])
            i += 1
            continue

        count += 1
        language = ""
        mode = "static"
        source = ""
        data_values = []
        code_lines = []
        i += 1
        found_end = False

        while i < len(lines):
            current_line = lines[i]
            current_text = current_line.strip()

            if re.match(
                r"^(?:#+\s*)?END Code\s*$",
                current_text,
                re.IGNORECASE,
            ):
                found_end = True
                i += 1
                break

            language_match = re.match(
                r"^Language\s*::\s*(.*)$",
                current_text,
                re.IGNORECASE,
            )
            mode_match = re.match(
                r"^Mode\s*::\s*(.*)$",
                current_text,
                re.IGNORECASE,
            )
            source_match = re.match(
                r"^Source\s*::\s*(.*)$",
                current_text,
                re.IGNORECASE,
            )
            data_match = re.match(
                r"^Data\s*::\s*(.*)$",
                current_text,
                re.IGNORECASE,
            )

            if language_match:
                language = language_match.group(1).strip()
            elif mode_match:
                mode = mode_match.group(1).strip()
            elif source_match:
                source = source_match.group(1).strip()
            elif data_match:
                data_values.append(data_match.group(1).strip())
            else:
                code_lines.append(current_line)

            i += 1

        if not found_end:
            raise ValueError(
                "Code block has no explicit END Code tag."
            )

        if not language:
            raise ValueError("Code block requires Language ::.")

        engine = resolve_engine(language, mode)

        inline_code = "\n".join(code_lines).strip()

        if source:
            if inline_code:
                raise ValueError(
                    "Code block cannot contain both Source :: and inline code."
                )
            if course_source_dir is None:
                raise ValueError(
                    "Code Source :: requires the course configuration directory."
                )

            if language.strip().lower() == "python":
                code = resolve_python_source(source, course_source_dir).strip()
            else:
                raise ValueError(
                    "Generic external Source :: is not yet enabled for "
                    f"Language :: {language}."
                )
        else:
            code = inline_code

        if not code:
            raise ValueError(
                "Code block requires either Source :: or inline code."
            )

        normalized_language = language.strip().lower()

        if normalized_language == "python":
            code = clean_python_code(code)

        embedded_data = []
        if data_values:
            if normalized_language != "python":
                raise ValueError(
                    "Data :: is currently supported only for Python Code blocks."
                )
            if course_source_dir is None:
                raise ValueError(
                    "Data :: requires the course configuration directory."
                )
            embedded_data = resolve_pyodide_data_files(
                data_values,
                course_source_dir,
            )

        if engine == "python":
            new_lines.append("```python")
            new_lines.append(code)
            new_lines.append("```")
            new_lines.append("")

        elif engine == "pyodide":
            pyodide_index += 1
            widget_id = f"learning-publisher-pyodide-{pyodide_index}"
            new_lines.append(
                render_pyodide_widget(
                    code,
                    widget_id=widget_id,
                    data_files=embedded_data,
                )
            )
            new_lines.append("")

        elif normalized_language == "r":
            raise ValueError(
                "Generic R Code blocks are reserved for a later compatibility "
                "stage. Continue using the existing R Code / END R Code syntax."
            )

        else:
            raise ValueError(
                f"Unsupported generic code engine: {engine}"
            )

    if count > 0:
        click.echo(click.style("Detected generic code blocks", fg="blue"))
        click.echo(f"  Rendering {count} generic code block(s)")

    return "\n".join(new_lines), count
