from pathlib import Path
from urllib.parse import urlparse
import subprocess
import sys
import yaml
import re


def strip_yaml_front_matter(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return "\n".join(lines[i + 1:]).strip()
    return text.strip()


def filename_from_url(url: str) -> str:
    path = urlparse(url).path
    filename = Path(path).name
    return filename if filename else url


def strip_inline_html_tags(text: str) -> str:
    text = re.sub(r"</?(strong|b|em|i)>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def clean_html_tags(text: str) -> str:
    text = re.sub(r"<strong>(.*?)</strong>", r"**\1**", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<b>(.*?)</b>", r"**\1**", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<em>(.*?)</em>", r"*\1*", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<i>(.*?)</i>", r"*\1*", text, flags=re.IGNORECASE | re.DOTALL)
    return text


def fix_unicode_math(text: str) -> str:
    text = text.replace("R₀", r"$R_0$")
    text = text.replace("basic reproduction number (R0)", r"basic reproduction number ($R_0$)")
    return text


def clean_step_markers(text: str) -> str:
    text = re.sub(r"(?m)^\s*[-*•]?\s*Step\s+(\d+)\s*::\s*(.+)$", r"\1. \2", text)
    text = re.sub(r"(?m)^\s*[-*•]?\s*Step\s+(\d+):\s*(.+)$", r"\1. \2", text)
    text = re.sub(r"(?m)^(\d+)\.\s+", r"\n\1. ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def replace_callouts_for_pdf(text: str) -> str:
    callout_labels = {
        "important": "Important",
        "tip": "Tip",
        "note": "Note",
        "warning": "Warning",
        "caution": "Caution",
    }

    def repl(match):
        callout_type = match.group(1).lower()
        content = match.group(2).strip()
        label = callout_labels.get(callout_type, callout_type.title())
        return f"**{label}**\n\n{content}"

    return re.sub(
        r":::\s*\{\s*\.callout-([a-zA-Z0-9_-]+)[^}]*\}\s*\n(.*?)\n:::",
        repl,
        text,
        flags=re.DOTALL,
    )


def replace_details_for_pdf(text: str) -> str:
    def repl(match):
        summary = strip_inline_html_tags(match.group(1))
        content = match.group(2).strip()
        summary_clean = summary.lower().strip("* ").strip()

        if summary_clean in ["show steps", "steps"]:
            heading = "**Steps**"
        elif summary_clean in ["show answer", "answer"]:
            heading = "**Answer**"
        else:
            heading = f"**{summary}**"

        return f"{heading}\n\n{content}"

    return re.sub(
        r"<details>\s*<summary>(.*?)</summary>\s*(.*?)\s*</details>",
        repl,
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )


def replace_panel_tabsets_for_pdf(text: str) -> str:
    text = re.sub(r":::\s*\{\s*\.panel-tabset[^}]*\}\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n:::\s*", "\n", text)
    return text


def replace_iframes_for_pdf(text: str) -> str:
    def repl(match):
        iframe = match.group(0)

        src_match = re.search(r'src=["\']([^"\']+)["\']', iframe, flags=re.IGNORECASE)
        title_match = re.search(r'title=["\']([^"\']+)["\']', iframe, flags=re.IGNORECASE)

        if not src_match:
            return ""

        url = src_match.group(1)
        title = title_match.group(1).strip() if title_match else ""

        youtube_match = re.search(r'youtube\.com/embed/([^?&"\']+)', url, flags=re.IGNORECASE)
        if youtube_match:
            video_id = youtube_match.group(1)
            watch_url = f"https://www.youtube.com/watch?v={video_id}"
            return f"[Watch video on YouTube]({watch_url})"

        if "panopto" in url.lower():
            return f"[Watch video on Panopto]({url})"

        filename = filename_from_url(url)

        if title:
            return f"{title}\n\nResource file: `{filename}`"

        return f"Resource file: `{filename}`"

    return re.sub(
        r"<iframe\b[^>]*>.*?</iframe>",
        repl,
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )


def replace_resource_links_for_pdf(text: str) -> str:
    def repl(match):
        label = match.group(1).strip()
        url = match.group(2).strip()

        if re.match(r"^https?://", url, flags=re.IGNORECASE):
            return match.group(0)

        if url.startswith("#"):
            return match.group(0)

        filename = filename_from_url(url)

        if any(word in label.lower() for word in ["download", "dataset", "file", "report", "resource", "view"]):
            return f"Resource file: `{filename}`"

        return match.group(0)

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", repl, text)


def replace_quiz_forms_for_pdf(text: str) -> str:
    def repl(match):
        form = match.group(0)
        labels = re.findall(r"<label[^>]*>(.*?)</label>", form, flags=re.IGNORECASE | re.DOTALL)

        if not labels:
            return ""

        options = []
        for label in labels:
            cleaned = re.sub(r"<[^>]+>", "", label).strip()
            if cleaned:
                options.append(f"- {cleaned}")

        if not options:
            return ""

        return "**Options**\n\n" + "\n".join(options)

    return re.sub(r"<form\b[^>]*>.*?</form>", repl, text, flags=re.IGNORECASE | re.DOTALL)


def replace_webr_chunks_for_pdf(text: str) -> str:
    """
    Convert interactive WebR chunks into standard R chunks for PDF/DOCX
    handbook output.

    The importer currently emits WebR chunks as ```{webr-r}```.
    Earlier versions may have emitted ```{web-r}```. This function supports
    both forms.

    This is non-destructive because it only affects the temporary handbook
    content generated from QMD files. The original QMD files remain unchanged.

    Static R chunks already support the new metadata options generated by
    the importer, for example:

        #| echo: false
        #| results: hide
        #| fig-show: hide

    so no separate handbook conversion is needed for those.
    """

    def repl(match):
        body = match.group(2).strip()
        return f"```{{r}}\n{body}\n```"

    return re.sub(
        r"```\{(web-r|webr-r)\}\s*\n(.*?)\n```",
        repl,
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )


def remove_duplicate_resource_lines(text: str) -> str:
    lines = text.splitlines()
    cleaned_lines = []
    previous_resource = None

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("Resource file:"):
            if stripped == previous_resource:
                continue
            previous_resource = stripped
        elif stripped:
            previous_resource = None

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def remove_stray_markdown_artifacts(text: str) -> str:
    text = re.sub(r"\s+##\s*(?=\n|$)", "", text)
    text = re.sub(r"^\s*##\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\.\s+##\s+([A-Z])", r".\n\n## \1", text)
    return text


def remove_web_navigation(text: str) -> str:
    start = "<!-- START_NAVIGATION -->"
    end = "<!-- END_NAVIGATION -->"

    while start in text and end in text:
        text = text.split(start)[0] + text.split(end, 1)[1]

    return text


def remove_workflow_markers(text: str) -> str:
    for marker in [
        "<!-- IMPORT_START -->",
        "<!-- IMPORT_END -->",
        "<!-- Standard workflow: content imported from Word -->",
        "<!-- Advanced users may edit directly -->",
    ]:
        text = text.replace(marker, "")

    return text


def tidy_spacing(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def clean_content(text: str) -> str:
    text = strip_yaml_front_matter(text)
    text = remove_web_navigation(text)
    text = remove_workflow_markers(text)

    text = replace_callouts_for_pdf(text)
    text = replace_details_for_pdf(text)
    text = replace_panel_tabsets_for_pdf(text)
    text = replace_iframes_for_pdf(text)
    text = replace_resource_links_for_pdf(text)
    text = replace_quiz_forms_for_pdf(text)
    text = replace_webr_chunks_for_pdf(text)

    text = clean_html_tags(text)
    text = clean_step_markers(text)
    text = fix_unicode_math(text)
    text = remove_duplicate_resource_lines(text)
    text = remove_stray_markdown_artifacts(text)
    text = tidy_spacing(text)

    return text


def get_handbook_title(data: dict) -> str:
    website_title = data.get("website", {}).get("sidebar", {}).get("title")
    if website_title:
        return website_title

    site_title = data.get("website", {}).get("title")
    if site_title:
        return site_title

    project_title = data.get("project", {}).get("title")
    if project_title:
        return project_title

    return "Course Handbook"


def add_page_content(out: list[str], course_dir: Path, href: str, title: str):
    qmd_path = course_dir / href

    if not qmd_path.exists():
        print(f"Missing file, skipped: {qmd_path}")
        return

    out.append("")
    out.append(f"### {title}")
    out.append("")

    content = clean_content(qmd_path.read_text(encoding="utf-8"))
    out.append(content)
    out.append("")


def process_items(items, out: list[str], course_dir: Path, level: int = 1):
    for item in items:
        if "section" in item:
            title = item["section"]

            if level == 1 and out:
                out.append("\\newpage")
                out.append("")

            if level == 1:
                out.append(f"# {title}")
            elif level == 2:
                out.append(f"## {title}")
            else:
                out.append(f"### {title}")

            out.append("")

            if "contents" in item:
                process_items(item["contents"], out, course_dir, level + 1)

        elif "text" in item and "href" in item:
            href = item["href"]

            if href.endswith("index.qmd"):
                continue

            add_page_content(out, course_dir, href, item["text"])


def render_output(handbook_file: Path, output_format: str):
    subprocess.run(
        ["quarto", "render", str(handbook_file), "--to", output_format],
        check=True,
    )


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 src/course_generator/tools/build_handbook_from_quarto.py <course_dir> [output_qmd]")
        print("")
        print("Examples:")
        print("  python3 src/course_generator/tools/build_handbook_from_quarto.py course/outbreak_ve_demo")
        print("  python3 src/course_generator/tools/build_handbook_from_quarto.py course/outbreak_ve_demo output/outbreak_handbook.qmd")
        sys.exit(1)

    course_dir = Path(sys.argv[1]).resolve()

    if not course_dir.exists():
        raise FileNotFoundError(f"Course folder not found: {course_dir}")

    quarto_file = course_dir / "_quarto.yml"

    if not quarto_file.exists():
        raise FileNotFoundError(f"_quarto.yml not found in course folder: {course_dir}")

    if len(sys.argv) >= 3:
        handbook_file = Path(sys.argv[2]).resolve()
        handbook_file.parent.mkdir(parents=True, exist_ok=True)
    else:
        handbook_file = course_dir / "course-handbook.qmd"

    data = yaml.safe_load(quarto_file.read_text(encoding="utf-8"))
    contents = data["website"]["sidebar"]["contents"]
    handbook_title = get_handbook_title(data)

    out = [
        "---",
        f'title: "{handbook_title}"',
        "format:",
        "  pdf:",
        "    toc: true",
        "    toc-depth: 2",
        "    number-sections: false",
        "    pdf-engine: lualatex",
        "  docx:",
        "    toc: true",
        "    toc-depth: 2",
        "---",
        "",
    ]

    process_items(contents, out, course_dir)

    handbook_file.write_text("\n".join(out), encoding="utf-8")
    print(f"Created: {handbook_file}")
    print(f"Handbook title: {handbook_title}")

    render_output(handbook_file, "pdf")
    print("PDF generated")

    render_output(handbook_file, "docx")
    print("Word document generated")


if __name__ == "__main__":
    main()