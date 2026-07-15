#!/usr/bin/env python3

import argparse
import csv
import html
import re
import shutil
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup


PROJECT_ROOT = Path.cwd()
INPUT_DIR = PROJECT_ROOT / "input" / "original"
WORK_DIR = PROJECT_ROOT / "work"
OUTPUT_DIR = PROJECT_ROOT / "output"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp"}

WEAK_ALT_PATTERNS = [
    r"^image[_\-\s]?\d*\.?\w*$",
    r"^picture[_\-\s]?\d*\.?\w*$",
    r"^photo[_\-\s]?\d*\.?\w*$",
    r"^diagram$",
    r"^graph$",
    r"^chart$",
    r"^screenshot$",
]

LIST_MARKER_RE = re.compile(r"^[a-zA-Z0-9]+[\)\.]$")
NUMERIC_FRAGMENT_RE = re.compile(r"^[0-9.,%()\s+\-=/x]+$")


@dataclass
class Issue:
    severity: str
    category: str
    file: str
    message: str
    evidence: str = ""


@dataclass
class Chapter:
    number: int
    title: str
    html_path: Path
    folder: Path


def safe_name(path_or_text) -> str:
    text = Path(path_or_text).stem if isinstance(path_or_text, Path) else str(path_or_text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "untitled"


def ensure_dirs(*folders: Path) -> None:
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)


def validate_zip(zip_path: Path) -> None:
    if not zip_path.exists():
        raise FileNotFoundError(f"ZIP file not found: {zip_path}")
    if zip_path.suffix.lower() != ".zip":
        raise ValueError(f"Expected a .zip file, got: {zip_path}")
    if not zipfile.is_zipfile(zip_path):
        raise ValueError(f"File is not a valid ZIP archive: {zip_path}")


def extract_zip(zip_path: Path, work_dir: Path = WORK_DIR) -> Path:
    book_id = safe_name(zip_path)
    extracted_dir = work_dir / book_id / "extracted_ims"

    if extracted_dir.exists():
        shutil.rmtree(extracted_dir)

    extracted_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extracted_dir)

    return extracted_dir


def find_manifest(extracted_dir: Path) -> Path | None:
    matches = list(extracted_dir.rglob("imsmanifest.xml"))
    return matches[0] if matches else None


def find_html_files(extracted_dir: Path) -> list[Path]:
    return sorted(extracted_dir.rglob("*.html"))


def find_css_files(extracted_dir: Path) -> list[Path]:
    return sorted(extracted_dir.rglob("*.css"))


def find_media_files(extracted_dir: Path) -> list[Path]:
    return sorted(
        p for p in extracted_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )


def rel(path: Path, base: Path) -> str:
    return str(path.relative_to(base))


def read_html(path: Path) -> BeautifulSoup:
    return BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser")


def get_best_html_title(html_file: Path, fallback: str = "Untitled") -> str:
    soup = read_html(html_file)

    h1 = soup.find("h1")
    if h1 and h1.get_text(" ", strip=True):
        return h1.get_text(" ", strip=True)

    title_tag = soup.find("title")
    if title_tag and title_tag.get_text(" ", strip=True):
        return title_tag.get_text(" ", strip=True)

    if html_file.parent.name:
        return html_file.parent.name

    return fallback


def choose_chapter_title(
    manifest_title: str | None,
    html_file: Path,
    chapter_number: int,
) -> str:
    if manifest_title and manifest_title.strip():
        return manifest_title.strip()

    html_title = get_best_html_title(html_file, fallback="")
    if html_title:
        return html_title.strip()

    return f"Chapter {chapter_number}"


def is_weak_alt(alt: str) -> bool:
    alt_clean = alt.strip().lower()
    if len(alt_clean) < 8:
        return True
    return any(re.match(pattern, alt_clean) for pattern in WEAK_ALT_PATTERNS)


def markdown_to_text(markdown: str) -> str:
    text = markdown
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = text.replace("**", "")
    text = text.replace("`", "")
    return text


