#!/usr/bin/env python3
"""
word_to_revealjs.py

Focused DOCX -> Quarto Reveal.js converter.

Recommended placement:
    src/course_generator/tools/word_to_revealjs.py

Recommended source folder:
    imports/presentations/

Recommended output folder:
    output/presentations/

Install:
    python -m pip install mammoth beautifulsoup4

Run from the Quarto publishing project root:
    python src/course_generator/tools/word_to_revealjs.py \
      --input-glob "imports/presentations/**/*.docx" \
      --output-dir "output/presentations" \
      --render

Word authoring rules:
    Heading 1 = presentation title
    Heading 2 = slide title
    bullets/paragraphs/images = slide content
    images should be "In Line with Text"

Supported metatags in Word:
    [YOUTUBE]
    https://youtu.be/VIDEO_ID

    [YOUTUBE] https://www.youtube.com/watch?v=VIDEO_ID

    YouTubeEmbed :: https://www.youtube.com/watch?v=VIDEO_ID

    PanoptoEmbed :: https://lshtm.cloud.panopto.eu/Panopto/Pages/Viewer.aspx?id=SESSION_ID

    [IFRAME]
    https://example.com/embed

    IFrameEmbed :: https://example.com/embed
"""

from __future__ import annotations

import argparse
import html
import mimetypes
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional
from urllib.parse import parse_qs, urlparse

import mammoth
from bs4 import BeautifulSoup, Tag


@dataclass
class Section:
    title: str
    elements: List[str] = field(default_factory=list)


@dataclass
class ImageRecord:
    filename: str
    src: str
    alt: str = ""
    content_type: str = ""


@dataclass
class SourceDoc:
    source_path: Path
    source_name: str
    source_stem: str
    title: str
    safe_title: str
    output_folder: str
    media_subdir: str
    media_files: List[Path]
    sections: List[Section]
    detected_headings: List[str] = field(default_factory=list)
    image_records: List[ImageRecord] = field(default_factory=list)
    messages: List[str] = field(default_factory=list)
    qa_findings: List[str] = field(default_factory=list)


def normalise_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).strip()


def safe_filename(text: str) -> str:
    text = text.strip()
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)
    return text.strip("_") or "untitled"


def extension_from_content_type(content_type: str) -> str:
    ext = mimetypes.guess_extension(content_type or "")
    if ext == ".jpe":
        ext = ".jpg"
    return ext or ".png"


def element_text(el: Tag) -> str:
    return normalise_text(el.get_text(" ", strip=True))


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def get_image_alt_text_from_mammoth_image(image: Any) -> str:
    for attr in ("alt_text", "alt", "description", "title"):
        value = getattr(image, attr, None)
        if isinstance(value, str) and value.strip():
            return normalise_text(value)
    for attr in ("metadata", "_metadata"):
        metadata = getattr(image, attr, None)
        if isinstance(metadata, dict):
            for key in ("alt_text", "alt", "description", "title"):
                value = metadata.get(key)
                if isinstance(value, str) and value.strip():
                    return normalise_text(value)
    return ""


def make_image_converter(media_dir: Path, media_subdir: str, saved_files: List[Path], image_records: List[ImageRecord]):
    media_dir.mkdir(parents=True, exist_ok=True)
    counter = {"count": 0}

    def convert_image(image):
        counter["count"] += 1
        content_type = getattr(image, "content_type", "") or ""
        ext = extension_from_content_type(content_type)
        filename = f"image_{counter['count']:03d}{ext}"
        src = f"{media_subdir}/{filename}"
        output_path = media_dir / filename

        with image.open() as image_bytes:
            output_path.write_bytes(image_bytes.read())

        alt_text = get_image_alt_text_from_mammoth_image(image)
        saved_files.append(output_path)
        image_records.append(ImageRecord(filename=filename, src=src, alt=alt_text, content_type=content_type))
        return {"src": src, "alt": alt_text}

    return mammoth.images.img_element(convert_image)


