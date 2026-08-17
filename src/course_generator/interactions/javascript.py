import html
import re
from pathlib import Path

import click


def resolve_javascript_source(source: str, course_source_dir: Path) -> str:
    """Read a safe, course-relative plain JavaScript source file."""
    source = source.strip().rstrip("\\").strip()
    if not source:
        raise ValueError(
            "Source :: in a JavaScript Interaction block cannot be empty."
        )

    relative_source = Path(source)
    if relative_source.is_absolute():
        raise ValueError(
            f"JavaScript source must be relative to the course folder: {source}"
        )
    if relative_source.suffix.lower() != ".js":
        raise ValueError(f"JavaScript source must be a .js file: {source}")

    course_root = course_source_dir.resolve()
    source_path = (course_root / relative_source).resolve()
    try:
        source_path.relative_to(course_root)
    except ValueError as exc:
        raise ValueError(
            f"JavaScript source must remain inside the course folder: {source}"
        ) from exc

    if not source_path.is_file():
        raise FileNotFoundError(f"JavaScript source file not found: {source_path}")

    script = source_path.read_text(encoding="utf-8")
    if re.search(r"</script\s*>", script, re.IGNORECASE):
        raise ValueError(
            f"JavaScript source cannot contain a closing </script> tag: {source}"
        )
    return script

def parse_javascript_interactions(
    content: str,
    course_source_dir: Path | None = None,
) -> tuple[str, int]:
    """Inline course-local plain JavaScript interactions into the generated page.

    Syntax:

    JavaScript Interaction
    Source :: code/example.js
    Container ID :: example-interaction
    Interaction :: example
    Alt :: Accessible description
    Caption :: Optional visible caption
    END JavaScript Interaction

    This component intentionally emits ordinary inline JavaScript rather than
    an iframe, a module, or a runtime server dependency.
    """
    lines = content.split("\n")
    new_lines = []
    count = 0
    in_block = False
    metadata = {}

    def flush_block():
        nonlocal metadata
        if course_source_dir is None:
            raise ValueError(
                "A JavaScript Interaction requires the course configuration directory."
            )

        source = metadata.get("source", "")
        container_id = metadata.get("container id", "")
        interaction = metadata.get("interaction", "")
        alt_text = metadata.get("alt", "")
        caption = metadata.get("caption", "")

        if not source:
            raise ValueError("JavaScript Interaction requires Source ::.")
        if not container_id:
            raise ValueError("JavaScript Interaction requires Container ID ::.")
        if not interaction:
            raise ValueError("JavaScript Interaction requires Interaction ::.")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]*", container_id):
            raise ValueError(
                "Container ID must begin with a letter and contain only letters, "
                f"numbers, '.', '_', ':', or '-': {container_id}"
            )
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", interaction):
            raise ValueError(
                "Interaction must contain only letters, numbers, '_' or '-': "
                f"{interaction}"
            )

        script = resolve_javascript_source(source, course_source_dir)
        accessible_label = alt_text or caption or "Interactive learning activity"
        escaped_id = html.escape(container_id, quote=True)
        escaped_interaction = html.escape(interaction, quote=True)
        escaped_label = html.escape(accessible_label, quote=True)

        new_lines.extend(
            [
                '<figure class="javascript-interaction-figure">',
                (
                    f'<div id="{escaped_id}" class="javascript-interaction" '
                    f'data-js-interaction="{escaped_interaction}" role="group" '
                    f'aria-label="{escaped_label}"></div>'
                ),
            ]
        )
        if caption:
            new_lines.append(
                '<figcaption class="javascript-interaction-caption">'
                f"{html.escape(caption)}"
                "</figcaption>"
            )
        new_lines.extend(["</figure>", "<script>", script.rstrip(), "</script>"])
        metadata = {}

    for line in lines:
        stripped = line.strip()
        if not in_block:
            if re.match(
                r"^(?:#+\s*)?JavaScript Interaction\s*$",
                stripped,
                re.IGNORECASE,
            ):
                in_block = True
                metadata = {}
                count += 1
            else:
                new_lines.append(line)
            continue

        if re.match(
            r"^(?:#+\s*)?END JavaScript Interaction\s*$",
            stripped,
            re.IGNORECASE,
        ):
            flush_block()
            in_block = False
            continue

        metadata_match = re.match(
            r"^(Source|Container ID|Interaction|Alt|Caption)\s*::\s*(.*)$",
            stripped,
            re.IGNORECASE,
        )
        if metadata_match:
            key = metadata_match.group(1).lower()
            if key in metadata:
                raise ValueError(
                    f"JavaScript Interaction contains duplicate {metadata_match.group(1)} ::."
                )
            metadata[key] = metadata_match.group(2).strip().rstrip("\\").strip()
        elif stripped:
            raise ValueError(
                "Unexpected content in JavaScript Interaction block: "
                f"{stripped}"
            )

    if in_block:
        raise ValueError(
            "JavaScript Interaction block has no explicit "
            "END JavaScript Interaction tag."
        )

    if count > 0:
        click.echo(click.style("Detected JavaScript interactions", fg="blue"))
        click.echo(f"  Inlining {count} plain JavaScript interaction(s)")

    return "\n".join(new_lines), count
