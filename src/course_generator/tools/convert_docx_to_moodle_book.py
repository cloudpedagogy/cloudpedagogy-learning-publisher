#!/usr/bin/env python3
"""
Generic DOCX to Moodle Book HTML ZIP Converter — v2 accessibility/heading QA edition

Converts one or more .docx files into Moodle Book import ZIP packages.

Main v2 additions:
- optional Word heading-based splitting, e.g. Heading 2 -> Moodle Book chapter;
- named section splitting retained as a fallback for legacy documents;
- Arial 11pt normal text CSS option;
- heading QA report: detected headings and possible fake/bold-only headings;
- image accessibility QA: missing alt text and image review flags;
- safer config-first approach for bulk PHM/Moodle Book work.

Basic use:
    python3 docx_to_moodle_book.py

Recommended H2 test:
    1. In Word, set main chapter headings to Heading 2.
    2. Leave normal text/questions as Normal.
    3. Use heading-based config or defaults below.
    4. Run this script and check qa_report.md.

Optional config:
    Create moodle_book_config.json in the same folder as the script.
    Run: python3 docx_to_moodle_book.py --init-config
"""

from __future__ import annotations

import argparse
import html
import json
import mimetypes
import re
import shutil
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import mammoth
from bs4 import BeautifulSoup, Tag


# =============================================================================
# DEFAULT CONFIGURATION
# =============================================================================

DEFAULT_CONFIG: Dict[str, Any] = {
    # Input/output
    "input_glob": "*.docx",
    "output_dir": "output_moodle_book",
    "output_mode": "per_doc",  # "per_doc" or "combined"
    "chapter_mode": "headings",  # "per_doc", "headings", "named_sections"
    "combined_zip_name": "Moodle_Book_Import.zip",

    # Naming
    "metadata_mode": "filename",  # "filename", "regex", or "config"
    "book_title": "Moodle Book Import",
    "zip_name_template": "{safe_title}_Moodle_Book_Import.zip",
    "folder_name_template": "{safe_title}",
    "parent_chapter_filename_template": "00_{safe_title}.html",
    "section_filename_template": "{section_index:02d}_{section_slug}.html",

    # Optional regex detection.
    "parent_pattern": "",
    "detected_title_template": "{source_stem}",
    "detected_safe_title_template": "{source_stem}",

    # Optional per-file metadata.
    "documents": {},

    # -------------------------------------------------------------------------
    # Section splitting
    # -------------------------------------------------------------------------
    # Recommended scalable/default behaviour for newly structured Word docs:
    # - set main Moodle chapters in Word as Heading 2;
    # - leave normal text and question numbers as Normal;
    # - the script splits only on h2.
    #
    # For legacy PHM102-style docs without reliable Word headings, you can switch
    # back to named section splitting using moodle_book_config.json:
    #   "section_headings": ["Introductory notes", "Extra exercises", "Suggested solutions"],
    #   "split_on_word_headings": false
    "section_headings": [],
    "split_on_word_headings": True,
    "word_heading_levels": ["h2"],
    "include_frontmatter": False,

    # Chapter behaviour.
    "create_parent_chapter": False,
    "parent_chapter_intro_template": "This Moodle Book section was generated from {source}.",
    "parent_chapter_list_sections": True,

    # Cleaning.
    "remove_patterns": [],
    "skip_line_patterns": [
        r"^Page\s+\d+\s*$",
    ],
    "exclude_filename_contains": [
        "Moodle_Book_Import",
        "output_moodle_book",
    ],

    # Accessibility / QA options.
    "accessibility": {
        "normal_font_family": "Arial, Helvetica, sans-serif",
        "normal_font_size": "11pt",
        "enforce_normal_font_size": True,
        "check_missing_alt_text": True,
        "flag_all_images_for_review": True,
        "check_possible_fake_headings": True,
        "fake_heading_max_words": 14,
        "warn_if_heading_count_exceeds": 30,
        "warn_if_no_headings_detected": True,
    },

    # HTML styling.
    "table_style": (
        "border-collapse: collapse; "
        "width: auto; "
        "max-width: 100%; "
        "margin-top: 1em; "
        "margin-bottom: 2em;"
    ),
    "cell_style": (
        "border: 1px solid #999; "
        "padding: 8px 12px; "
        "vertical-align: top; "
        "line-height: 1.35;"
    ),
    "image_style": (
        "display: block; "
        "max-width: 700px; "
        "height: auto; "
        "margin: 1em auto 1.5em auto;"
    ),
    "add_spacer_after_tables": True,

    # Mammoth style mapping.
    "style_map": """
p[style-name='Body Text'] => p:fresh
p[style-name='Table Paragraph'] => p:fresh
p[style-name='List Paragraph'] => p:fresh
p[style-name='Default'] => p:fresh
p[style-name='Source Code'] => pre:separator('\\n') > code:fresh
r[style-name='Verbatim Char'] => code
r[style-name='token'] => code
r[style-name='FunctionTok'] => code
r[style-name='NormalTok'] => code
r[style-name='Body Text Char'] => span
""",
}

