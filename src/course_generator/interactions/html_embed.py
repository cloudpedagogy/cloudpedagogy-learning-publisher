import html
import re
from pathlib import Path

import click

from ..core.assets import rewrite_asset_path
from ..core.parsing import is_markdown_heading, is_interaction_header


def parse_html_embeds(
    content: str,
    qmd_path: Path,
    course_dir: Path,
) -> tuple[str, int]:
    """Render trusted, local, standalone HTML activities in accessible iframes."""
    lines = content.split("\n")
    new_lines = []
    count = 0
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()
        match = re.match(
            r"^(?:#+\s*)?HTML Embed\s*::\s*(.+)$",
            stripped,
            re.IGNORECASE,
        )

        if not match:
            new_lines.append(lines[i])
            i += 1
            continue

        raw_path = match.group(1).strip().replace("\\", "/")
        path_object = Path(raw_path)
        if (
            not raw_path.startswith("resources/html/")
            or path_object.suffix.lower() not in {".html", ".htm"}
            or ".." in path_object.parts
            or path_object.is_absolute()
        ):
            raise ValueError(
                "HTML Embed must reference a trusted local file under "
                f"resources/html/: {raw_path}"
            )
        source_file = course_dir / raw_path
        if not source_file.is_file():
            raise FileNotFoundError(f"HTML Embed source not found: {source_file}")

        title = path_object.stem.replace("_", " ").replace("-", " ").strip()
        height = 700
        fallback_image = ""
        found_end = False
        i += 1

        while i < len(lines):
            current_line = lines[i]
            current_text = current_line.strip()

            if re.match(
                r"^(?:#+\s*)?END HTML Embed\s*$",
                current_text,
                re.IGNORECASE,
            ):
                found_end = True
                i += 1
                break

            if is_markdown_heading(current_line) or is_interaction_header(current_line):
                break

            title_match = re.match(
                r"^Title\s*::\s*(.*)$",
                current_text,
                re.IGNORECASE,
            )
            height_match = re.match(
                r"^Height\s*::\s*(.*)$",
                current_text,
                re.IGNORECASE,
            )
            fallback_match = re.match(
                r"^Fallback Image\s*::\s*(.*)$",
                current_text,
                re.IGNORECASE,
            )

            if title_match and title_match.group(1).strip():
                title = title_match.group(1).strip()
            elif height_match:
                height_value = height_match.group(1).strip()
                if height_value.isdigit() and 300 <= int(height_value) <= 2000:
                    height = int(height_value)
            elif fallback_match:
                fallback_image = fallback_match.group(1).strip().replace("\\", "/")

            i += 1

        if not found_end:
            click.echo(
                click.style(
                    "Warning: HTML Embed block has no END HTML Embed tag.",
                    fg="yellow",
                )
            )

        path = rewrite_asset_path(raw_path, qmd_path, course_dir)
        safe_path = html.escape(path, quote=True)
        safe_title = html.escape(title, quote=True)
        link_label = title.replace("[", "\\[").replace("]", "\\]")

        new_lines.append('::: {.content-visible when-format="html"}')
        new_lines.append("")
        new_lines.append(
            f'<iframe class="html-embed" src="{safe_path}" '
            f'title="{safe_title}" width="100%" height="{height}" '
            f'style="border: 0;" '
            f'loading="lazy" sandbox="allow-scripts allow-downloads" '
            f'referrerpolicy="no-referrer"></iframe>'
        )
        new_lines.append("")
        new_lines.append(
            f'[{link_label} — open in a new window]({path})'
            '{target="_blank" rel="noopener"}'
        )
        new_lines.append("")
        new_lines.append(":::")
        new_lines.append("")

        new_lines.append('::: {.content-visible unless-format="html"}')
        new_lines.append("")
        if fallback_image:
            fallback_object = Path(fallback_image)
            if (
                not fallback_image.startswith("resources/images/")
                or fallback_object.suffix.lower()
                not in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
                or ".." in fallback_object.parts
                or fallback_object.is_absolute()
            ):
                raise ValueError(
                    "Fallback Image must reference a local image under "
                    f"resources/images/: {fallback_image}"
                )
            fallback_source = course_dir / fallback_image
            if not fallback_source.is_file():
                raise FileNotFoundError(
                    f"HTML Embed fallback image not found: {fallback_source}"
                )
            fallback_path = rewrite_asset_path(fallback_image, qmd_path, course_dir)
            new_lines.append(f"![{link_label}]({fallback_path})")
            new_lines.append("")
        new_lines.append(f"[{link_label} — open the interactive version]({path})")
        new_lines.append("")
        new_lines.append(":::")
        new_lines.append("")
        count += 1

    if count > 0:
        click.echo(click.style("Detected HTML embeds", fg="blue"))
        click.echo(f"  Rendering {count} standalone HTML interaction(s)")

    return "\n".join(new_lines), count
