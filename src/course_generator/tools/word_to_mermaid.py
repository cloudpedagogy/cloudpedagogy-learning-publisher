#!/usr/bin/env python3
"""
Word → Mermaid.js converter

Purpose:
    Convert a structured Word document into Mermaid diagram files and optional
    runnable Mermaid HTML pages.

Expected Word structure:
    Heading 1 = document / diagram collection title
    Heading 2 = individual diagram title
    Body text under each Heading 2 = Mermaid code

Example Word body under Heading 2:
    flowchart TD
    A[Start] --> B{Decision?}
    B -->|Yes| C[Continue]
    B -->|No| D[Revise]

Single file:
    python src/course_generator/tools/word_to_mermaid.py \
      --input imports/mermaid/literature_review_mermaid_branching_demo.docx \
      --output-dir output/mermaid \
      --html

Glob mode:
    python src/course_generator/tools/word_to_mermaid.py \
      --input-glob "imports/mermaid/**/*.docx" \
      --output-dir output/mermaid \
      --html
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

try:
    import mammoth
except ImportError:
    print(
        "Missing dependency: mammoth\n\n"
        "Install it with:\n"
        "  pip install mammoth\n",
        file=sys.stderr,
    )
    raise


HEADING_RE = re.compile(r"<h([1-6])>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)
BLOCK_RE = re.compile(r"(<h[1-6]>.*?</h[1-6]>)", re.IGNORECASE | re.DOTALL)


def clean_text(value: str) -> str:
    value = value.replace("&amp;", "&")
    value = value.replace("&lt;", "<")
    value = value.replace("&gt;", ">")
    value = value.replace("&quot;", '"')
    value = value.replace("&#x27;", "'")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def strip_html(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"</p\s*>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<p\s*>", "", value, flags=re.IGNORECASE)
    value = re.sub(r"</li\s*>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<li\s*>", "", value, flags=re.IGNORECASE)
    value = re.sub(r"</?(ul|ol)\s*>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r'<a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>', lambda m: m.group(1), value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r"<[^>]+>", "", value)
    return clean_text(value)


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = value.strip("_")
    return value or "diagram"


def convert_docx_to_html(docx_path: Path) -> str:
    with docx_path.open("rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)

    if result.messages:
        print(f"\nMammoth messages for {docx_path}:")
        for message in result.messages:
            print(f"  - {message}")

    return result.value


def split_html_by_headings(html_text: str) -> list[tuple[int, str, str]]:
    parts = BLOCK_RE.split(html_text)
    sections: list[tuple[int, str, str]] = []

    current_level: int | None = None
    current_title: str | None = None
    current_body: list[str] = []

    for part in parts:
        if not part.strip():
            continue

        heading_match = HEADING_RE.match(part.strip())
        if heading_match:
            if current_level is not None and current_title is not None:
                sections.append((current_level, current_title, "\n".join(current_body)))

            current_level = int(heading_match.group(1))
            current_title = strip_html(heading_match.group(2))
            current_body = []
        else:
            if current_level is not None:
                current_body.append(part)

    if current_level is not None and current_title is not None:
        sections.append((current_level, current_title, "\n".join(current_body)))

    return sections


def extract_mermaid_diagrams(docx_path: Path) -> tuple[str, list[tuple[str, str]]]:
    html_text = convert_docx_to_html(docx_path)
    sections = split_html_by_headings(html_text)

    if not sections:
        raise ValueError(
            f"No headings found in {docx_path}. Use Heading 1 for the title and Heading 2 for diagrams."
        )

    collection_title = docx_path.stem.replace("_", " ").replace("-", " ").title()
    diagrams: list[tuple[str, str]] = []

    current_title: str | None = None
    current_body: list[str] = []

    for level, title, body_html in sections:
        body_text = strip_html(body_html)

        if level == 1:
            collection_title = title or collection_title
            continue

        if level == 2:
            if current_title and current_body:
                diagrams.append((current_title, clean_text("\n".join(current_body))))

            current_title = title
            current_body = []
            if body_text:
                current_body.append(body_text)
            continue

        if current_title:
            if body_text:
                current_body.append(body_text)

    if current_title and current_body:
        diagrams.append((current_title, clean_text("\n".join(current_body))))

    if not diagrams:
        raise ValueError(
            f"No Heading 2 diagram sections found in {docx_path}. Use Heading 2 for each Mermaid diagram."
        )

    return collection_title, diagrams


def ensure_mermaid_header(code: str) -> str:
    stripped = code.strip()
    first_line = stripped.splitlines()[0].strip() if stripped else ""
    mermaid_starts = (
        "flowchart", "graph", "sequenceDiagram", "classDiagram", "stateDiagram",
        "stateDiagram-v2", "erDiagram", "journey", "gantt", "pie", "mindmap",
        "timeline", "quadrantChart", "requirementDiagram", "gitGraph"
    )
    if first_line.startswith(mermaid_starts):
        return stripped
    return "flowchart TD\n" + stripped


def html_page(title: str, diagrams: list[tuple[str, str]]) -> str:
    diagram_blocks = []
    for diagram_title, code in diagrams:
        diagram_blocks.append(
            f"<section>\n"
            f"  <h2>{html.escape(diagram_title)}</h2>\n"
            f"  <pre class=\"mermaid\">\n{html.escape(ensure_mermaid_header(code))}\n  </pre>\n"
            f"</section>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      margin: 2rem;
      line-height: 1.5;
      background: #ffffff;
      color: #222222;
    }}
    main {{
      max-width: 1100px;
      margin: 0 auto;
    }}
    section {{
      margin: 2rem 0;
      padding: 1rem;
      border: 1px solid #dddddd;
      border-radius: 8px;
    }}
    .mermaid {{
      text-align: center;
    }}
  </style>
</head>
<body>
<main>
  <h1>{html.escape(title)}</h1>
  {''.join(diagram_blocks)}
</main>
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
  mermaid.initialize({{ startOnLoad: true }});
</script>
</body>
</html>
"""


