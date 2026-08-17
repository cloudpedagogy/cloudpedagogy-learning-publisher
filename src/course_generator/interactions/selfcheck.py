import re

import click


def parse_selfcheck(content: str) -> tuple[str, int]:
    """
    Render SelfCheck blocks as questions with hidden suggested answers.

    Preferred syntax:

    SelfCheck
    Question :: Why might effectiveness differ?
    Answer :: Differences in exposure...

    Additional answer paragraphs, lists and equations can follow.

    END SelfCheck

    END SelfCheck is required so rich answer content can safely contain
    headings and other ordinary Markdown.
    """
    lines = content.split("\n")
    new_lines = []
    count = 0
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()

        if not re.match(
            r"^(?:#+\s*)?SelfCheck\s*$",
            stripped,
            re.IGNORECASE,
        ):
            new_lines.append(lines[i])
            i += 1
            continue

        question = ""
        answer_lines = []
        answer_started = False
        i += 1
        found_end = False

        while i < len(lines):
            current_line = lines[i]
            current_text = current_line.strip()

            # Preferred explicit ending
            if re.match(
                r"^(?:#+\s*)?END SelfCheck\s*$",
                current_text,
                re.IGNORECASE,
            ):
                found_end = True
                i += 1
                break

            question_match = re.match(
                r"^Question\s*::\s*(.*)$",
                current_text,
                re.IGNORECASE,
            )
            answer_match = re.match(
                r"^Answer\s*::\s*(.*)$",
                current_text,
                re.IGNORECASE,
            )

            if question_match:
                question = question_match.group(1).strip()
            elif answer_match:
                answer_started = True
                answer_lines.append(answer_match.group(1).strip())
            elif answer_started:
                # Preserve ordinary content and blank lines so answers can
                # contain multiple paragraphs, lists, tables and equations.
                answer_lines.append(current_line)

            i += 1

        # Remove unnecessary blank lines around the answer while preserving
        # blank lines within it.
        while answer_lines and not answer_lines[0].strip():
            answer_lines.pop(0)

        while answer_lines and not answer_lines[-1].strip():
            answer_lines.pop()

        new_lines.append(
            '::: {.callout-tip title="Self-check"}'
        )

        if question:
            new_lines.append(question)
            new_lines.append("")

        if answer_lines:
            new_lines.append("<details>")
            new_lines.append(
                "<summary><strong>Show suggested answer</strong></summary>"
            )
            new_lines.append("")
            new_lines.extend(answer_lines)
            new_lines.append("")
            new_lines.append("</details>")

        new_lines.append(":::")
        new_lines.append("")
        count += 1

        if not found_end:
            click.echo(
                click.style(
                    "Warning: SelfCheck block has no END SelfCheck tag; "
                    "content continued to the end of the document.",
                    fg="yellow",
                )
            )

    if count > 0:
        click.echo(
            click.style(
                "Detected self-check blocks",
                fg="blue",
            )
        )
        click.echo(
            f"  Rendering {count} self-check interactions "
            "with hidden answers"
        )

    return "\n".join(new_lines), count