def parse_manifest_chapters(extracted_dir: Path) -> list[Chapter]:
    manifest = find_manifest(extracted_dir)

    if not manifest:
        html_files = find_html_files(extracted_dir)
        chapters = []
        for i, html_file in enumerate(html_files, start=1):
            title = choose_chapter_title(None, html_file, i)
            chapters.append(Chapter(i, title, html_file, html_file.parent))
        return chapters

    ns = {"ims": "http://www.imsglobal.org/xsd/imscp_v1p1"}
    tree = ET.parse(manifest)
    root = tree.getroot()

    resources = {}
    for resource in root.findall(".//ims:resource", ns):
        identifier = resource.attrib.get("identifier")
        xml_base = resource.attrib.get("{http://www.w3.org/XML/1998/namespace}base", "")
        href = resource.attrib.get("href", "index.html")
        if identifier:
            resources[identifier] = (xml_base, href)

    chapters = []
    for item in root.findall(".//ims:item", ns):
        identifier_ref = item.attrib.get("identifierref")
        title_el = item.find("ims:title", ns)
        manifest_title = title_el.text.strip() if title_el is not None and title_el.text else None

        if identifier_ref not in resources:
            continue

        xml_base, href = resources[identifier_ref]
        html_path = extracted_dir / xml_base / href

        if html_path.exists():
            chapter_number = len(chapters) + 1
            title = choose_chapter_title(manifest_title, html_path, chapter_number)
            chapters.append(
                Chapter(
                    number=chapter_number,
                    title=title,
                    html_path=html_path,
                    folder=html_path.parent,
                )
            )

    return chapters


def audit_images(html_file: Path, soup: BeautifulSoup, extracted_dir: Path) -> list[Issue]:
    issues = []
    file_label = rel(html_file, extracted_dir)

    for img in soup.find_all("img"):
        src = img.get("src", "").strip()
        alt = img.get("alt")

        if alt is None:
            issues.append(Issue("high", "Image accessibility", file_label, "Image is missing alternative text. This is a likely accessibility issue for screen reader users.", src))
        elif alt.strip() == "":
            issues.append(Issue("high", "Image accessibility", file_label, "Image has empty alternative text. This is only acceptable if the image is decorative.", src))
        elif is_weak_alt(alt):
            issues.append(Issue("medium", "Image accessibility", file_label, "Image alternative text may be too generic to be useful.", f"src={src}; alt={alt}"))

        if src:
            candidate = (html_file.parent / src).resolve()
            if not candidate.exists():
                issues.append(Issue("high", "Media integrity", file_label, "Image file appears to be missing or incorrectly referenced.", src))

    return issues


def audit_headings(html_file: Path, soup: BeautifulSoup, extracted_dir: Path) -> list[Issue]:
    issues = []
    file_label = rel(html_file, extracted_dir)

    headings = soup.find_all(re.compile("^h[1-6]$"))
    levels = []

    for heading in headings:
        level = int(heading.name[1])
        text = heading.get_text(" ", strip=True)
        levels.append((level, text))

    for i in range(1, len(levels)):
        previous_level, previous_text = levels[i - 1]
        current_level, current_text = levels[i]

        if current_level > previous_level + 1:
            issues.append(Issue("medium", "Heading structure", file_label, "Heading levels appear to skip a level, which may make page navigation harder for assistive technology users.", f"'{previous_text}' h{previous_level} → '{current_text}' h{current_level}"))

    return issues


def audit_tables(html_file: Path, soup: BeautifulSoup, extracted_dir: Path) -> list[Issue]:
    issues = []
    file_label = rel(html_file, extracted_dir)

    for index, table in enumerate(soup.find_all("table"), start=1):
        if not table.find("th"):
            issues.append(Issue("medium", "Table accessibility", file_label, "Table may not expose row or column headers clearly to screen reader users.", f"Table #{index}"))

    return issues


def audit_links(html_file: Path, soup: BeautifulSoup, extracted_dir: Path) -> list[Issue]:
    issues = []
    file_label = rel(html_file, extracted_dir)
    weak_text = {"click here", "here", "link", "read more", "more"}

    for link in soup.find_all("a"):
        href = link.get("href", "").strip()
        text = link.get_text(" ", strip=True).lower()

        if not text:
            issues.append(Issue("medium", "Link accessibility", file_label, "Link has no visible text.", href))
        elif text in weak_text:
            issues.append(Issue("low", "Link accessibility", file_label, "Link text may not be meaningful out of context.", f"text='{text}', href='{href}'"))

    return issues


def audit_inline_styles(html_file: Path, soup: BeautifulSoup, extracted_dir: Path) -> list[Issue]:
    issues = []
    file_label = rel(html_file, extracted_dir)
    risky_terms = ["font-size", "font-family", "color", "background", "text-align"]

    for tag in soup.find_all(style=True):
        style = tag.get("style", "")
        if any(term in style.lower() for term in risky_terms):
            text = tag.get_text(" ", strip=True)[:100]
            issues.append(Issue("low", "Formatting consistency", file_label, "Inline styling may override shared Moodle Book styling.", f"<{tag.name} style=\"{style}\"> {text}"))

    return issues