def clean_soup(soup: BeautifulSoup) -> None:
    for p in list(soup.find_all("p")):
        if not normalise_text(p.get_text(" ", strip=True)) and not p.find(["img", "table", "iframe"]):
            p.decompose()

    for img in soup.find_all("img"):
        existing = img.get("style", "")
        if existing:
            existing = existing.rstrip(";") + "; "
        img["style"] = existing + "display: block; max-width: 90%; height: auto; margin: 1em auto;"

    for table in soup.find_all("table"):
        table["border"] = "1"
        table["cellpadding"] = "6"
        table["cellspacing"] = "0"
        table["style"] = "border-collapse: collapse; width: 100%; max-width: 100%;"
        for cell in table.find_all(["td", "th"]):
            existing = cell.get("style", "")
            if existing:
                existing = existing.rstrip(";") + "; "
            cell["style"] = existing + "border: 1px solid #999; padding: 6px 10px; vertical-align: top;"


def split_into_sections(soup: BeautifulSoup, slide_heading_level: str = "h2") -> tuple[str, List[Section], List[str]]:
    body = soup.body or soup
    sections: List[Section] = []
    detected_headings: List[str] = []
    title: Optional[str] = None
    current: Optional[Section] = None
    slide_heading_level = slide_heading_level.lower()

    for el in list(body.children):
        if not isinstance(el, Tag):
            continue

        tag_name = el.name.lower()
        text = element_text(el)

        if tag_name in {"h1", "h2", "h3", "h4", "h5", "h6"} and text:
            detected_headings.append(f"{tag_name.upper()}: {text}")

        if tag_name == "h1" and text and title is None:
            title = text
            continue

        if tag_name == slide_heading_level and text:
            current = Section(title=text)
            sections.append(current)
            continue

        if current is None:
            continue

        if text or el.find(["img", "table"]):
            current.elements.append(str(el))

    if title is None:
        for heading in detected_headings:
            if ": " in heading:
                title = heading.split(": ", 1)[1]
                break

    return title or "", sections, detected_headings


def parse_docx(src_path: Path, media_work_root: Path, slide_heading_level: str) -> SourceDoc:
    source_slug = safe_filename(src_path.stem)
    source_media_slug = source_slug.lower()
    media_subdir = f"media/{source_media_slug}"
    media_dir = media_work_root / source_media_slug

    if media_dir.exists():
        shutil.rmtree(media_dir)

    saved_media_files: List[Path] = []
    image_records: List[ImageRecord] = []

    style_map = """
p[style-name='Body Text'] => p:fresh
p[style-name='Table Paragraph'] => p:fresh
p[style-name='List Paragraph'] => p:fresh
p[style-name='Default'] => p:fresh
p[style-name='Source Code'] => pre:separator('\\n') > code:fresh
r[style-name='Verbatim Char'] => code
"""

    with src_path.open("rb") as docx_file:
        result = mammoth.convert_to_html(
            docx_file,
            style_map=style_map,
            convert_image=make_image_converter(media_dir, media_subdir, saved_media_files, image_records),
        )

    soup = BeautifulSoup(result.value, "html.parser")
    if soup.body is None:
        wrapper = BeautifulSoup("<body></body>", "html.parser")
        wrapper.body.append(soup)
        soup = wrapper

    clean_soup(soup)

    title, sections, detected_headings = split_into_sections(soup, slide_heading_level=slide_heading_level)
    if not title:
        title = src_path.stem

    safe_title = safe_filename(src_path.stem)
    messages = [str(m) for m in result.messages]
    qa_findings: List[str] = []

    if not sections:
        qa_findings.append(f"No slide sections detected. Apply Word {slide_heading_level.upper()} styles for slide titles.")

    missing_alt = [img for img in image_records if not img.alt.strip()]
    if missing_alt:
        qa_findings.append(f"{len(missing_alt)} image(s) have missing alt text. Add alt text in Word for accessibility.")

    if messages:
        qa_findings.append("Mammoth produced conversion messages; inspect QA report.")

    return SourceDoc(
        source_path=src_path,
        source_name=src_path.name,
        source_stem=src_path.stem,
        title=title,
        safe_title=safe_title,
        output_folder=safe_title,
        media_subdir=media_subdir,
        media_files=saved_media_files,
        sections=sections,
        detected_headings=detected_headings,
        image_records=image_records,
        messages=messages,
        qa_findings=qa_findings,
    )