PAGE_CSS_TEMPLATE = """
body {{
    font-family: {normal_font_family};
    line-height: 1.5;
}}
body, p, li, td, th {{
    font-family: {normal_font_family};
    {normal_font_size_rule}
}}
p {{
    margin-top: 0;
    margin-bottom: 1em;
}}
h1, h2, h3, h4, h5, h6 {{
    font-family: {normal_font_family};
    line-height: 1.25;
    margin-top: 1.4em;
    margin-bottom: 0.6em;
}}
table {{
    border-collapse: collapse;
    margin-top: 1em;
    margin-bottom: 2em;
    width: auto;
    max-width: 100%;
}}
td, th {{
    border: 1px solid #999;
    padding: 8px 12px;
    vertical-align: top;
    line-height: 1.35;
}}
th {{
    font-weight: bold;
}}
ol, ul {{
    margin-top: 1.2em;
    margin-bottom: 1.2em;
}}
li {{
    margin-bottom: 0.5em;
}}
img {{
    {image_style}
}}
pre {{
    white-space: pre-wrap;
    background: #f7f7f7;
    border: 1px solid #ddd;
    padding: 0.75em;
    overflow-x: auto;
}}
code {{
    font-family: Consolas, Monaco, monospace;
}}
.qa-warning {{
    border: 1px solid #c77;
    background: #fff4f4;
    padding: 0.75em;
    margin: 1em 0;
}}
"""

CONFIG_TEMPLATE_JSON = {
    "book_title": "PHM Moodle Book Import",
    "output_mode": "per_doc",
    "chapter_mode": "headings",
    "metadata_mode": "filename",

    "section_headings": [],
    "split_on_word_headings": True,
    "word_heading_levels": ["h2"],

    "remove_patterns": [
        "\\b2025[-–_]26\\b",
        "\\b2025\\s*[-–]\\s*2026\\b"
    ],
    "skip_line_patterns": [
        "^Page\\s+\\d+\\s*$"
    ],

    "accessibility": {
        "normal_font_family": "Arial, Helvetica, sans-serif",
        "normal_font_size": "11pt",
        "enforce_normal_font_size": True,
        "check_missing_alt_text": True,
        "flag_all_images_for_review": True,
        "check_possible_fake_headings": True,
        "fake_heading_max_words": 14,
        "warn_if_heading_count_exceeds": 30,
        "warn_if_no_headings_detected": True
    },

    "documents": {
        "example.docx": {
            "title": "Example Moodle Book",
            "safe_title": "example_moodle_book",
            "zip_name": "Example_Moodle_Book_Import.zip"
        }
    }
}


# =============================================================================
# DATA MODELS
# =============================================================================

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
class HeadingRecord:
    level: str
    text: str


@dataclass
class SourceDoc:
    source: str
    source_stem: str
    order: int
    title: str
    safe_title: str
    output_folder: str
    zip_name: str
    media_subdir: str
    media_files: List[Path]
    sections: List[Section]
    metadata_source: str
    messages: List[str] = field(default_factory=list)
    skipped_markers: List[str] = field(default_factory=list)
    suspicious_lines: List[str] = field(default_factory=list)
    qa_findings: List[str] = field(default_factory=list)
    detected_headings: List[HeadingRecord] = field(default_factory=list)
    possible_fake_headings: List[str] = field(default_factory=list)
    image_records: List[ImageRecord] = field(default_factory=list)


# =============================================================================
# CONFIGURATION HELPERS
# =============================================================================

def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(config_path: Optional[Path]) -> Dict[str, Any]:
    config = dict(DEFAULT_CONFIG)

    if config_path and config_path.exists():
        try:
            user_config = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON config file: {config_path}\n{exc}") from exc
        config = deep_merge(config, user_config)

    return config


def write_config_template(path: Path) -> None:
    if path.exists():
        raise SystemExit(f"Refusing to overwrite existing config file: {path}")
    path.write_text(json.dumps(CONFIG_TEMPLATE_JSON, indent=2), encoding="utf-8")


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def normalise_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).strip()


def safe_filename(text: str) -> str:
    text = text.strip()
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)
    return text.strip("_") or "untitled"


def remove_configured_patterns(text: str, config: Dict[str, Any]) -> str:
    out = text
    for pattern in config["remove_patterns"]:
        out = re.sub(pattern, "", out)
    return re.sub(r"\s{2,}", " ", out).strip()


def should_skip_line(text: str, config: Dict[str, Any]) -> bool:
    t = normalise_text(text)
    for pattern in config["skip_line_patterns"]:
        if re.match(pattern, t, flags=re.IGNORECASE):
            return True
    return False


def section_heading_match(text: str, config: Dict[str, Any]) -> Optional[str]:
    t = normalise_text(text).lower()
    for heading in config["section_headings"]:
        if t == str(heading).lower():
            return str(heading)
    return None


def element_text(el: Tag) -> str:
    return normalise_text(el.get_text(" ", strip=True))


def looks_suspicious(text: str) -> bool:
    t = normalise_text(text)

    suspicious_patterns = [
        r"\bin\s*\?\s*$",
        r"\?\?",
        r"\(\s*\)",
        r"±\s*[0-9.]+\s*\(\s*\)",
        r"=\s*[0-9.]+\s*±\s*[0-9.]+\s*\(\s*\)",
        r"=\s*$",
        r"^\s*[+\-*/=]\s*$",
        r"\[\s*\]",
        r"\{\s*\}",
        r"√\s*$",
        r"≤\s*$",
        r"≥\s*$",
    ]

    return any(re.search(pattern, t) for pattern in suspicious_patterns)


def extension_from_content_type(content_type: str) -> str:
    ext = mimetypes.guess_extension(content_type or "")
    if ext == ".jpe":
        ext = ".jpg"
    return ext or ".png"