def audit_css(css_file: Path, extracted_dir: Path) -> list[Issue]:
    issues = []
    file_label = rel(css_file, extracted_dir)
    css = css_file.read_text(encoding="utf-8", errors="replace").lower()

    if "a:link" in css and "text-decoration: none" in css:
        issues.append(Issue("medium", "Link visibility", file_label, "Links may rely on colour alone because underlines appear to be removed in the stylesheet.", "text-decoration: none"))

    fixed_font_matches = re.findall(r"font-size\s*:\s*([0-9.]+)(px|pt)", css)
    for size, unit in fixed_font_matches:
        issues.append(Issue("low", "Formatting consistency", file_label, "Fixed font size found. Relative units may be better for user-controlled resizing.", f"font-size: {size}{unit}"))

    return issues


def looks_like_false_heading(text: str, tag) -> bool:
    text = text.strip()

    if not text:
        return True
    if tag.find_parent("table"):
        return True
    if tag.name not in {"p", "div"}:
        return True
    if len(text) < 10 or len(text) > 90:
        return True
    if LIST_MARKER_RE.match(text):
        return True
    if NUMERIC_FRAGMENT_RE.match(text):
        return True
    if text.lower() in {"total", "number", "weight", "frequency"}:
        return True
    if len(text.split()) < 2:
        return True

    return False


def audit_optional_fake_headings(html_file: Path, soup: BeautifulSoup, extracted_dir: Path) -> list[Issue]:
    issues = []
    file_label = rel(html_file, extracted_dir)

    for tag in soup.find_all(["p", "div"]):
        text = tag.get_text(" ", strip=True)
        style = (tag.get("style") or "").lower()

        has_bold_tag = tag.find(["b", "strong"]) is not None
        has_bold_style = "font-weight" in style and ("bold" in style or "700" in style)

        if not (has_bold_tag or has_bold_style):
            continue

        if looks_like_false_heading(text, tag):
            continue

        issues.append(Issue("low", "Optional semantic review", file_label, "Bold standalone text may be acting as a visual heading rather than a semantic heading.", text))

    return issues


def audit_package_references(extracted_dir: Path, html_files: list[Path], media_files: list[Path]) -> list[Issue]:
    issues = []
    referenced = set()

    for html_file in html_files:
        soup = read_html(html_file)
        for img in soup.find_all("img"):
            src = img.get("src", "").strip()
            if src:
                referenced.add((html_file.parent / src).resolve())

    actual_media = {p.resolve() for p in media_files}

    for media in sorted(actual_media - referenced):
        issues.append(Issue("low", "Media inventory", rel(media, extracted_dir), "Media file exists in the package but does not appear to be referenced by an HTML image tag."))

    return issues


def run_checks(extracted_dir: Path, html_files: list[Path], css_files: list[Path], media_files: list[Path], include_optional: bool = False) -> list[Issue]:
    issues = []

    for html_file in html_files:
        soup = read_html(html_file)
        issues.extend(audit_images(html_file, soup, extracted_dir))
        issues.extend(audit_headings(html_file, soup, extracted_dir))
        issues.extend(audit_tables(html_file, soup, extracted_dir))
        issues.extend(audit_links(html_file, soup, extracted_dir))
        issues.extend(audit_inline_styles(html_file, soup, extracted_dir))

        if include_optional:
            issues.extend(audit_optional_fake_headings(html_file, soup, extracted_dir))

    for css_file in css_files:
        issues.extend(audit_css(css_file, extracted_dir))

    issues.extend(audit_package_references(extracted_dir, html_files, media_files))

    return issues


def issue_counts(issues: list[Issue]) -> dict[str, int]:
    counts = {"high": 0, "medium": 0, "low": 0}
    for issue in issues:
        counts[issue.severity] = counts.get(issue.severity, 0) + 1
    return counts


def issues_by_category(issues: list[Issue]) -> dict[str, int]:
    counts = {}
    for issue in issues:
        counts[issue.category] = counts.get(issue.category, 0) + 1
    return counts


def has_category(issues: list[Issue], category: str) -> bool:
    return any(issue.category == category for issue in issues)


