import re

import click


def parse_tabs(content: str) -> tuple[str, int]:
    """
    Render flexible tab interactions as Quarto panel tabsets.

    Required syntax:

    Tabs

    Tab :: First tab

    Any ordinary Markdown content can appear here.

    END Tab

    Tab :: Second tab

    Additional content can appear here.

    END Tab

    END Tabs

    Each tab can contain paragraphs, lists, links, tables, equations
    and ordinary Markdown produced by Pandoc.

    Interaction metadata blocks should not be nested inside tabs.
    """
    lines = content.split("\n")
    new_lines = []
    count = 0
    i = 0

    while i < len(lines):
        current_text = lines[i].strip()

        # Copy ordinary content until a Tabs block is found.
        if not re.match(
            r"^(?:#+\s*)?Tabs\s*$",
            current_text,
            re.IGNORECASE,
        ):
            new_lines.append(lines[i])
            i += 1
            continue

        count += 1
        i += 1

        tabs = []
        current_tab_title = None
        current_tab_lines = []
        found_tabs_end = False

        while i < len(lines):
            current_line = lines[i]
            current_text = current_line.strip()

            # Close the complete Tabs block.
            if re.match(
                r"^(?:#+\s*)?END Tabs\s*$",
                current_text,
                re.IGNORECASE,
            ):
                if current_tab_title is not None:
                    tabs.append(
                        (
                            current_tab_title,
                            current_tab_lines,
                        )
                    )

                current_tab_title = None
                current_tab_lines = []
                found_tabs_end = True
                i += 1
                break

            # Start a new tab.
            tab_match = re.match(
                r"^(?:#+\s*)?Tab\s*::\s*(.+?)\s*$",
                current_text,
                re.IGNORECASE,
            )

            if tab_match:
                # If the previous tab did not have END Tab, preserve it
                # but issue a warning.
                if current_tab_title is not None:
                    tabs.append(
                        (
                            current_tab_title,
                            current_tab_lines,
                        )
                    )

                    click.echo(
                        click.style(
                            f"Warning: Tab '{current_tab_title}' has no "
                            "END Tab tag; it was closed by the next Tab.",
                            fg="yellow",
                        )
                    )

                current_tab_title = tab_match.group(1).strip()
                current_tab_lines = []
                i += 1
                continue

            # Close the current individual tab.
            if re.match(
                r"^(?:#+\s*)?END Tab\s*$",
                current_text,
                re.IGNORECASE,
            ):
                if current_tab_title is None:
                    click.echo(
                        click.style(
                            "Warning: END Tab found without a matching "
                            "Tab :: opening tag.",
                            fg="yellow",
                        )
                    )
                else:
                    tabs.append(
                        (
                            current_tab_title,
                            current_tab_lines,
                        )
                    )
                    current_tab_title = None
                    current_tab_lines = []

                i += 1
                continue

            # Preserve all ordinary content inside the current tab,
            # including blank lines.
            if current_tab_title is not None:
                current_tab_lines.append(current_line)
            elif current_text:
                click.echo(
                    click.style(
                        "Warning: Content found inside Tabs but outside "
                        "a Tab :: block; the content was ignored.",
                        fg="yellow",
                    )
                )

            i += 1

        # Handle a Tabs block that reaches the end of the document.
        if not found_tabs_end:
            if current_tab_title is not None:
                tabs.append(
                    (
                        current_tab_title,
                        current_tab_lines,
                    )
                )

            click.echo(
                click.style(
                    "Warning: Tabs block has no END Tabs tag; "
                    "content continued to the end of the document.",
                    fg="yellow",
                )
            )

        # Generate the Quarto panel tabset.
        new_lines.append("::: {.panel-tabset}")
        new_lines.append("")

        for tab_title, tab_lines in tabs:
            # Remove unnecessary blank lines around the tab content,
            # while retaining blank lines within it.
            tab_lines = list(tab_lines)

            while tab_lines and not tab_lines[0].strip():
                tab_lines.pop(0)

            while tab_lines and not tab_lines[-1].strip():
                tab_lines.pop()

            new_lines.append(f"## {tab_title}")
            new_lines.append("")

            if tab_lines:
                new_lines.extend(tab_lines)
                new_lines.append("")

        new_lines.append(":::")
        new_lines.append("")

    if count > 0:
        click.echo(
            click.style(
                "Detected tabs interactions",
                fg="blue",
            )
        )
        click.echo(
            f"  Rendering {count} flexible tabset interaction(s)"
        )

    return "\n".join(new_lines), count