def template_context(source_path: Path, order: int, regex_groups: Optional[Tuple[str, ...]] = None) -> Dict[str, Any]:
    ctx: Dict[str, Any] = {
        "source": source_path.name,
        "source_stem": source_path.stem,
        "safe_source_stem": safe_filename(source_path.stem),
        "order": order,
    }

    if regex_groups:
        for index, value in enumerate(regex_groups, start=1):
            ctx[f"group{index}"] = value
            ctx[f"safe_group{index}"] = safe_filename(value)

    return ctx


def render_template(template: str, ctx: Dict[str, Any]) -> str:
    try:
        return template.format(**ctx)
    except KeyError as exc:
        missing = exc.args[0]
        raise SystemExit(f"Template references missing value: {missing}\nTemplate: {template}") from exc


def get_image_alt_text_from_mammoth_image(image: Any) -> str:
    """
    Best-effort attempt to preserve alt text if Mammoth exposes it.

    Mammoth's Python image object may not consistently expose Word alt text across
    document/image types, so this function is deliberately defensive. If no alt
    text is available, it returns an empty string and the QA report flags it.
    """
    for attr in ("alt_text", "alt", "description", "title"):
        value = getattr(image, attr, None)
        if isinstance(value, str) and value.strip():
            return normalise_text(value)

    # Some versions/objects may expose a dict-like metadata object.
    for attr in ("metadata", "_metadata"):
        metadata = getattr(image, attr, None)
        if isinstance(metadata, dict):
            for key in ("alt_text", "alt", "description", "title"):
                value = metadata.get(key)
                if isinstance(value, str) and value.strip():
                    return normalise_text(value)

    return ""


def is_possible_fake_heading(el: Tag, config: Dict[str, Any]) -> bool:
    """
    Detect paragraphs that look like headings visually but are not semantic headings.
    This is intentionally conservative and only flags likely cases for human review.
    """
    accessibility = config.get("accessibility", {})
    if not accessibility.get("check_possible_fake_headings", True):
        return False

    if el.name.lower() != "p":
        return False

    text = element_text(el)
    if not text:
        return False

    max_words = int(accessibility.get("fake_heading_max_words", 14))
    if len(text.split()) > max_words:
        return False

    # Avoid flagging common question/list markers.
    if re.match(r"^(\d+\)|\d+\.|[a-z]\)|[ivxlcdm]+\))$", text.strip(), flags=re.IGNORECASE):
        return False

    # Paragraph mostly/entirely strong or bold inline content.
    strong_text = " ".join(s.get_text(" ", strip=True) for s in el.find_all(["strong", "b"]))
    strong_text = normalise_text(strong_text)

    if strong_text and strong_text.lower() == text.lower():
        return True

    # Inline style-based bold paragraph.
    style = (el.get("style") or "").lower()
    if "font-weight" in style and "bold" in style:
        return True

    return False


# =============================================================================
# METADATA
# =============================================================================

def resolve_doc_metadata(
    source_path: Path,
    order: int,
    all_text: str,
    config: Dict[str, Any],
) -> Tuple[str, str, str, str, str]:
    docs_config = config.get("documents", {})
    doc_override = docs_config.get(source_path.name) or docs_config.get(source_path.stem)

    base_ctx = template_context(source_path, order)

    if doc_override:
        title = doc_override.get("title") or source_path.stem
        safe_title = doc_override.get("safe_title") or safe_filename(title)
        output_folder = doc_override.get("output_folder") or render_template(
            config["folder_name_template"],
            {**base_ctx, "title": title, "safe_title": safe_title}
        )
        zip_name = doc_override.get("zip_name") or render_template(
            config["zip_name_template"],
            {**base_ctx, "title": title, "safe_title": safe_title}
        )
        return title, safe_filename(safe_title), safe_filename(output_folder), zip_name, "config"

    if config["metadata_mode"] == "regex" and config.get("parent_pattern"):
        search_target = all_text + "\n" + source_path.stem
        match = re.search(config["parent_pattern"], search_target, flags=re.IGNORECASE)
        if match:
            groups = tuple(match.groups())
            ctx = template_context(source_path, order, groups)
            title = render_template(config["detected_title_template"], ctx)
            raw_safe_title = render_template(config["detected_safe_title_template"], ctx)
            safe_title = safe_filename(raw_safe_title)
            output_folder = safe_filename(render_template(
                config["folder_name_template"],
                {**ctx, "title": title, "safe_title": safe_title}
            ))
            zip_name = render_template(
                config["zip_name_template"],
                {**ctx, "title": title, "safe_title": safe_title}
            )
            return title, safe_title, output_folder, zip_name, "regex"

    title = source_path.stem
    safe_title = safe_filename(source_path.stem)
    output_folder = safe_filename(render_template(
        config["folder_name_template"],
        {**base_ctx, "title": title, "safe_title": safe_title}
    ))
    zip_name = render_template(
        config["zip_name_template"],
        {**base_ctx, "title": title, "safe_title": safe_title}
    )
    return title, safe_title, output_folder, zip_name, "filename"


# =============================================================================
# QA CLASSIFICATION
# =============================================================================

