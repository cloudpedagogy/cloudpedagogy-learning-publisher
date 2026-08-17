import html
import re

import click


def parse_callouts(content: str) -> tuple[str, int]:
    """
    Render Callout blocks containing rich Markdown content.

    Syntax:

    Callout :: important
    Title :: Optional title

    Paragraphs, lists, tables, equations, links and ordinary Markdown.

    END Callout

    Text :: remains accepted for concise, single-paragraph content.
    END Callout is required so headings and other ordinary Markdown can safely
    appear inside the callout.
    """
    lines = content.split("\n")
    new_lines = []
    count = 0
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()
        match = re.match(r"^(?:#+\s*)?Callout\s*::\s*(.+)$", stripped, re.IGNORECASE)

        if not match:
            new_lines.append(lines[i])
            i += 1
            continue

        callout_type = match.group(1).strip().lower()
        allowed_types = {"note", "tip", "warning", "caution", "important"}
        if callout_type not in allowed_types:
            click.echo(
                click.style(
                    f"Warning: Unknown Callout type '{callout_type}'; using 'note'.",
                    fg="yellow",
                )
            )
            callout_type = "note"

        title = ""
        content_lines = []
        i += 1
        found_end = False

        while i < len(lines):
            current_line = lines[i]
            s = current_line.strip()

            if re.match(r"^(?:#+\s*)?END Callout\s*$", s, re.IGNORECASE):
                found_end = True
                i += 1
                break

            title_match = re.match(r"^Title\s*::\s*(.*)$", s, re.IGNORECASE)
            text_match = re.match(r"^Text\s*::\s*(.*)$", s, re.IGNORECASE)

            if title_match:
                title = title_match.group(1).strip()
            elif text_match:
                content_lines.append(text_match.group(1).strip())
            else:
                content_lines.append(current_line)

            i += 1

        while content_lines and not content_lines[0].strip():
            content_lines.pop(0)
        while content_lines and not content_lines[-1].strip():
            content_lines.pop()

        attributes = f".callout-{callout_type}"
        if title:
            attributes += f' title="{html.escape(title, quote=True)}"'

        new_lines.append(f"::: {{{attributes}}}")
        if content_lines:
            new_lines.extend(content_lines)
        new_lines.append(":::")
        new_lines.append("")
        count += 1

        if not found_end:
            click.echo(
                click.style(
                    "Warning: Callout block has no END Callout tag; "
                    "content continued to the end of the document.",
                    fg="yellow",
                )
            )

    if count > 0:
        click.echo(click.style("Detected callouts", fg="blue"))
        click.echo(f"  Rendering {count} callout blocks")

    return "\n".join(new_lines), count
