import re
from pathlib import Path

import click

from ..core.assets import rewrite_asset_path
from ..core.parsing import is_markdown_heading, is_interaction_header


def parse_files(content: str, qmd_path: Path, course_dir: Path) -> tuple[str, int]:
    """Render File blocks, preferring END File and retaining legacy implicit endings."""
    lines = content.split("\n")
    new_lines = []
    count = 0
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()
        match = re.match(r"^(?:#+\s*)?File\s*::\s*(.+)$", stripped, re.IGNORECASE)

        if not match:
            new_lines.append(lines[i])
            i += 1
            continue

        raw_path = match.group(1).strip()
        path = rewrite_asset_path(raw_path, qmd_path, course_dir)
        label = "Download file"
        display = ""
        i += 1

        while i < len(lines):
            s = lines[i].strip()
            if re.match(r"^(?:#+\s*)?END File\s*$", s, re.IGNORECASE):
                i += 1
                break
            if is_markdown_heading(lines[i]) or is_interaction_header(lines[i]):
                break

            label_match = re.match(r"^Label\s*::\s*(.*)$", s, re.IGNORECASE)
            display_match = re.match(r"^Display\s*::\s*(.*)$", s, re.IGNORECASE)

            if label_match:
                label = label_match.group(1).strip()
            elif display_match:
                display = display_match.group(1).strip().lower()

            i += 1

        if display == "embed" and path.lower().endswith(".pdf"):
            iframe_title = f"Embedded PDF: {label}" if label else "Embedded PDF document"
            new_lines.append(
                f'<iframe src="{path}" title="{iframe_title}" width="100%" height="600" loading="lazy"></iframe>'
            )
            new_lines.append("")
            new_lines.append(f"[{label}]({path})")
            new_lines.append("")
        else:
            new_lines.append(f"[{label}]({path})")
            new_lines.append("")

        count += 1

    if count > 0:
        click.echo(click.style("Detected file links", fg="blue"))
        click.echo(f"  Rendering {count} file links")

    return "\n".join(new_lines), count