def classify_mammoth_messages(messages: List[str]) -> List[str]:
    findings: List[str] = []
    joined = "\n".join(messages)

    if "v:path" in joined:
        findings.append(
            "Potential missing Word chart/drawing detected: Mammoth ignored `v:path`. "
            "Check for missing graphs, shapes, SmartArt, or pasted Excel/Office graphics. "
            "Recommended fix: convert the object to an inline PNG image in Word before conversion."
        )

    if "oMathPara" in joined or "oMath" in joined:
        findings.append(
            "Potential equation loss detected: Mammoth ignored Word equation elements. "
            "Check formulas carefully, especially confidence intervals, fractions, roots, and bracketed expressions. "
            "Recommended fix: convert equations to plain text/Unicode or use a Pandoc-based route for maths-heavy content."
        )

    if "office-word:anchorlock" in joined:
        findings.append(
            "Floating or anchored object detected. Images or shapes may have been positioned in Word rather than inline. "
            "Recommended fix: set affected objects to 'In line with text' before conversion."
        )

    if any(marker in joined for marker in ["Source Code", "Verbatim Char", "FunctionTok", "NormalTok"]):
        findings.append("Code-style content detected. Check that R/code examples appear correctly in the HTML output.")

    style_warnings = [
        msg for msg in messages
        if "Unrecognised paragraph style" in msg or "Unrecognised run style" in msg
    ]

    if style_warnings:
        findings.append(
            "Unrecognised Word styles were reported. These are usually lower-risk formatting issues, "
            "but check list spacing, tables, and code blocks visually."
        )

    return findings


def add_accessibility_findings(doc: SourceDoc, config: Dict[str, Any]) -> None:
    accessibility = config.get("accessibility", {})

    if accessibility.get("warn_if_no_headings_detected", True) and not doc.detected_headings:
        doc.qa_findings.append(
            "No semantic Word headings were detected in the converted HTML. If this document should split dynamically, "
            "apply real Word heading styles such as Heading 2 before conversion."
        )

    warn_limit = int(accessibility.get("warn_if_heading_count_exceeds", 30))
    if warn_limit and len(doc.detected_headings) > warn_limit:
        doc.qa_findings.append(
            f"High number of semantic headings detected ({len(doc.detected_headings)}). "
            "Check that question numbers or small subparts have not accidentally been styled as headings."
        )

    if doc.possible_fake_headings:
        doc.qa_findings.append(
            f"Possible fake headings detected ({len(doc.possible_fake_headings)}). These look visually like headings "
            "but are not semantic Word headings. Consider applying the correct Word Heading style where appropriate."
        )

    if accessibility.get("check_missing_alt_text", True):
        missing = [img for img in doc.image_records if not img.alt.strip()]
        if missing:
            doc.qa_findings.append(
                f"Images with missing alt text detected ({len(missing)}). Module organisers should add meaningful alt text "
                "in the Word source or after Moodle import where the image is pedagogically meaningful. Decorative images may use empty alt text."
            )

    if accessibility.get("flag_all_images_for_review", True) and doc.image_records:
        doc.qa_findings.append(
            f"Images extracted ({len(doc.image_records)}). Review graphs, diagrams, screenshots and charts for alt text, "
            "colour-only meaning, and sufficient contrast. Colour accessibility is flagged for review rather than automatically corrected."
        )


# =============================================================================
# IMAGE EXTRACTION
# =============================================================================

def make_image_converter(media_dir: Path, media_subdir: str, saved_files: List[Path], image_records: List[ImageRecord]):
    media_dir.mkdir(parents=True, exist_ok=True)
    image_counter = {"count": 0}

    def convert_image(image):
        image_counter["count"] += 1
        content_type = getattr(image, "content_type", "") or ""
        ext = extension_from_content_type(content_type)
        filename = f"image_{image_counter['count']:03d}{ext}"
        src = f"{media_subdir}/{filename}"
        output_path = media_dir / filename

        with image.open() as image_bytes:
            output_path.write_bytes(image_bytes.read())

        saved_files.append(output_path)

        alt_text = get_image_alt_text_from_mammoth_image(image)
        image_records.append(ImageRecord(filename=filename, src=src, alt=alt_text, content_type=content_type))

        return {
            "src": src,
            "alt": alt_text,
        }

    return mammoth.images.img_element(convert_image)


# =============================================================================
# HTML CLEANUP AND PARSING
# =============================================================================

def clean_soup(soup: BeautifulSoup, config: Dict[str, Any]) -> None:
    for p in list(soup.find_all("p")):
        if not normalise_text(p.get_text(" ", strip=True)) and not p.find(["img", "table"]):
            p.decompose()

    for text_node in soup.find_all(string=True):
        new = remove_configured_patterns(str(text_node), config)
        if new != str(text_node):
            text_node.replace_with(new)

    for img in soup.find_all("img"):
        img["style"] = config["image_style"]

    for table in soup.find_all("table"):
        table["border"] = "1"
        table["cellpadding"] = "6"
        table["cellspacing"] = "0"
        table["style"] = config["table_style"]

        for row in table.find_all("tr"):
            row["style"] = "vertical-align: top;"

        for cell in table.find_all(["td", "th"]):
            existing = cell.get("style", "")
            if existing:
                existing = existing.rstrip(";") + "; "
            cell["style"] = existing + config["cell_style"]

        if config["add_spacer_after_tables"]:
            spacer = soup.new_tag("p")
            spacer.string = "\u00a0"
            spacer["style"] = "margin: 0 0 1.5em 0;"
            table.insert_after(spacer)