YOUTUBE_PATTERNS = [
    re.compile(r"https?://(?:www\.)?youtube\.com/watch\?v=([A-Za-z0-9_-]+)"),
    re.compile(r"https?://youtu\.be/([A-Za-z0-9_-]+)"),
    re.compile(r"https?://(?:www\.)?youtube\.com/embed/([A-Za-z0-9_-]+)"),
]


def youtube_embed_url(url: str) -> Optional[str]:
    url = html.unescape(url.strip().strip("<>"))
    for pattern in YOUTUBE_PATTERNS:
        match = pattern.search(url)
        if match:
            return f"https://www.youtube.com/embed/{match.group(1)}"
    return None


def extract_panopto_id(url: str) -> Optional[str]:
    url = html.unescape(url.strip().strip("<>"))
    match = re.search(r"[?&]id=([a-zA-Z0-9\-]+)", url)
    return match.group(1) if match else None


def panopto_embed_url(url: str) -> Optional[str]:
    """
    Preserve the original Panopto host and query string.

    Do not reconstruct from urlparse(). In testing, reconstruction caused:
        :///Panopto/Pages/Embed.aspx?id=...
    """
    url = html.unescape(url.strip().strip("<>"))

    if not extract_panopto_id(url):
        return None

    if "/Pages/Viewer.aspx" in url:
        return url.replace("/Pages/Viewer.aspx", "/Pages/Embed.aspx")

    if "/Pages/Embed.aspx" in url:
        return url

    return None


def raw_html_block(html_text: str) -> str:
    return "```{=html}\n" + html_text.strip() + "\n```"


def youtube_iframe_block(url: str) -> str:
    embed = youtube_embed_url(url)
    if not embed:
        return f"<p>Invalid YouTube URL: {html.escape(url)}</p>"
    iframe = f"""
<iframe
  width="900"
  height="506"
  src="{embed}"
  title="YouTube video player"
  frameborder="0"
  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
  referrerpolicy="strict-origin-when-cross-origin"
  allowfullscreen>
</iframe>
"""
    return raw_html_block(iframe)


def panopto_iframe_block(url: str) -> str:
    embed = panopto_embed_url(url)
    if not embed:
        return f"<p>Invalid Panopto URL: {html.escape(url)}</p>"
    iframe = f"""
<iframe
  width="900"
  height="506"
  src="{html.escape(embed, quote=True)}"
  title="Panopto video player"
  frameborder="0"
  allowfullscreen>
</iframe>
"""
    return raw_html_block(iframe)


def iframe_block(url: str) -> str:
    safe_url = html.escape(html.unescape(url.strip().strip("<>")), quote=True)
    iframe = f"""
<iframe
  src="{safe_url}"
  width="900"
  height="560"
  frameborder="0"
  allowfullscreen>
</iframe>
"""
    return raw_html_block(iframe)