def build_report_text(zip_path: Path, book_id: str, extracted_dir: Path, manifest: Path | None, html_files: list[Path], css_files: list[Path], media_files: list[Path], issues: list[Issue], include_optional: bool) -> str:
    category_counts = issues_by_category(issues)
    blocker_issues = [i for i in issues if i.severity == "high"]
    improvement_issues = [i for i in issues if i.severity == "medium"]
    advisory_issues = [i for i in issues if i.severity == "low"]

    lines = [
        "# Moodle Book Accessibility QA Report",
        "",
        f"**Source ZIP:** `{zip_path}`",
        f"**Book ID:** `{book_id}`",
        "",
        "## 1. Accessibility triage summary",
        "",
        f"- Potential accessibility blockers detected: {len(blocker_issues)}",
        f"- Recommended accessibility improvements: {len(improvement_issues)}",
        f"- Advisory / optional review items shown: {len(advisory_issues)}",
        f"- Total findings shown in this report: {len(issues)}",
        "",
        "This report checks the exported Moodle Book IMS/HTML package before any changes are made in Moodle. It is intended for screening and triage, not as a formal accessibility sign-off.",
        "",
        "## 2. Plain-English interpretation",
        "",
    ]

    if not issues:
        lines.extend([
            "- No issues were detected by the current rule set.",
            "- No missing image alternative text was detected.",
            "- No broken image/media references were detected.",
            "- No obvious accessibility blockers were detected by this scan.",
        ])
    else:
        if not blocker_issues:
            lines.append("- No obvious accessibility blockers were detected by this scan.")
        if not has_category(issues, "Image accessibility"):
            lines.append("- No missing, empty, or weak image alternative text was detected.")
        if not has_category(issues, "Media integrity"):
            lines.append("- No broken image/media references were detected.")
        if has_category(issues, "Table accessibility"):
            lines.append("- Some tables may need clearer row or column headers for screen reader support.")
        if has_category(issues, "Link visibility"):
            lines.append("- Link styling may need review because links may rely on colour alone.")

    lines.extend(["", "## 3. Recommended actions", ""])

    if not blocker_issues and not improvement_issues:
        lines.append("- No blocker or recommended-improvement actions were identified.")
    else:
        if has_category(blocker_issues, "Image accessibility"):
            lines.append("- Ask module owners to review images flagged for missing or empty alternative text.")
        if has_category(blocker_issues, "Media integrity"):
            lines.append("- Check broken or missing media references before reusing/importing this Book.")
        if has_category(improvement_issues, "Image accessibility"):
            lines.append("- Review images with generic alternative text and improve where needed.")
        if has_category(improvement_issues, "Table accessibility"):
            lines.append("- Check whether flagged tables contain meaningful row or column headers. If so, mark those header cells semantically in Moodle/source HTML.")
        if has_category(improvement_issues, "Heading structure"):
            lines.append("- Review heading levels where the structure skips a level, as this may affect navigation for assistive technology users.")
        if has_category(improvement_issues, "Link accessibility"):
            lines.append("- Review links with missing or unclear visible text.")
        if has_category(improvement_issues, "Link visibility"):
            lines.append("- Confirm whether Moodle or the theme provides a visible non-colour cue for links; if not, consider restoring underlines.")

    lines.extend(["", "## 4. Blockers and recommended improvements", ""])

    priority_issues = blocker_issues + improvement_issues

    if not priority_issues:
        lines.append("No accessibility blockers or recommended improvements were detected.")
    else:
        for issue in priority_issues:
            label = "BLOCKER" if issue.severity == "high" else "RECOMMENDED IMPROVEMENT"
            lines.extend([
                f"### {label} — {issue.category}",
                "",
                f"- Location: `{issue.file}`",
                f"- Finding: {issue.message}",
                f"- Evidence: `{issue.evidence}`" if issue.evidence else "- Evidence: n/a",
                "",
            ])

    if include_optional:
        lines.extend(["", "## 5. Advisory findings", "", "These are lower-priority checks. They may support content improvement but should not usually be treated as accessibility blockers.", ""])

        if not advisory_issues:
            lines.append("No advisory findings detected.")
        else:
            for issue in advisory_issues:
                lines.extend([
                    f"### ADVISORY — {issue.category}",
                    "",
                    f"- Location: `{issue.file}`",
                    f"- Finding: {issue.message}",
                    f"- Evidence: `{issue.evidence}`" if issue.evidence else "- Evidence: n/a",
                    "",
                ])
    else:
        lines.extend(["", "## 5. Advisory findings", "", "Lower-confidence advisory checks, such as possible visual headings, are hidden by default. Run with `--include-optional` if you want to review them.", ""])

    lines.extend([
        "",
        "## 6. Package overview",
        "",
        f"- IMS manifest found: {'Yes' if manifest else 'No'}",
        f"- HTML chapter files found: {len(html_files)}",
        f"- CSS files found: {len(css_files)}",
        f"- Media/image files found: {len(media_files)}",
        "",
        "## 7. Findings by category",
        "",
    ])

    if category_counts:
        for category, count in sorted(category_counts.items()):
            lines.append(f"- {category}: {count}")
    else:
        lines.append("- No findings.")

    lines.extend([
        "",
        "## 8. Technical file inventory",
        "",
        "### Manifest",
        "",
        f"- `{rel(manifest, extracted_dir)}`" if manifest else "- No manifest found",
        "",
        "### HTML files",
        "",
    ])

    for file in html_files:
        lines.append(f"- `{rel(file, extracted_dir)}`")

    lines.extend(["", "### CSS files", ""])
    for file in css_files:
        lines.append(f"- `{rel(file, extracted_dir)}`")

    lines.extend(["", "### Media files", ""])
    for file in media_files:
        lines.append(f"- `{rel(file, extracted_dir)}`")

    lines.extend([
        "",
        "## Notes",
        "",
        "- This report is produced from the Moodle Book IMS/HTML export, not from a Word export.",
        "- The default report focuses on likely accessibility blockers and recommended structural improvements.",
        "- Advisory checks are hidden by default because some issues, such as bold text that looks like a heading, may be acceptable in worked examples, answers, or emphasis.",
        "- Human review is still needed for judgement-based tasks such as writing meaningful alternative text for complex diagrams or deciding whether a table is genuinely data-based.",
        "",
    ])

    return "\n".join(lines)