def split_into_sections(
    soup: BeautifulSoup,
    config: Dict[str, Any],
) -> Tuple[List[Section], List[str], List[str], List[HeadingRecord], List[str]]:
    sections: List[Section] = []
    current: Optional[Section] = None
    skipped_markers: List[str] = []
    suspicious_lines: List[str] = []
    detected_headings: List[HeadingRecord] = []
    possible_fake_headings: List[str] = []
    state = "frontmatter"

    body = soup.body or soup
    heading_tags = {str(h).lower() for h in config["word_heading_levels"]}
    all_heading_tags = {"h1", "h2", "h3", "h4", "h5", "h6"}

    for el in list(body.children):
        if not isinstance(el, Tag):
            continue

        text = element_text(el)

        if not text and not el.find("img"):
            continue

        tag_name = el.name.lower()

        if tag_name in all_heading_tags and text:
            detected_headings.append(HeadingRecord(level=tag_name, text=text))

        if text and is_possible_fake_heading(el, config):
            possible_fake_headings.append(text)

        if text and should_skip_line(text, config):
            skipped_markers.append(text)
            continue

        if text and looks_suspicious(text):
            suspicious_lines.append(text)

        matched_heading = None

        # Priority 1: configured exact section headings.
        # This remains useful for legacy docs where heading styles are unreliable.
        if config["section_headings"]:
            matched_heading = section_heading_match(text, config)

        # Priority 2: Word headings converted by Mammoth to h1/h2/h3/etc.
        if (
            matched_heading is None
            and config["split_on_word_headings"]
            and tag_name in heading_tags
            and text
        ):
            matched_heading = text

        if matched_heading:
            current = Section(title=matched_heading)
            sections.append(current)
            state = "inside_section"
            continue

        if state == "frontmatter":
            if config["include_frontmatter"]:
                if current is None:
                    current = Section(title="Front matter")
                    sections.append(current)
                current.elements.append(str(el))
            continue

        if current is None:
            current = Section(title="Content")
            sections.append(current)

        current.elements.append(str(el))

    if not sections:
        whole = Section(title="Content")
        for el in list(body.children):
            if isinstance(el, Tag):
                text = element_text(el)
                if (text and not should_skip_line(text, config)) or el.find("img"):
                    whole.elements.append(str(el))
        sections = [whole]

    sections = [section for section in sections if section.elements or section.title]

    return (
        sections,
        sorted(set(skipped_markers)),
        sorted(set(suspicious_lines)),
        detected_headings,
        sorted(set(possible_fake_headings)),
    )


def parse_docx(src_path: Path, order: int, media_root: Path, config: Dict[str, Any]) -> SourceDoc:
    source_media_slug = safe_filename(src_path.stem).lower()
    media_subdir = f"media/{source_media_slug}"
    media_dir = media_root / source_media_slug
    saved_media_files: List[Path] = []
    image_records: List[ImageRecord] = []

    if media_dir.exists():
        shutil.rmtree(media_dir)
    media_dir.mkdir(parents=True, exist_ok=True)

    with src_path.open("rb") as docx_file:
        result = mammoth.convert_to_html(
            docx_file,
            style_map=config["style_map"],
            convert_image=make_image_converter(media_dir, media_subdir, saved_media_files, image_records),
        )

    soup = BeautifulSoup(result.value, "html.parser")

    if soup.body is None:
        wrapper = BeautifulSoup("<body></body>", "html.parser")
        wrapper.body.append(soup)
        soup = wrapper

    clean_soup(soup, config)

    all_text = soup.get_text("\n", strip=True)
    title, safe_title, output_folder, zip_name, metadata_source = resolve_doc_metadata(
        src_path,
        order,
        all_text,
        config,
    )

    sections, skipped_markers, suspicious_lines, detected_headings, possible_fake_headings = split_into_sections(soup, config)

    messages = [str(m) for m in result.messages]
    qa_findings = classify_mammoth_messages(messages)

    doc = SourceDoc(
        source=src_path.name,
        source_stem=src_path.stem,
        order=order,
        title=title,
        safe_title=safe_title,
        output_folder=output_folder,
        zip_name=zip_name,
        media_subdir=media_subdir,
        media_files=saved_media_files,
        sections=sections,
        metadata_source=metadata_source,
        messages=messages,
        skipped_markers=skipped_markers,
        suspicious_lines=suspicious_lines,
        qa_findings=qa_findings,
        detected_headings=detected_headings,
        possible_fake_headings=possible_fake_headings,
        image_records=image_records,
    )

    if metadata_source == "filename":
        doc.qa_findings.append(
            "Output naming used the source filename. For clearer Moodle import names, rename the DOCX file "
            "or add this document to moodle_book_config.json."
        )

    if len(sections) == 1 and sections[0].title == "Content":
        doc.qa_findings.append(
            "The document was exported as one content section. If you expected multiple Moodle chapters, "
            "configure section_headings in moodle_book_config.json or apply real Word heading styles and enable split_on_word_headings."
        )

    add_accessibility_findings(doc, config)

    return doc


# =============================================================================
# HTML OUTPUT
# =============================================================================

def page_css(config: Dict[str, Any]) -> str:
    accessibility = config.get("accessibility", {})
    normal_font_family = accessibility.get("normal_font_family", "Arial, Helvetica, sans-serif")
    normal_font_size = accessibility.get("normal_font_size", "11pt")
    enforce_size = accessibility.get("enforce_normal_font_size", True)
    normal_font_size_rule = f"font-size: {normal_font_size};" if enforce_size else ""

    return PAGE_CSS_TEMPLATE.format(
        image_style=config["image_style"],
        normal_font_family=normal_font_family,
        normal_font_size_rule=normal_font_size_rule,
    )


