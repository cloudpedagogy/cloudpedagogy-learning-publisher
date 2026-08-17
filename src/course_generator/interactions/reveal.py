import html
import re

import click


def parse_reveal(content: str) -> tuple[str, int]:
    """
    Render generic Reveal blocks as collapsible content.

    Syntax:

    Reveal
    Label :: Show more

    Any ordinary Markdown content can appear here.

    END Reveal

    The content may contain paragraphs, lists, links, tables, equations
    and Markdown produced from normal Word formatting.

    Metadata interaction blocks should not be nested inside Reveal.
    """
    lines = content.split("\n")
    new_lines = []
    count = 0
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()

        if not re.match(
            r"^(?:#+\s*)?Reveal\s*$",
            stripped,
            re.IGNORECASE,
        ):
            new_lines.append(lines[i])
            i += 1
            continue

        label = "Show more"
        reveal_lines = []
        i += 1
        found_end = False

        while i < len(lines):
            current_line = lines[i]
            current_text = current_line.strip()

            if re.match(
                r"^(?:#+\s*)?END Reveal\s*$",
                current_text,
                re.IGNORECASE,
            ):
                found_end = True
                i += 1
                break

            label_match = re.match(
                r"^Label\s*::\s*(.*)$",
                current_text,
                re.IGNORECASE,
            )

            if label_match:
                label_value = label_match.group(1).strip()
                if label_value:
                    label = label_value
            else:
                reveal_lines.append(current_line)

            i += 1

        # Remove unnecessary blank lines around the contained content.
        while reveal_lines and not reveal_lines[0].strip():
            reveal_lines.pop(0)

        while reveal_lines and not reveal_lines[-1].strip():
            reveal_lines.pop()

        new_lines.append("<details>")
        new_lines.append(
            f"<summary><strong>{html.escape(label)}</strong></summary>"
        )
        new_lines.append("")

        if reveal_lines:
            new_lines.extend(reveal_lines)
            new_lines.append("")

        new_lines.append("</details>")
        new_lines.append("")
        count += 1

        if not found_end:
            click.echo(
                click.style(
                    "Warning: Reveal block has no END Reveal tag; "
                    "content continued to the end of the document.",
                    fg="yellow",
                )
            )

    if count > 0:
        click.echo(
            click.style(
                "Detected reveal blocks",
                fg="blue",
            )
        )
        click.echo(
            f"  Rendering {count} generic reveal interactions"
        )

    return "\n".join(new_lines), count