def process_metatags(qmd_text: str) -> str:
    text = qmd_text

        # Original bracket-style tags

    text = re.sub(
        r"<p>\s*\[YOUTUBE\]\s*</p>\s*<p>\s*(https?://[^<\s]+)\s*</p>",
        lambda m: youtube_iframe_block(m.group(1)),
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"<p>\s*\[YOUTUBE\]\s*(https?://[^<\s]+)\s*</p>",
        lambda m: youtube_iframe_block(m.group(1)),
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"<p>\s*\[IFRAME\]\s*</p>\s*<p>\s*(https?://[^<\s]+)\s*</p>",
        lambda m: iframe_block(m.group(1)),
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"<p>\s*\[IFRAME\]\s*(https?://[^<\s]+)\s*</p>",
        lambda m: iframe_block(m.group(1)),
        text,
        flags=re.IGNORECASE,
    )

    # Simple text forms

    text = re.sub(
        r"<p>\s*YouTubeEmbed\s*::\s*(https?://[^<\s]+)\s*</p>",
        lambda m: youtube_iframe_block(m.group(1)),
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"<p>\s*PanoptoEmbed\s*::\s*(https?://[^<\s]+)\s*</p>",
        lambda m: panopto_iframe_block(m.group(1)),
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"<p>\s*IFrameEmbed\s*::\s*(https?://[^<\s]+)\s*</p>",
        lambda m: iframe_block(m.group(1)),
        text,
        flags=re.IGNORECASE,
    )

    # Mammoth hyperlink versions

    text = re.sub(
        r'<p>\s*YouTubeEmbed\s*::\s*<a href="([^"]+)">.*?</a>\s*(?:<br\s*/?>)?\s*</p>',
        lambda m: youtube_iframe_block(m.group(1)),
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    text = re.sub(
        r'<p>\s*PanoptoEmbed\s*::\s*<a href="([^"]+)">.*?</a>\s*(?:<br\s*/?>)?\s*</p>',
        lambda m: panopto_iframe_block(m.group(1)),
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    text = re.sub(
        r'<p>\s*IFrameEmbed\s*::\s*<a href="([^"]+)">.*?</a>\s*(?:<br\s*/?>)?\s*</p>',
        lambda m: iframe_block(m.group(1)),
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    return text


def reveal_yaml(title: str, theme: str = "simple") -> str:
    return f"""---
title: {yaml_quote(title)}

format:
  revealjs:
    theme: {theme}
    controls: true
    progress: true
    slide-number: true
    scrollable: true
    incremental: false
    navigation-mode: linear
    controls-layout: edges
    transition: none
    auto-stretch: true
    center: false
---
"""


def html_fragments_to_qmd(elements: List[str]) -> str:
    return "\n\n".join(fragment.strip() for fragment in elements if fragment.strip())


def qmd_for_doc(doc: SourceDoc) -> str:
    parts: List[str] = []
    for section in doc.sections:
        parts.append(f"## {section.title}\n")
        body = html_fragments_to_qmd(section.elements)
        parts.append(body if body else "<!-- Empty slide generated from heading-only section. -->")
        parts.append("")
    return "\n\n".join(parts).strip() + "\n"


def copy_media_for_doc(doc: SourceDoc, media_work_root: Path, out_dir: Path) -> None:
    source_media_slug = Path(doc.media_subdir).name
    source_dir = media_work_root / source_media_slug
    target_dir = out_dir / doc.media_subdir

    if not source_dir.exists():
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    for src_file in source_dir.iterdir():
        if src_file.is_file():
            shutil.copy2(src_file, target_dir / src_file.name)


def write_quarto_yml(out_dir: Path) -> None:
    (out_dir / "_quarto.yml").write_text(
        "project:\n"
        "  type: website\n"
        "  resources:\n"
        "    - media/**\n",
        encoding="utf-8",
    )


def write_qa_report(doc: SourceDoc, out_dir: Path, qmd_path: Path) -> None:
    lines: List[str] = [
        "# Word to Reveal.js QA Report",
        "",
        f"Source file: `{doc.source_name}`",
        f"Presentation title: {doc.title}",
        f"QMD file: `{qmd_path.name}`",
        "",
        "## Summary",
        "",
        f"- Slides generated: {len(doc.sections)}",
        f"- Semantic headings detected: {len(doc.detected_headings)}",
        f"- Images extracted: {len(doc.image_records)}",
        "",
    ]
    if doc.sections:
        lines.extend(["## Slides generated", ""])
        for section in doc.sections:
            lines.append(f"- {section.title} ({len(section.elements)} content elements)")
        lines.append("")
    if doc.detected_headings:
        lines.extend(["## Detected headings", ""])
        for heading in doc.detected_headings:
            lines.append(f"- {heading}")
        lines.append("")
    if doc.image_records:
        lines.extend(["## Image accessibility", ""])
        for img in doc.image_records:
            alt_status = "present" if img.alt.strip() else "MISSING"
            line = f"- `{img.src}` | alt text: {alt_status}"
            if img.alt.strip():
                line += f" | alt: {img.alt}"
            lines.append(line)
        lines.append("")
    if doc.qa_findings:
        lines.extend(["## QA findings", ""])
        for finding in doc.qa_findings:
            lines.append(f"- {finding}")
        lines.append("")
    if doc.messages:
        lines.extend(["## Mammoth messages", ""])
        for msg in doc.messages:
            lines.append(f"- {msg}")
        lines.append("")
    lines.extend([
        "## Authoring guidance",
        "",
        "- Use Word Heading 1 for the presentation title.",
        "- Use Word Heading 2 for slide titles.",
        "- Keep each Heading 2 section slide-sized.",
        "- Set images to 'In Line with Text'.",
        "- Add alt text to images in Word.",
        "- Use `[YOUTUBE]` followed by a YouTube URL, or `YouTubeEmbed :: URL`.",
        "- Use `PanoptoEmbed :: URL` for Panopto Viewer or Embed URLs.",
        "",
    ])
    (out_dir / "qa_report_revealjs.md").write_text("\n".join(lines), encoding="utf-8")


def render_quarto(qmd_path: Path) -> None:
    subprocess.run(["quarto", "render", str(qmd_path)], check=True)


def write_reveal_output(doc: SourceDoc, output_root: Path, media_work_root: Path, theme: str, render: bool) -> Path:
    doc_out = output_root / doc.output_folder
    if doc_out.exists():
        shutil.rmtree(doc_out)
    doc_out.mkdir(parents=True, exist_ok=True)

    copy_media_for_doc(doc, media_work_root, doc_out)
    write_quarto_yml(doc_out)

    qmd_path = doc_out / f"{doc.safe_title}_slides.qmd"
    qmd_text = reveal_yaml(title=doc.title, theme=theme) + "\n" + qmd_for_doc(doc)
    qmd_text = process_metatags(qmd_text)
    qmd_path.write_text(qmd_text, encoding="utf-8")
    write_qa_report(doc, doc_out, qmd_path)

    if render:
        render_quarto(qmd_path)

    return qmd_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert DOCX files to Quarto Reveal.js QMD/HTML.")
    parser.add_argument("--input-glob", default="imports/presentations/**/*.docx", help="Input DOCX glob.")
    parser.add_argument("--output-dir", default="output/presentations", help="Output folder.")
    parser.add_argument("--slide-heading-level", default="h2", choices=["h1", "h2", "h3", "h4", "h5", "h6"])
    parser.add_argument("--theme", default="simple", help="Reveal.js theme.")
    parser.add_argument("--render", action="store_true", help="Run quarto render after QMD generation.")
    parser.add_argument("--clean", action="store_true", help="Delete the full output directory before running.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    cwd = Path.cwd()
    output_root = cwd / args.output_dir
    media_work_root = output_root / "_media_work"

    if args.clean and output_root.exists():
        shutil.rmtree(output_root)

    output_root.mkdir(parents=True, exist_ok=True)
    media_work_root.mkdir(parents=True, exist_ok=True)

    candidates = [
        p for p in sorted(cwd.glob(args.input_glob))
        if not p.name.startswith("~$") and p.suffix.lower() == ".docx"
    ]

    if not candidates:
        print("No DOCX files found.")
        print(f"Input glob: {args.input_glob}")
        print("Expected location example: imports/presentations/MySlides.docx")
        return

    qmd_paths: List[Path] = []
    try:
        for src_path in candidates:
            print(f"Converting {src_path}...")
            doc = parse_docx(src_path=src_path, media_work_root=media_work_root, slide_heading_level=args.slide_heading_level)
            qmd_path = write_reveal_output(doc=doc, output_root=output_root, media_work_root=media_work_root, theme=args.theme, render=args.render)
            qmd_paths.append(qmd_path)
            print(f"  Title: {doc.title}")
            print(f"  Slides: {len(doc.sections)}")
            print(f"  Images: {len(doc.image_records)}")
            print(f"  QMD: {qmd_path}")
            if args.render:
                print(f"  HTML should be in: {qmd_path.parent / '_site'}")

        print("\nDone.")
        print("Generated QMD files:")
        for qmd_path in qmd_paths:
            print(f"  - {qmd_path}")
        if not args.render:
            print("\nRender example:")
            print(f"  quarto render \"{qmd_paths[0]}\"")
    finally:
        if media_work_root.exists():
            shutil.rmtree(media_work_root)


if __name__ == "__main__":
    main()