def full_html_page(title: str, body_fragments: List[str], config: Dict[str, Any]) -> str:
    body = "\n".join(body_fragments).strip()
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
{page_css(config)}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def parent_chapter_html(doc: SourceDoc, config: Dict[str, Any]) -> str:
    intro = config["parent_chapter_intro_template"].format(
        source=html.escape(doc.source),
        title=html.escape(doc.title),
        safe_title=html.escape(doc.safe_title),
    )

    body_parts = [f"<p>{intro}</p>"]

    if config["parent_chapter_list_sections"]:
        section_list = "\n".join(f"<li>{html.escape(section.title)}</li>" for section in doc.sections)
        body_parts.append(f"""
<p>Use the following chapters for this section:</p>
<ul>
{section_list}
</ul>
""")

    return full_html_page(doc.title, body_parts, config)


def copy_media_for_doc(doc: SourceDoc, media_work_root: Path, out_dir: Path) -> List[Path]:
    copied_files: List[Path] = []

    source_media_slug = Path(doc.media_subdir).name
    source_dir = media_work_root / source_media_slug
    target_dir = out_dir / doc.media_subdir

    if not source_dir.exists():
        return copied_files

    target_dir.mkdir(parents=True, exist_ok=True)

    for src_file in source_dir.iterdir():
        if src_file.is_file():
            dst_file = target_dir / src_file.name
            shutil.copy2(src_file, dst_file)
            copied_files.append(dst_file)

    return copied_files


def write_html_files_for_docs(
    docs: List[SourceDoc],
    out_dir: Path,
    combined: bool,
    media_work_root: Path,
    config: Dict[str, Any],
) -> List[Path]:
    written_files: List[Path] = []

    for doc_index, doc in enumerate(docs, start=1):
        written_files.extend(copy_media_for_doc(doc, media_work_root, out_dir))

        prefix = f"{doc_index:02d}_" if combined else ""

        if config["create_parent_chapter"]:
            parent_name = prefix + render_template(
                config["parent_chapter_filename_template"],
                {
                    "safe_title": doc.safe_title,
                    "title": doc.title,
                    "source_stem": doc.source_stem,
                    "order": doc.order,
                },
            )
            parent_file = out_dir / parent_name
            parent_file.write_text(parent_chapter_html(doc, config), encoding="utf-8")
            written_files.append(parent_file)

        for section_index, section in enumerate(doc.sections, start=1):
            section_slug = safe_filename(section.title).lower()
            child_name = prefix + render_template(
                config["section_filename_template"],
                {
                    "section_index": section_index,
                    "section_title": section.title,
                    "section_slug": section_slug,
                    "safe_title": doc.safe_title,
                    "title": doc.title,
                    "source_stem": doc.source_stem,
                    "order": doc.order,
                },
            )

            child_file = out_dir / child_name
            child_file.write_text(
                full_html_page(section.title, section.elements, config),
                encoding="utf-8",
            )
            written_files.append(child_file)

    return written_files


def create_zip(zip_path: Path, files: List[Path], base_dir: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for file_path in sorted(files):
            if file_path.is_file():
                z.write(file_path, arcname=file_path.relative_to(base_dir))


def write_combined_book(docs: List[SourceDoc], out_dir: Path, media_work_root: Path, config: Dict[str, Any]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)

    written_files = write_html_files_for_docs(
        docs,
        out_dir,
        combined=True,
        media_work_root=media_work_root,
        config=config,
    )

    zip_path = out_dir / config["combined_zip_name"]
    create_zip(zip_path, written_files, out_dir)
    write_qa_report(docs, out_dir, zip_path, config)

    return zip_path


def write_books_per_doc(docs: List[SourceDoc], out_dir: Path, media_work_root: Path, config: Dict[str, Any]) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)

    zip_paths: List[Path] = []

    for doc in docs:
        doc_folder = out_dir / doc.output_folder
        doc_folder.mkdir(parents=True, exist_ok=True)

        written_files = write_html_files_for_docs(
            [doc],
            doc_folder,
            combined=False,
            media_work_root=media_work_root,
            config=config,
        )

        zip_path = doc_folder / doc.zip_name
        create_zip(zip_path, written_files, doc_folder)
        write_qa_report([doc], doc_folder, zip_path, config)

        zip_paths.append(zip_path)

    return zip_paths


