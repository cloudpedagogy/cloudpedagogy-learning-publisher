import re
from pathlib import Path

import click

from ..core.assets import rewrite_asset_path
from ..core.parsing import is_markdown_heading, is_interaction_header


def parse_images(content: str, qmd_path: Path, course_dir: Path) -> tuple[str, int]:
    """Render Image blocks, preferring END Image and retaining legacy implicit endings."""
    lines = content.split("\n")
    new_lines = []
    count = 0
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()
        match = re.match(r"^(?:#+\s*)?Image\s*::\s*(.+)$", stripped, re.IGNORECASE)

        if not match:
            new_lines.append(lines[i])
            i += 1
            continue

        raw_path = match.group(1).strip()
        path = rewrite_asset_path(raw_path, qmd_path, course_dir)
        alt = ""
        caption = ""
        width = ""
        i += 1

        while i < len(lines):
            s = lines[i].strip()
            if re.match(r"^(?:#+\s*)?END Image\s*$", s, re.IGNORECASE):
                i += 1
                break
            if is_markdown_heading(lines[i]) or is_interaction_header(lines[i]):
                break

            alt_match = re.match(r"^Alt\s*::\s*(.*)$", s, re.IGNORECASE)
            cap_match = re.match(r"^Caption\s*::\s*(.*)$", s, re.IGNORECASE)
            width_match = re.match(r"^Width\s*::\s*(.*)$", s, re.IGNORECASE)

            if alt_match:
                alt = alt_match.group(1).strip()
            elif cap_match:
                caption = cap_match.group(1).strip()
            elif width_match:
                width = width_match.group(1).strip()

            i += 1

        visible_caption = caption or ""
        image_line = f"![{visible_caption}]({path})"

        attributes = []
        if width:
            attributes.append(f"width='{width}'")
        if alt:
            attributes.append(f'fig-alt="{alt}"')

        if attributes:
            image_line += "{" + " ".join(attributes) + "}"

        new_lines.append(image_line)
        new_lines.append("")
        count += 1

    if count > 0:
        click.echo(click.style("Detected image blocks", fg="blue"))
        click.echo(f"  Rendering {count} images")

    return "\n".join(new_lines), count