def write_reports(report_dir: Path, report_text: str, issues: list[Issue]) -> tuple[Path, Path, Path]:
    report_md = report_dir / "qa_report.md"
    report_txt = report_dir / "qa_report.txt"
    report_csv = report_dir / "qa_summary.csv"

    report_md.write_text(report_text, encoding="utf-8")
    report_txt.write_text(markdown_to_text(report_text), encoding="utf-8")

    with report_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["severity", "category", "file", "message", "evidence"])
        writer.writeheader()
        for issue in issues:
            writer.writerow({
                "severity": issue.severity,
                "category": issue.category,
                "file": issue.file,
                "message": issue.message,
                "evidence": issue.evidence,
            })

    return report_md, report_txt, report_csv


def audit(
    zip_path: Path,
    include_optional: bool = False,
    report_dir: Path | None = None,
    work_dir: Path = WORK_DIR,
) -> None:
    ensure_dirs(work_dir)
    validate_zip(zip_path)

    book_id = safe_name(zip_path)
    extracted_dir = extract_zip(zip_path, work_dir=work_dir)

    manifest = find_manifest(extracted_dir)
    html_files = find_html_files(extracted_dir)
    css_files = find_css_files(extracted_dir)
    media_files = find_media_files(extracted_dir)

    issues = run_checks(extracted_dir, html_files, css_files, media_files, include_optional=include_optional)

    if report_dir is None:
        report_dir = OUTPUT_DIR / "reports" / book_id

    report_dir.mkdir(parents=True, exist_ok=True)

    report_text = build_report_text(zip_path, book_id, extracted_dir, manifest, html_files, css_files, media_files, issues, include_optional)
    report_md, report_txt, report_csv = write_reports(report_dir, report_text, issues)

    counts = issue_counts(issues)

    print("Audit complete.")
    print(f"Extracted IMS folder: {extracted_dir}")
    print(f"Markdown report: {report_md}")
    print(f"Text report: {report_txt}")
    print(f"CSV summary: {report_csv}")
    print(
        f"Findings shown: {len(issues)} "
        f"(blockers/high={counts.get('high', 0)}, "
        f"recommended/medium={counts.get('medium', 0)}, "
        f"advisory/low={counts.get('low', 0)})"
    )