def write_qa_report(docs: List[SourceDoc], out_dir: Path, zip_path: Path, config: Dict[str, Any]) -> None:
    accessibility = config.get("accessibility", {})

    lines = [
        "# DOCX to Moodle Book Export QA Report",
        "",
        f"Book title: {config['book_title']}",
        "",
        "Original DOCX files were not modified.",
        "",
        f"Generated ZIP: `{zip_path.name}`",
        "",
        "Import route:",
        "",
        "- Moodle Book > Import chapter",
        "- Type: Each HTML file represents one chapter",
        "- Upload the generated ZIP",
        "",
        "Configuration used:",
        "",
        f"- Output mode: `{config['output_mode']}`",
        f"- Metadata mode: `{config['metadata_mode']}`",
        f"- Input glob: `{config['input_glob']}`",
        f"- Parent/detection pattern: `{config.get('parent_pattern') or 'not used'}`",
        f"- Section headings: {', '.join(config['section_headings']) if config['section_headings'] else 'not configured'}",
        f"- Split on Word headings: {config['split_on_word_headings']}",
        f"- Word heading levels used for splitting: {', '.join(config['word_heading_levels'])}",
        f"- Parent chapters created: {config['create_parent_chapter']}",
        f"- Normal font: {accessibility.get('normal_font_family', 'not configured')}",
        f"- Normal font size: {accessibility.get('normal_font_size', 'not configured')}",
        f"- Image display style: `{config['image_style']}`",
        "",
        "## QA interpretation guide",
        "",
        "- `v:path` usually means a Word chart, drawing, shape, SmartArt, or pasted Office graphic may not have converted.",
        "- `oMath` or `oMathPara` means a Word equation may not have converted correctly.",
        "- `office-word:anchorlock` usually means a floating or anchored object may need to be changed to inline in Word.",
        "- Missing alt text means the generated image has no meaningful screen-reader description.",
        "- Possible fake headings are visually bold/heading-like paragraphs that are not semantic Word headings.",
        "- Colour use in graphs/diagrams is flagged for human/AI review rather than automatically corrected.",
        "- Suspicious lines often indicate broken equations, empty brackets, or missing formula content.",
        "",
    ]

    for doc in docs:
        lines.extend([
            f"## {doc.source}",
            "",
            f"- Output title: {doc.title}",
            f"- Safe title / slug: `{doc.safe_title}`",
            f"- Output folder: `{doc.output_folder}`",
            f"- ZIP name: `{doc.zip_name}`",
            f"- Metadata source: `{doc.metadata_source}`",
            f"- Sections detected: {len(doc.sections)}",
            f"- Semantic headings detected: {len(doc.detected_headings)}",
            f"- Possible fake headings detected: {len(doc.possible_fake_headings)}",
            f"- Images extracted: {len(doc.media_files)}",
            f"- Media folder in ZIP: `{doc.media_subdir}`",
            "",
            "### Sections generated",
            "",
        ])

        for section in doc.sections:
            lines.append(f"- {section.title} ({len(section.elements)} HTML elements)")
        lines.append("")

        if doc.detected_headings:
            lines.extend(["### Semantic headings detected in source", ""])
            for heading in doc.detected_headings[:150]:
                lines.append(f"- {heading.level.upper()}: {heading.text}")
            if len(doc.detected_headings) > 150:
                lines.append(f"- ... {len(doc.detected_headings) - 150} further headings omitted from report")
            lines.append("")

        if doc.possible_fake_headings:
            lines.extend(["### Possible fake headings to review", ""])
            for heading in doc.possible_fake_headings[:120]:
                lines.append(f"- {heading}")
            if len(doc.possible_fake_headings) > 120:
                lines.append(f"- ... {len(doc.possible_fake_headings) - 120} further possible fake headings omitted from report")
            lines.append("")

        if doc.image_records:
            lines.extend(["### Image accessibility review", ""])
            for image_record in doc.image_records:
                alt_status = "present" if image_record.alt.strip() else "MISSING"
                lines.append(
                    f"- `{image_record.src}` | alt text: {alt_status}"
                    + (f" | alt: {image_record.alt}" if image_record.alt.strip() else "")
                )
            lines.append("")

        if doc.qa_findings:
            lines.extend(["### QA findings / manual checks required", ""])
            for finding in doc.qa_findings:
                lines.append(f"- {finding}")
            lines.append("")

        if doc.suspicious_lines:
            lines.extend(["### Suspicious lines to check", ""])
            for line in doc.suspicious_lines[:120]:
                lines.append(f"- {line}")
            lines.append("")

        if doc.skipped_markers:
            lines.extend(["### Skipped lines", ""])
            for marker in doc.skipped_markers[:80]:
                lines.append(f"- {marker}")
            lines.append("")

        if doc.messages:
            lines.extend(["### Mammoth conversion messages", ""])
            for msg in doc.messages[:150]:
                lines.append(f"- {msg}")
            lines.append("")

    (out_dir / "qa_report.md").write_text("\n".join(lines), encoding="utf-8")