def convert_one(input_path: Path, output_dir: Path, make_html: bool = False, overwrite: bool = True) -> None:
    title, diagrams = extract_mermaid_diagrams(input_path)

    target_dir = output_dir / input_path.stem
    target_dir.mkdir(parents=True, exist_ok=True)

    for diagram_title, code in diagrams:
        output_path = target_dir / f"{slugify(diagram_title)}.mmd"
        if output_path.exists() and not overwrite:
            raise FileExistsError(f"Output already exists: {output_path}")
        output_path.write_text(ensure_mermaid_header(code) + "\n", encoding="utf-8")
        print(f"Created: {output_path}")

    if make_html:
        html_path = target_dir / "index.html"
        if html_path.exists() and not overwrite:
            raise FileExistsError(f"Output already exists: {html_path}")
        html_path.write_text(html_page(title, diagrams), encoding="utf-8")
        print(f"Created: {html_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert Word .docx files into Mermaid .mmd and HTML files.")

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--input", type=Path, help="Path to a single .docx file.")
    mode.add_argument("--input-glob", help='Glob pattern, e.g. "imports/mermaid/**/*.docx".')

    parser.add_argument("--output-dir", type=Path, default=Path("output/mermaid"), help="Output directory. Default: output/mermaid")
    parser.add_argument("--html", action="store_true", help="Also create a runnable Mermaid.js index.html page.")
    parser.add_argument("--no-overwrite", action="store_true", help="Do not overwrite existing files.")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    overwrite = not args.no_overwrite

    if args.input:
        if not args.input.exists():
            raise FileNotFoundError(f"Input file not found: {args.input}")
        if args.input.suffix.lower() != ".docx":
            raise ValueError(f"Input must be a .docx file: {args.input}")
        convert_one(args.input, args.output_dir, make_html=args.html, overwrite=overwrite)
        return

    input_paths = sorted(Path().glob(args.input_glob))
    if not input_paths:
        raise FileNotFoundError(f"No files matched: {args.input_glob}")

    for input_path in input_paths:
        if input_path.suffix.lower() == ".docx":
            convert_one(input_path, args.output_dir, make_html=args.html, overwrite=overwrite)


if __name__ == "__main__":
    main()