def check_pandoc_available() -> None:
    try:
        subprocess.run(["pandoc", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError("Pandoc is not available. Install Pandoc first, then rerun this command.")


def remove_moodle_header(body, expected_title: str | None = None) -> None:
    first_h1 = body.find("h1")
    if not first_h1:
        return

    # Moodle Book exports commonly include a top heading/header inside each chapter.
    # For reconstructed combined DOCX output, we insert our own clean chapter title,
    # so this prevents duplicate headings.
    first_h1.decompose()


def rewrite_image_paths_to_absolute(body, chapter_folder: Path) -> None:
    for img in body.find_all("img"):
        src = img.get("src", "")
        if src:
            abs_src = (chapter_folder / src).resolve()
            img["src"] = str(abs_src)


def export_docx(
    zip_path: Path,
    single_docx: bool = False,
    output_dir: Path | None = None,
    work_dir: Path = WORK_DIR,
) -> None:
    ensure_dirs(work_dir)
    validate_zip(zip_path)
    check_pandoc_available()

    book_id = safe_name(zip_path)
    extracted_dir = extract_zip(zip_path, work_dir=work_dir)
    chapters = parse_manifest_chapters(extracted_dir)

    if not chapters:
        raise RuntimeError("No HTML chapters found to export.")

    if output_dir is None:
        output_dir = OUTPUT_DIR / "docx" / book_id
        
    output_dir.mkdir(parents=True, exist_ok=True)

    if not single_docx:
        for chapter in chapters:
            slug = safe_name(chapter.title)
            output_docx = output_dir / f"{chapter.number:02d}_{slug}.docx"

            subprocess.run(
                [
                    "pandoc",
                    str(chapter.html_path),
                    "--resource-path",
                    str(chapter.folder),
                    "-o",
                    str(output_docx),
                ],
                check=True,
            )

            print(f"Created: {output_docx}")

    else:
        combined_dir = work_dir / book_id / "combined"
        combined_dir.mkdir(parents=True, exist_ok=True)
        combined_html = combined_dir / "combined_book.html"

        body_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            '<meta charset="utf-8">',
            f"<title>{html.escape(book_id)}</title>",
            "</head>",
            "<body>",
        ]

        for chapter in chapters:
            soup = read_html(chapter.html_path)
            body = soup.body if soup.body else soup

            remove_moodle_header(body, chapter.title)
            rewrite_image_paths_to_absolute(body, chapter.folder)

            clean_title = chapter.title.strip() if chapter.title else f"Chapter {chapter.number}"

            body_parts.append(f"<h1>{html.escape(clean_title)}</h1>")

            for child in body.children:
                body_parts.append(str(child))

            body_parts.append('<div style="page-break-after: always;"></div>')

        body_parts.extend(["</body>", "</html>"])
        combined_html.write_text("\n".join(body_parts), encoding="utf-8")

        output_docx = output_dir / f"{book_id}_combined.docx"

        subprocess.run(
            [
                "pandoc",
                str(combined_html),
                "-o",
                str(output_docx),
            ],
            check=True,
        )

        print(f"Combined HTML created: {combined_html}")
        print(f"Combined DOCX created: {output_docx}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Moodle Book IMS QA and accessibility toolkit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser("audit", help="Audit a Moodle Book IMS ZIP")
    audit_parser.add_argument("zip_path", help="Path to Moodle Book IMS ZIP file")
    audit_parser.add_argument("--include-optional", action="store_true", help="Include lower-confidence advisory checks such as possible fake headings.")
    audit_parser.add_argument("--report-dir", help="Folder for QA reports.")
    audit_parser.add_argument("--work-dir", default="work", help="Temporary working folder.")

    docx_parser = subparsers.add_parser("export-docx", help="Export Moodle Book IMS ZIP chapters to Word DOCX")
    docx_parser.add_argument("zip_path", help="Path to Moodle Book IMS ZIP file")
    docx_parser.add_argument("--single-docx", action="store_true", help="Export one combined DOCX instead of one DOCX per chapter.")
    docx_parser.add_argument("--output-dir", help="Folder for exported DOCX files.")
    docx_parser.add_argument("--work-dir", default="work", help="Temporary working folder.")

    args = parser.parse_args()

    if args.command == "audit":
        audit(
            Path(args.zip_path),
            include_optional=args.include_optional,
            report_dir=Path(args.report_dir) if args.report_dir else None,
            work_dir=Path(args.work_dir),
        )

    if args.command == "export-docx":
        export_docx(
            Path(args.zip_path),
            single_docx=args.single_docx,
            output_dir=Path(args.output_dir) if args.output_dir else None,
            work_dir=Path(args.work_dir),
        )


if __name__ == "__main__":
    main()