# =============================================================================
# MAIN
# =============================================================================

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert DOCX files into Moodle Book import ZIP packages."
    )

    parser.add_argument(
        "--config",
        default="moodle_book_config.json",
        help="Path to optional JSON config file. Default: moodle_book_config.json",
    )

    parser.add_argument(
        "--init-config",
        action="store_true",
        help="Create an example moodle_book_config.json and exit.",
    )

    parser.add_argument(
        "--input-glob",
        help="Override config input_glob, e.g. '*.docx' or 'input/*.docx'."
    )

    parser.add_argument(
        "--output-dir",
        help="Override config output_dir."
    )

    parser.add_argument(
        "--output-mode",
        choices=["per_doc", "combined"],
        help="Override config output_mode."
    )

    parser.add_argument(
        "--metadata-mode",
        choices=["filename", "regex", "config"],
        help="Override config metadata_mode."
    )

    parser.add_argument(
        "--chapter-mode",
        choices=["per_doc", "headings", "named_sections"],
        help=(
            "Chaptering strategy. "
            "per_doc = one DOCX becomes one Moodle Book chapter; "
            "headings = split by Word heading levels; "
            "named_sections = split using section_headings from the JSON config."
        ),
    )

    parser.add_argument(
        "--no-parent-chapter",
        action="store_true",
        help="Do not create a parent/overview HTML chapter.",
    )

    parser.add_argument(
        "--include-frontmatter",
        action="store_true",
        help="Include content before the first detected section as a Front matter chapter.",
    )

    parser.add_argument(
        "--split-on-word-headings",
        action="store_true",
        help="Split on configured Word heading levels.",
    )

    parser.add_argument(
        "--word-heading-levels",
        help="Comma-separated heading levels for splitting, e.g. h2 or h2,h3. Overrides config.",
    )

    parser.add_argument(
        "--use-named-section-headings",
        action="store_true",
        help="Use section_headings defined in moodle_book_config.json.",
    )

    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    cwd = Path.cwd()
    config_path = Path(args.config)

    if args.init_config:
        write_config_template(config_path)
        print(f"Created example config file: {config_path}")
        return

    config = load_config(config_path)

    if args.input_glob:
        config["input_glob"] = args.input_glob
    if args.output_dir:
        config["output_dir"] = args.output_dir
    if args.output_mode:
        config["output_mode"] = args.output_mode
    if args.chapter_mode:
        config["chapter_mode"] = args.chapter_mode
    if args.metadata_mode:
        config["metadata_mode"] = args.metadata_mode
    if args.no_parent_chapter:
        config["create_parent_chapter"] = False
    if args.include_frontmatter:
        config["include_frontmatter"] = True
    if args.split_on_word_headings:
        config["split_on_word_headings"] = True
    if args.word_heading_levels:
        config["word_heading_levels"] = [h.strip().lower() for h in args.word_heading_levels.split(",") if h.strip()]

    if args.use_named_section_headings:
        config["chapter_mode"] = "named_sections"

    if config["chapter_mode"] == "per_doc":

        config["section_headings"] = []
        config["split_on_word_headings"] = False
        config["include_frontmatter"] = True

    elif config["chapter_mode"] == "headings":

        config["section_headings"] = []
        config["split_on_word_headings"] = True

        if not config.get("word_heading_levels"):
            config["word_heading_levels"] = ["h2"]

    elif config["chapter_mode"] == "named_sections":

        config["split_on_word_headings"] = False
        config["include_frontmatter"] = True

        if not config.get("section_headings"):
            raise SystemExit(
                "chapter_mode='named_sections' requires section_headings in moodle_book_config.json."
            )

    if config["output_mode"] not in {"per_doc", "combined"}:
        raise SystemExit("Invalid output_mode. Use 'per_doc' or 'combined'.")

    if config["metadata_mode"] not in {"filename", "regex", "config"}:
        raise SystemExit("Invalid metadata_mode. Use 'filename', 'regex', or 'config'.")

    valid_heading_levels = {"h1", "h2", "h3", "h4", "h5", "h6"}
    bad_levels = [h for h in config["word_heading_levels"] if h.lower() not in valid_heading_levels]
    if bad_levels:
        raise SystemExit(f"Invalid word_heading_levels: {bad_levels}. Use values like h2 or h2,h3.")

    if config["section_headings"] and config["split_on_word_headings"]:
        print(
            "WARNING: section_headings and split_on_word_headings are both enabled. "
            "Named section headings have priority. Consider using one method at a time for clearer QA."
        )

    out_dir = cwd / config["output_dir"]
    media_work_root = out_dir / "_media_work"

    if out_dir.exists():
        shutil.rmtree(out_dir)

    out_dir.mkdir(parents=True, exist_ok=True)
    media_work_root.mkdir(parents=True, exist_ok=True)

    candidates = [
        p for p in cwd.glob(config["input_glob"])
        if not p.name.startswith("~$")
        and p.suffix.lower() == ".docx"
        and all(exclusion not in str(p) for exclusion in config["exclude_filename_contains"])
    ]

    if not candidates:
        print("No source .docx files found.")
        print(f"Input glob: {config['input_glob']}")
        print("Place this script in the folder with the source Word files, or set --input-glob.")
        return

    docs: List[SourceDoc] = []

    for order, src in enumerate(sorted(candidates), start=1):
        print(f"Converting {src.name}...")
        try:
            doc = parse_docx(src, order=order, media_root=media_work_root, config=config)
            docs.append(doc)
            print(f"  Output title: {doc.title}")
            print(f"  Metadata source: {doc.metadata_source}")
            print(f"  Sections detected: {len(doc.sections)}")
            print(f"  Semantic headings detected: {len(doc.detected_headings)}")
            print(f"  Possible fake headings: {len(doc.possible_fake_headings)}")
            print(f"  Images extracted: {len(doc.media_files)}")
            if doc.qa_findings:
                print(f"  QA warnings: {len(doc.qa_findings)}")
        except Exception as e:
            print(f"  ERROR converting {src.name}: {e}", file=sys.stderr)

    if not docs:
        print("No files converted.")
        return

    docs.sort(key=lambda d: (d.order, d.source))

    print("")
    print(f"Output mode: {config['output_mode']}")
    print(f"Output folder: {out_dir}")

    try:
        if config["output_mode"] == "combined":
            zip_path = write_combined_book(docs, out_dir, media_work_root, config)
            print("")
            print("Done.")
            print(f"Upload this ZIP to Moodle: {zip_path}")
            print("Check qa_report.md first.")

        elif config["output_mode"] == "per_doc":
            zip_paths = write_books_per_doc(docs, out_dir, media_work_root, config)
            print("")
            print("Done.")
            print("Generated Moodle Book ZIPs:")
            for zip_path in zip_paths:
                print(f"  - {zip_path}")
            print("Check each qa_report.md before importing.")

    finally:
        if media_work_root.exists():
            shutil.rmtree(media_work_root)


if __name__ == "__main__":
    main()
