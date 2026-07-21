import os
import shutil
import subprocess
from pathlib import Path
import click
import re
import html
import yaml
from urllib.parse import urlparse, parse_qs
from ..core.config_loader import ConfigLoader

IMPORT_START = "<!-- IMPORT_START -->"
IMPORT_END = "<!-- IMPORT_END -->"


def check_pandoc():
    """Check if pandoc is installed and available in PATH."""
    return shutil.which("pandoc") is not None


def contains_webr_directive(content: str) -> bool:
    """Return True when imported Markdown requests browser-based WebR."""
    normalized = re.sub(r"\\\s*\n", "\n", content)
    return re.search(
        r"^\s*R Mode\s*::\s*webr\s*$",
        normalized,
        re.IGNORECASE | re.MULTILINE,
    ) is not None


def contains_html_embed_directive(content: str) -> bool:
    """Return True when imported Markdown contains a local HTML Embed block."""
    normalized = re.sub(r"\\\s*\n", "\n", content)
    return re.search(
        r"^\s*(?:#+\s*)?HTML Embed\s*::\s*.+$",
        normalized,
        re.IGNORECASE | re.MULTILINE,
    ) is not None


def is_webr_extension_installed(course_dir: Path) -> bool:
    """Detect an installed WebR extension without assuming one folder layout."""
    extensions_dir = course_dir / "_extensions"
    if not extensions_dir.exists():
        return False

    for marker in extensions_dir.rglob("_extension.yml"):
        if marker.parent.name.lower() == "webr":
            return True
        try:
            extension_data = yaml.safe_load(marker.read_text(encoding="utf-8")) or {}
            if str(extension_data.get("title", "")).strip().lower() == "webr":
                return True
            if str(extension_data.get("name", "")).strip().lower() == "webr":
                return True
        except (OSError, yaml.YAMLError):
            continue

    return False


def install_webr_extension(course_dir: Path):
    """Install the trusted WebR extension non-interactively when required."""
    if is_webr_extension_installed(course_dir):
        click.echo("WebR extension already installed")
        return

    if shutil.which("quarto") is None:
        raise RuntimeError(
            "WebR content was detected, but Quarto is not available in PATH. "
            "Install Quarto and rerun import-word."
        )

    click.echo("Installing trusted WebR extension (coatless/quarto-webr)...")
    result = subprocess.run(
        ["quarto", "add", "coatless/quarto-webr", "--no-prompt"],
        cwd=course_dir,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        details = (result.stderr or result.stdout or "Unknown Quarto error").strip()
        raise RuntimeError(f"WebR extension installation failed: {details}")

    if not is_webr_extension_installed(course_dir):
        raise RuntimeError(
            "Quarto reported success, but the WebR extension could not be found "
            f"under {course_dir / '_extensions'}."
        )

    click.echo("WebR extension installed")


def ensure_webr_filter(course_dir: Path):
    """Ensure the generated Quarto project enables the WebR filter."""
    quarto_config = course_dir / "_quarto.yml"
    if not quarto_config.exists():
        raise FileNotFoundError(f"Generated Quarto configuration not found: {quarto_config}")

    try:
        config_data = yaml.safe_load(quarto_config.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise RuntimeError(f"Unable to read {quarto_config}: {exc}") from exc

    filters = config_data.get("filters")
    if filters is None:
        config_data["filters"] = ["webr"]
    elif isinstance(filters, str):
        if filters == "webr":
            click.echo("WebR filter already enabled in _quarto.yml")
            return
        config_data["filters"] = [filters, "webr"]
    elif isinstance(filters, list):
        if "webr" in filters:
            click.echo("WebR filter already enabled in _quarto.yml")
            return
        filters.append("webr")
    else:
        raise RuntimeError(
            f"Unsupported filters structure in {quarto_config}; expected a string or list."
        )

    quarto_config.write_text(
        yaml.safe_dump(config_data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    click.echo("WebR filter enabled in _quarto.yml")


def ensure_webr_support(course_dir: Path):
    """Install and configure WebR for a generated course project."""
    install_webr_extension(course_dir)
    ensure_webr_filter(course_dir)


def ensure_html_resources(course_dir: Path):
    """Ensure Quarto copies local HTML activities into rendered output."""
    quarto_config = course_dir / "_quarto.yml"
    if not quarto_config.exists():
        raise FileNotFoundError(f"Generated Quarto configuration not found: {quarto_config}")

    try:
        config_data = yaml.safe_load(quarto_config.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise RuntimeError(f"Unable to read {quarto_config}: {exc}") from exc

    project = config_data.get("project")
    if project is None:
        project = {}
        config_data["project"] = project
    if not isinstance(project, dict):
        raise RuntimeError(
            f"Unsupported project structure in {quarto_config}; expected a mapping."
        )

    required_resource = "resources/**"
    resources = project.get("resources")
    if resources is None:
        project["resources"] = [required_resource]
    elif isinstance(resources, str):
        if resources == required_resource:
            click.echo("HTML resources already enabled in _quarto.yml")
            return
        project["resources"] = [resources, required_resource]
    elif isinstance(resources, list):
        if required_resource in resources:
            click.echo("HTML resources already enabled in _quarto.yml")
            return
        resources.append(required_resource)
    else:
        raise RuntimeError(
            f"Unsupported project.resources structure in {quarto_config}; "
            "expected a string or list."
        )

    quarto_config.write_text(
        yaml.safe_dump(config_data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    click.echo("HTML resources enabled in _quarto.yml")


def convert_docx_to_md(docx_path: Path, md_path: Path) -> Path:
    """
    Convert a DOCX file to Markdown using Pandoc, extracting embedded images.

    Pandoc writes embedded DOCX media to a sibling folder such as:
        imports/<course_id>/md/<doc_stem>_media/media/image1.png

    The returned media_dir is later used only for reporting/debugging; image path
    copying and rewriting are handled when the Markdown is inserted into the
    target QMD because only then do we know the final QMD location.
    """
    media_dir = md_path.parent / f"{md_path.stem}_media"
    media_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "pandoc",
        str(docx_path),
        "-t",
        "markdown",
        "--wrap=none",
        f"--extract-media={media_dir}",
        "-o",
        str(md_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(f"Pandoc conversion failed: {result.stderr}")

    return media_dir


def normalize_metadata_blocks(content: str) -> str:
    """
    Normalize Word/Pandoc directive blocks while preserving
    line structure required for interaction parsing.

    Pandoc may emit Word hard line breaks as trailing backslashes.
    For directive blocks, those backslashes need to become real
    newlines so parsers can detect markers such as R Code,
    R Mode ::, Alt ::, Caption ::, and END R Code.
    """

    directive_prefixes = [
        "Callout ::",
        "Title ::",
        "Text ::",
        "Reveal",
        "END Reveal",
        "SelfCheck",
        "END SelfCheck",
        "Question ::",
        "Type ::",
        "Answer ::",
        "Option ::",
        "Option",
        "END Option",
        "Correct ::",
        "Feedback ::",
        "Hint ::",
        "Explanation ::",
        "R Code",
        "END R Code",
        "R Example",
        "END R Example",
        "R Mode ::",
        "Echo ::",
        "Output ::",
        "Alt ::",
        "Caption ::",
        "Tabs",
        "END Tabs",
        "Tab ::",
        "END Tab",
        "Interpretation ::",
        "Assumptions ::",
        "Limitations ::",
        "Image ::",
        "END Image",
        "Width ::",
        "File ::",
        "END File",
        "Display ::",
        "Label ::",
        "Quiz",
        "END Quiz",
        "END Callout",
        "YouTubeEmbed ::",
        "PanoptoEmbed ::",
        "HTML Embed ::",
        "END HTML Embed",
        "Height ::",
        "Fallback Image ::",
    ]

    # Convert Pandoc hard-line-break markers into actual line breaks.
    # Example:
    #   R Code\
    #   R Mode :: webr\
    # becomes:
    #   R Code
    #   R Mode :: webr
    content = re.sub(r"\\\s*\n", "\n", content)

    normalized_lines = []

    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            normalized_lines.append("")
            continue

        if any(stripped.startswith(prefix) for prefix in directive_prefixes):
            normalized_lines.append(stripped)
            continue

        if re.match(r"^Step\s+\d+\s*::", stripped):
            normalized_lines.append(stripped)
            continue

        normalized_lines.append(line)

    return "\n".join(normalized_lines)


def normalize_doubled_latex_backslashes(math_text: str) -> str:
    """
    Normalize backslashes duplicated by Word/Pandoc inside a maths region.

    A doubled backslash is reduced only when it introduces a LaTeX command
    (for example ``\\\\frac`` or ``\\\\alpha``) or an escaped LaTeX symbol
    (for example ``\\\\%``). A standalone ``\\\\`` is preserved because it
    may be an intentional LaTeX line break.
    """
    return re.sub(r"\\\\(?=[A-Za-z]+|[%#&_{}])", r"\\", math_text)


def normalize_latex_in_math_regions(content: str) -> str:
    """
    Normalize doubled LaTeX backslashes only inside recognised maths regions.

    Markdown fenced code blocks are deliberately excluded so R code, regular
    expressions, paths and other code containing backslashes are unchanged.
    Supported maths delimiters are ``$...$``, ``$$...$$``, ``\\(...\\)`` and
    ``\\[...\\]``.
    """
    math_pattern = re.compile(
        r"""
        \$\$.*?\$\$                  # Display maths: $$ ... $$
        |
        (?<!\\)\$(?!\$).*?(?<!\\)\$  # Inline maths: $ ... $
        |
        \\\(.*?\\\)                   # Inline maths: \( ... \)
        |
        \\\[.*?\\\]                   # Display maths: \[ ... \]
        """,
        re.VERBOSE | re.DOTALL,
    )
    fenced_code_pattern = re.compile(
        r"(^[ \t]*(`{3,}|~{3,})[^\n]*\n.*?^[ \t]*\2[ \t]*$)",
        re.MULTILINE | re.DOTALL,
    )

    parts = fenced_code_pattern.split(content)
    # The capturing groups make each match occupy three consecutive entries:
    # full fence, delimiter, then the following non-code text.
    for index in range(0, len(parts), 3):
        parts[index] = math_pattern.sub(
            lambda match: normalize_doubled_latex_backslashes(match.group(0)),
            parts[index],
        )

    return "".join(
        part
        for index, part in enumerate(parts)
        if index % 3 != 2  # Omit the duplicated fence-delimiter capture.
    )


def normalize_math_blocks(content: str) -> str:
    """
    Normalize LaTeX math emitted by Pandoc/Word.

    Fixes:
    - escaped $$ delimiters
    - over-escaped inline/display math delimiters
    - escaped exponent operators
    - double-escaped LaTeX commands
    - blank lines inserted inside $$ display-math blocks
    """

    normalized_lines = []

    for line in content.split("\n"):
        stripped = line.strip()

        if stripped == r"\$\$":
            normalized_lines.append("$$")
            continue

        line = line.replace(r"\\[", r"\[")
        line = line.replace(r"\\]", r"\]")
        line = line.replace(r"\\(", r"\(")
        line = line.replace(r"\\)", r"\)")
        line = line.replace(r"\^", "^")

        normalized_lines.append(line)

    # Word/Pandoc can insert empty paragraphs immediately inside display-math
    # delimiters. Remove blank lines only while inside a $$ block so separate
    # equations and surrounding paragraph spacing remain untouched.
    compacted_lines = []
    in_display_math = False

    for line in normalized_lines:
        if line.strip() == "$$":
            compacted_lines.append("$$")
            in_display_math = not in_display_math
            continue

        if in_display_math and not line.strip():
            continue

        compacted_lines.append(line)

    content = "\n".join(compacted_lines)
    return normalize_latex_in_math_regions(content)


def clean_r_code(code: str) -> str:
    """
    Clean R code after Pandoc conversion.

    Fixes:
    - trailing backslashes
    - escaped symbols, including R's native pipe operator
    - artificial blank lines introduced by Word/Pandoc
    """
    cleaned_lines = []

    for raw_line in code.splitlines():
        line = raw_line.rstrip()

        if line.endswith("\\"):
            line = line[:-1].rstrip()

        # Clean escaped R and comparison symbols first.
        line = line.replace(r"\<-", "<-")
        line = line.replace(r"\"", '"')
        line = line.replace(r"\<", "<")
        line = line.replace(r"\>", ">")
        line = line.replace(r"\$", "$")
        line = line.replace(r"\~", "~")

        # Run after \> has been converted to >.
        # Supports one or more Pandoc escape backslashes.
        line = re.sub(r"\\+\|>", "|>", line)

        if line.strip():
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def rewrite_asset_path(asset_path: str, qmd_path: Path, course_dir: Path) -> str:
    """
    Rewrite a site-level asset path like 'resources/pdf/file.pdf' so it works
    from the nested location of the generated QMD/HTML page.
    """
    asset_path = asset_path.strip().replace("\\", "/")

    if not asset_path.startswith("resources/"):
        return asset_path

    qmd_parent = qmd_path.parent
    target_asset = course_dir / asset_path
    relative_path = os.path.relpath(target_asset, start=qmd_parent)
    return relative_path.replace("\\", "/")


def copy_imported_media_and_rewrite_paths(content: str, md_path: Path, qmd_path: Path, course_dir: Path) -> str:
    """
    Support embedded DOCX images converted by Pandoc.

    Pandoc writes embedded Word images as normal Markdown image links, for example:
        ![](01_r_and_rstudio_media/media/image1.jpg)

    Those media files initially live under imports/<course_id>/md/, but Quarto renders
    from the generated course directory. This function copies only Pandoc-extracted
    media into course/<course_id>/imported_media/<doc_stem>/ and rewrites the Markdown
    links so they are correct relative to the target QMD file.

    This deliberately does not touch your existing course-engine image directives:
        Image :: resources/images/example.png

    Those are still handled later by parse_images().
    """
    md_parent = md_path.parent
    media_dest_root = course_dir / "imported_media" / md_path.stem
    media_dest_root.mkdir(parents=True, exist_ok=True)

    def is_external_or_site_path(image_path: str) -> bool:
        normalized = image_path.strip().replace("\\", "/")
        return normalized.startswith((
            "http://",
            "https://",
            "mailto:",
            "#",
            "/",
            "../",
            "resources/",
            "imported_media/",
        ))

    def replace_match(match: re.Match) -> str:
        alt_text = match.group(1)
        image_path = match.group(2).strip().replace("\\", "/")

        # Leave existing external/site/resource links alone.
        if is_external_or_site_path(image_path):
            return match.group(0)

        # Safety guard: only rewrite Pandoc-extracted media paths.
        # This avoids interfering with manually authored Markdown image links.
        if "_media/" not in image_path and "_media/media/" not in image_path:
            return match.group(0)

        candidate_paths = [
            md_parent / image_path,
            Path(image_path),
        ]

        source_image = None

        for candidate in candidate_paths:
            if candidate.exists() and candidate.is_file():
                source_image = candidate.resolve()
                break

        if source_image is None:
            return match.group(0)

        dest_image = media_dest_root / source_image.name
        shutil.copy2(source_image, dest_image)

        rel_path = os.path.relpath(dest_image, start=qmd_path.parent).replace("\\", "/")
        return f"![{alt_text}]({rel_path})"

    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace_match, content)


def apply_following_alt_text_to_images(content: str) -> str:
    """
    Convert Moodle/Pandoc-style visible alt text lines into Quarto fig-alt metadata,
    without creating visible captions.

    Converts:

        ![](path/to/image.png){width="5.8in"}
        Alt text: Screenshot of the RStudio interface

    into:

        ![](path/to/image.png){width="5.8in" fig-alt="Screenshot of the RStudio interface"}
    """

    image_pattern = re.compile(
        r"^!\[([^\]]*)\]\(([^)]+)\)(\{[^}]*\})?\s*$"
    )
    alt_pattern = re.compile(
        r"^\s*Alt\s+text\s*:\s*(.+?)\s*$",
        re.IGNORECASE,
    )

    lines = content.splitlines()
    new_lines = []
    i = 0

    def clean_alt_text(value: str) -> str:
        value = re.sub(r"\s+", " ", value.strip())
        value = value.replace("\\", "\\\\").replace('"', '\\"')
        return value

    def add_fig_alt(attributes: str, alt_text: str) -> str:
        alt_attr = f'fig-alt="{alt_text}"'

        if attributes and attributes.startswith("{") and attributes.endswith("}"):
            inner = attributes[1:-1].strip()

            # Avoid duplicate fig-alt if already present.
            if re.search(r"\bfig-alt\s*=", inner):
                return attributes

            if inner:
                return "{" + inner + " " + alt_attr + "}"
            return "{" + alt_attr + "}"

        return "{" + alt_attr + "}"

    while i < len(lines):
        line = lines[i]
        image_match = image_pattern.match(line.strip())

        if not image_match:
            new_lines.append(line)
            i += 1
            continue

        existing_alt = image_match.group(1).strip()
        image_path = image_match.group(2).strip()
        attributes = image_match.group(3) or ""

        j = i + 1
        blank_lines = []

        while j < len(lines) and not lines[j].strip():
            blank_lines.append(lines[j])
            j += 1

        alt_match = alt_pattern.match(lines[j]) if j < len(lines) else None

        if alt_match:
            alt_text = clean_alt_text(existing_alt or alt_match.group(1))
            new_attributes = add_fig_alt(attributes, alt_text)

            # Keep square brackets empty so Quarto does not make a visible caption.
            new_lines.append(f"![]({image_path}){new_attributes}")

            if blank_lines:
                new_lines.append("")

            i = j + 1
            continue

        new_lines.append(line)
        i += 1

    return "\n".join(new_lines)


def copy_site_resources(course_dir: Path):
    """Copy top-level project resources into the generated course directory."""
    source_resources = Path("resources")
    if not source_resources.exists():
        click.echo(click.style("No top-level resources/ directory found; skipping resource copy", fg="yellow"))
        return

    dest_resources = course_dir / "resources"

    if dest_resources.exists():
        shutil.rmtree(dest_resources)

    shutil.copytree(source_resources, dest_resources)
    click.echo(f"Copied site resources to: {dest_resources}")


def is_markdown_heading(line: str) -> bool:
    return re.match(r"^#+\s+", line.strip()) is not None


def is_interaction_header(line: str) -> bool:
    stripped = line.strip()
    return any(
        re.match(pattern, stripped, re.IGNORECASE)
        for pattern in [
            r"^(?:#+\s*)?R Code\s*$",
            r"^(?:#+\s*)?END R Code\s*$",
            r"^(?:#+\s*)?R Example\s*$",
            r"^(?:#+\s*)?END R Example\s*$",
            r"^(?:#+\s*)?Tabs\s*$",
            r"^(?:#+\s*)?END Tabs\s*$",
            r"^(?:#+\s*)?Reveal\s*$",
            r"^(?:#+\s*)?END Reveal\s*$",
            r"^(?:#+\s*)?Quiz\s*$",
            r"^(?:#+\s*)?END Quiz\s*$",
            r"^(?:#+\s*)?SelfCheck\s*$",
            r"^(?:#+\s*)?END SelfCheck\s*$",
            r"^(?:#+\s*)?Callout\s*::",
            r"^(?:#+\s*)?END Callout\s*$",
            r"^(?:#+\s*)?Image\s*::",
            r"^(?:#+\s*)?END Image\s*$",
            r"^(?:#+\s*)?File\s*::",
            r"^(?:#+\s*)?END File\s*$",
            r"^(?:#+\s*)?YouTubeEmbed\s*::",
            r"^(?:#+\s*)?PanoptoEmbed\s*::",
            r"^(?:#+\s*)?HTML Embed\s*::",
            r"^(?:#+\s*)?END HTML Embed\s*$",
        ]
    )


def extract_youtube_id(url: str) -> str | None:
    """Extract a YouTube video ID from common YouTube URL formats."""
    url = url.strip()

    if "youtu.be/" in url:
        return url.split("youtu.be/")[-1].split("?")[0]

    if "youtube.com" in url:
        parsed = urlparse(url)
        return parse_qs(parsed.query).get("v", [None])[0]

    return None


def extract_panopto_id(url: str) -> str | None:
    """Extract the Panopto video/session id from a Panopto Viewer URL."""
    match = re.search(r"[?&]id=([a-zA-Z0-9\-]+)", url)
    return match.group(1) if match else None


def render_youtube_iframe(url: str) -> str:
    """Render a standard YouTube embed iframe from a URL."""
    video_id = extract_youtube_id(url)
    if not video_id:
        return f"<!-- Invalid YouTube URL: {url} -->"

    return (
        f'<iframe width="560" height="315" '
        f'src="https://www.youtube.com/embed/{video_id}" '
        f'title="YouTube video player" frameborder="0" '
        f'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" '
        f'referrerpolicy="strict-origin-when-cross-origin" '
        f'allowfullscreen></iframe>'
    )


def render_panopto_iframe(url: str) -> str:
    """Render a Panopto embed iframe from a Panopto Viewer URL."""
    video_id = extract_panopto_id(url)
    if not video_id:
        return f"<!-- Invalid Panopto URL: {url} -->"

    parsed = urlparse(url)
    embed_url = f"{parsed.scheme}://{parsed.netloc}/Panopto/Pages/Embed.aspx?id={video_id}"

    return (
        f'<iframe src="{embed_url}" title="Panopto video player" width="720" height="405" '
        f'frameborder="0" allowfullscreen></iframe>'
    )


def validate_import_content(content: str, page_id: str = "", project_root: Path | None = None) -> list[str]:
    """
    Lightweight validation for common authoring mistakes.
    Returns warnings only; does not block import.
    """
    # Validate the same normalized representation consumed by the parsers.
    # This prevents Word/Pandoc hard-line-break markers from hiding directives.
    content = normalize_metadata_blocks(content)
    warnings = []
    lines = content.split("\n")
    project_root = project_root or Path(".")

    quiz_open = False
    quiz_start_line = None
    quiz_has_question = False
    quiz_option_count = 0
    quiz_has_answer = False
    quiz_type = "single"
    quiz_answers = []
    quiz_options = []
    bounded_blocks = {
        "callout": "Callout",
        "reveal": "Reveal",
        "selfcheck": "SelfCheck",
        "tabs": "Tabs",
        "quiz": "Quiz",
        "r code": "R Code",
        "r example": "R Example",
        "image": "Image",
        "file": "File",
        "html embed": "HTML Embed",
    }
    block_stack = []

    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        if not line:
            continue

        end_match = re.match(
            r"^(?:#+\s*)?END\s+(Callout|Reveal|SelfCheck|Tabs|Quiz|R Code|R Example|Image|File|HTML Embed)\s*$",
            line,
            re.IGNORECASE,
        )
        if end_match:
            end_name = end_match.group(1).lower()
            if not block_stack:
                warnings.append(f"{page_id} line {idx}: END {end_match.group(1)} has no matching opening tag")
            elif block_stack[-1][0] != end_name:
                expected = bounded_blocks[block_stack[-1][0]]
                warnings.append(
                    f"{page_id} line {idx}: END {end_match.group(1)} does not match open {expected} "
                    f"block from line {block_stack[-1][1]}"
                )
            else:
                block_stack.pop()
            if end_name == "quiz" and quiz_open:
                if not quiz_has_question:
                    warnings.append(f"{page_id} line {quiz_start_line}: Quiz block missing Question ::")
                if quiz_option_count < 2:
                    warnings.append(f"{page_id} line {quiz_start_line}: Quiz block has fewer than 2 Option :: lines")
                if not quiz_has_answer:
                    warnings.append(f"{page_id} line {quiz_start_line}: Quiz block missing Answer ::")
                for answer in quiz_answers:
                    if answer.casefold() not in {option.casefold() for option in quiz_options}:
                        warnings.append(
                            f"{page_id} line {quiz_start_line}: Answer '{answer}' does not match an Option :: value"
                        )
                if quiz_type == "single" and len(quiz_answers) > 1:
                    warnings.append(
                        f"{page_id} line {quiz_start_line}: single-select Quiz has more than one Answer ::; "
                        "use Type :: multiple"
                    )
                quiz_open = False
                quiz_start_line = None
            continue

        opener_match = re.match(
            r"^(?:#+\s*)?(Callout\s*::\s*.+|Reveal|SelfCheck|Tabs|Quiz|R Code|R Example|Image\s*::\s*.+|File\s*::\s*.+|HTML Embed\s*::\s*.+)\s*$",
            line,
            re.IGNORECASE,
        )
        if opener_match:
            opener = opener_match.group(1)
            name = re.split(r"\s*::", opener, maxsplit=1)[0].strip().lower()
            block_stack.append((name, idx))

        malformed_match = re.match(
            r"^(YouTubeEmbed|PanoptoEmbed|HTML Embed|Image|File|Callout|Title|Question|Type|Option|Answer|Correct|Feedback|Hint|Explanation|Caption|Alt|Width|Height|Fallback Image|Display|Label|R Mode|Echo|Output)\s*:\s+\S+",
            line,
            re.IGNORECASE,
        )
        if malformed_match:
            warnings.append(f"{page_id} line {idx}: possible directive syntax error. Use '::' not ':'.")

        r_mode_match = re.match(r"^R Mode\s*::\s*(.+)$", line, re.IGNORECASE)
        if r_mode_match:
            mode = r_mode_match.group(1).strip().rstrip("\\").strip().lower()
            if mode not in ["static", "r", "webr"]:
                warnings.append(
                    f"{page_id} line {idx}: unknown R Mode '{mode}'. Use 'static' or 'webr'."
                )

        echo_match = re.match(r"^Echo\s*::\s*(.+)$", line, re.IGNORECASE)
        if echo_match:
            echo_value = echo_match.group(1).strip().rstrip("\\").strip().lower()
            if echo_value not in ["true", "false", "yes", "no"]:
                warnings.append(
                    f"{page_id} line {idx}: unknown Echo value '{echo_value}'. Use 'true' or 'false'."
                )

        output_match = re.match(r"^Output\s*::\s*(.+)$", line, re.IGNORECASE)
        if output_match:
            output_value = output_match.group(1).strip().rstrip("\\").strip().lower()
            if output_value not in ["true", "false", "yes", "no"]:
                warnings.append(
                    f"{page_id} line {idx}: unknown Output value '{output_value}'. Use 'true' or 'false'."
                )

        if re.match(r"^(?:#+\s*)?Quiz\s*$", line, re.IGNORECASE):
            if quiz_open:
                if not quiz_has_question:
                    warnings.append(f"{page_id} line {idx}: previous Quiz block missing Question ::")
                if quiz_option_count < 2:
                    warnings.append(f"{page_id} line {idx}: previous Quiz block has fewer than 2 Option :: lines")
                if not quiz_has_answer:
                    warnings.append(f"{page_id} line {idx}: previous Quiz block missing Answer ::")

            quiz_open = True
            quiz_start_line = idx
            quiz_has_question = False
            quiz_option_count = 0
            quiz_has_answer = False
            quiz_type = "single"
            quiz_answers = []
            quiz_options = []
            continue

        if quiz_open:
            if re.match(r"^Question\s*::\s*(.+)$", line, re.IGNORECASE):
                quiz_has_question = True
            elif re.match(r"^Option\s*::\s*(.+)$", line, re.IGNORECASE):
                quiz_option_count += 1
                quiz_options.append(re.match(r"^Option\s*::\s*(.+)$", line, re.IGNORECASE).group(1).strip())
            elif re.match(r"^(?:#+\s*)?Option\s*$", line, re.IGNORECASE):
                quiz_option_count += 1
            elif re.match(r"^Answer\s*::\s*(.+)$", line, re.IGNORECASE):
                quiz_has_answer = True
                quiz_answers.append(re.match(r"^Answer\s*::\s*(.+)$", line, re.IGNORECASE).group(1).strip())
            elif re.match(r"^Correct\s*::\s*(yes|true|correct|1)\s*$", line, re.IGNORECASE):
                quiz_has_answer = True
            elif re.match(r"^Type\s*::\s*(.+)$", line, re.IGNORECASE):
                quiz_type = re.match(r"^Type\s*::\s*(.+)$", line, re.IGNORECASE).group(1).strip().lower()
                if quiz_type not in {"single", "multiple"}:
                    warnings.append(
                        f"{page_id} line {idx}: unknown Quiz Type '{quiz_type}'. Use 'single' or 'multiple'."
                    )

        yt_match = re.match(r"^(?:#+\s*)?YouTubeEmbed\s*::\s*(.+)$", line, re.IGNORECASE)
        if yt_match:
            url = yt_match.group(1).strip()
            if not extract_youtube_id(url):
                warnings.append(f"{page_id} line {idx}: invalid YouTube URL")

        pan_match = re.match(r"^(?:#+\s*)?PanoptoEmbed\s*::\s*(.+)$", line, re.IGNORECASE)
        if pan_match:
            url = pan_match.group(1).strip()
            if not extract_panopto_id(url):
                warnings.append(f"{page_id} line {idx}: invalid Panopto URL")

        img_match = re.match(r"^(?:#+\s*)?Image\s*::\s*(.+)$", line, re.IGNORECASE)
        if img_match:
            raw_path = img_match.group(1).strip().replace("\\", "/")
            if raw_path.startswith("resources/") and not (project_root / raw_path).exists():
                warnings.append(f"{page_id} line {idx}: image path not found: {raw_path}")

        file_match = re.match(r"^(?:#+\s*)?File\s*::\s*(.+)$", line, re.IGNORECASE)
        if file_match:
            raw_path = file_match.group(1).strip().replace("\\", "/")
            if raw_path.startswith("resources/") and not (project_root / raw_path).exists():
                warnings.append(f"{page_id} line {idx}: file path not found: {raw_path}")

        html_match = re.match(
            r"^(?:#+\s*)?HTML Embed\s*::\s*(.+)$",
            line,
            re.IGNORECASE,
        )
        if html_match:
            raw_path = html_match.group(1).strip().replace("\\", "/")
            path_parts = Path(raw_path).parts
            if (
                not raw_path.startswith("resources/html/")
                or Path(raw_path).suffix.lower() not in {".html", ".htm"}
                or ".." in path_parts
                or Path(raw_path).is_absolute()
            ):
                warnings.append(
                    f"{page_id} line {idx}: HTML Embed must reference a local "
                    "resources/html/*.html file"
                )
            elif not (project_root / raw_path).is_file():
                warnings.append(
                    f"{page_id} line {idx}: HTML Embed source not found: {raw_path}"
                )

        height_match = re.match(r"^Height\s*::\s*(.+)$", line, re.IGNORECASE)
        if height_match:
            height_value = height_match.group(1).strip()
            if not height_value.isdigit() or not 300 <= int(height_value) <= 2000:
                warnings.append(
                    f"{page_id} line {idx}: Height must be a whole number "
                    "between 300 and 2000"
                )

        fallback_match = re.match(
            r"^Fallback Image\s*::\s*(.+)$",
            line,
            re.IGNORECASE,
        )
        if fallback_match:
            fallback_path = fallback_match.group(1).strip().replace("\\", "/")
            if fallback_path.startswith("resources/") and not (
                project_root / fallback_path
            ).is_file():
                warnings.append(
                    f"{page_id} line {idx}: fallback image not found: {fallback_path}"
                )

    if quiz_open:
        if not quiz_has_question:
            warnings.append(f"{page_id} line {quiz_start_line}: Quiz block missing Question ::")
        if quiz_option_count < 2:
            warnings.append(f"{page_id} line {quiz_start_line}: Quiz block has fewer than 2 Option :: lines")
        if not quiz_has_answer:
            warnings.append(f"{page_id} line {quiz_start_line}: Quiz block missing Answer ::")

    for name, start_line in block_stack:
        warnings.append(
            f"{page_id} line {start_line}: {bounded_blocks[name]} block has no explicit "
            f"END {bounded_blocks[name]} tag"
        )

    return warnings


def print_validation_warnings(warnings: list[str]):
    if warnings:
        click.echo(click.style("Validation warnings:", fg="yellow"))
        for warning in warnings:
            click.echo(click.style(f"  - {warning}", fg="yellow"))


def parse_r_example(content: str) -> tuple[str, int]:
    """
    Detect 'R Example' sections and render them as non-executing
    display-only R code blocks.

    Preferred syntax:

    R Example
    <R code>
    END R Example
    """
    lines = content.split("\n")
    new_lines = []
    count = 0

    in_code_block = False
    code_lines = []

    def flush_code_block():
        nonlocal code_lines, new_lines
        cleaned_code = clean_r_code("\n".join(code_lines))
        new_lines.append("```r")
        if cleaned_code:
            new_lines.append(cleaned_code)
        new_lines.append("```")
        code_lines = []

    for line in lines:
        stripped = line.strip()

        if not in_code_block:
            if re.match(r"^(?:#+\s*)?R Example\s*$", stripped, re.IGNORECASE):
                in_code_block = True
                count += 1
                code_lines = []
                continue
            else:
                new_lines.append(line)
        else:
            if re.match(r"^END\s+R\s+Example\s*$", stripped.strip(), re.IGNORECASE):
                flush_code_block()
                in_code_block = False
                continue

            if is_markdown_heading(line) or (
                is_interaction_header(line)
                and not re.match(r"^(?:#+\s*)?R Example\s*$", stripped, re.IGNORECASE)
            ):
                flush_code_block()
                new_lines.append("")
                new_lines.append(line)
                in_code_block = False
            else:
                # Accept the same display metadata authors may use in R Code
                # blocks, but do not print it as part of a static R example.
                if re.match(
                    r"^(R Mode|Echo|Output|Alt|Caption)\s*::",
                    stripped,
                    re.IGNORECASE,
                ):
                    continue
                if stripped not in ["{r}", "`{r}`", "```{r}", "```", "```r"]:
                    code_lines.append(line)

    if in_code_block:
        flush_code_block()

    if count > 0:
        click.echo(click.style("Detected R example blocks", fg="blue"))
        click.echo(f"  Rendering {count} non-executing R examples")

    return "\n".join(new_lines), count


def parse_r_code(content: str) -> tuple[str, int]:
    """
    Detect 'R Code' sections and wrap subsequent lines into executable
    Quarto fenced R code blocks.

    Preferred syntax:

    R Code
    R Mode :: static
    Echo :: true
    Output :: true
    Alt :: Description of generated figure
    Caption :: Visible figure caption
    <R code>
    END R Code

    R Mode options:
    - static/default/r -> ```{r}
    - webr -> ```{webr-r}

    Echo options:
    - true/default -> show code
    - false -> hide code

    Output options:
    - true/default -> execute code and show generated output
    - false -> do not execute code; useful for code-only examples
    """
    lines = content.split("\n")
    new_lines = []
    count = 0

    in_code_block = False
    code_lines = []
    fig_alt = ""
    fig_cap = ""
    r_mode = "static"
    echo = "true"
    output = "true"

    def escape_chunk_option_text(text: str) -> str:
        return text.replace("\\", "\\\\").replace('"', '\\"')

    def normalize_bool(value: str, default: str = "true") -> str:
        value = (value or default).strip().rstrip("\\").strip().lower()
        if value in ["false", "no"]:
            return "false"
        if value in ["true", "yes"]:
            return "true"
        return default

    def flush_code_block():
        nonlocal code_lines, new_lines, fig_alt, fig_cap, r_mode, echo, output

        cleaned_code = clean_r_code("\n".join(code_lines))
        chunk_engine = "webr-r" if r_mode.lower() == "webr" else "r"
        echo_value = normalize_bool(echo, default="true")
        output_value = normalize_bool(output, default="true")

        new_lines.append(f"```{{{chunk_engine}}}")

        # Standard R chunks support Quarto execution/display metadata.
        # WebR blocks are kept simpler so learners can edit/run directly in the browser.
        if chunk_engine == "r":
            new_lines.append(f"#| echo: {echo_value}")

            # Output :: false is used for code-only examples.
            # Using eval: false prevents charts/tables/results from being generated.
            if output_value == "false":
                new_lines.append("#| eval: false")

            if fig_alt:
                new_lines.append(f'#| fig-alt: "{escape_chunk_option_text(fig_alt)}"')
            if fig_cap:
                new_lines.append(f'#| fig-cap: "{escape_chunk_option_text(fig_cap)}"')

        if cleaned_code:
            new_lines.append(cleaned_code)

        new_lines.append("```")

        code_lines = []
        fig_alt = ""
        fig_cap = ""
        r_mode = "static"
        echo = "true"
        output = "true"

    for line in lines:
        stripped = line.strip()

        if not in_code_block:
            if re.match(r"^(?:#+\s*)?R Code\s*$", stripped, re.IGNORECASE):
                in_code_block = True
                count += 1
                code_lines = []
                fig_alt = ""
                fig_cap = ""
                r_mode = "static"
                echo = "true"
                output = "true"
                continue
            else:
                new_lines.append(line)
        else:
            if re.match(r"^(?:#+\s*)?END R Code\s*$", stripped, re.IGNORECASE):
                flush_code_block()
                in_code_block = False
                continue

            if is_markdown_heading(line) or (
                is_interaction_header(line)
                and not re.match(r"^(?:#+\s*)?R Code\s*$", stripped, re.IGNORECASE)
            ):
                flush_code_block()
                new_lines.append("")
                new_lines.append(line)
                in_code_block = False
            else:
                mode_match = re.match(r"^R Mode\s*::\s*(.*)$", stripped, re.IGNORECASE)
                echo_match = re.match(r"^Echo\s*::\s*(.*)$", stripped, re.IGNORECASE)
                output_match = re.match(r"^Output\s*::\s*(.*)$", stripped, re.IGNORECASE)
                alt_match = re.match(r"^Alt\s*::\s*(.*)$", stripped, re.IGNORECASE)
                cap_match = re.match(r"^Caption\s*::\s*(.*)$", stripped, re.IGNORECASE)

                if mode_match:
                    r_mode = mode_match.group(1).strip().rstrip("\\").strip().lower()
                elif echo_match:
                    echo = echo_match.group(1).strip().rstrip("\\").strip().lower()
                elif output_match:
                    output = output_match.group(1).strip().rstrip("\\").strip().lower()
                elif alt_match:
                    fig_alt = alt_match.group(1).strip()
                elif cap_match:
                    fig_cap = cap_match.group(1).strip()
                elif stripped not in ["{r}", "`{r}`", "```{r}", "```{webr-r}", "```"]:
                    code_lines.append(line)

    if in_code_block:
        flush_code_block()

    if count > 0:
        click.echo(click.style("Detected R code blocks", fg="blue"))
        click.echo(f"  Rendering {count} fenced code chunks")

    return "\n".join(new_lines), count

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


def parse_quiz(content: str) -> tuple[str, int]:
    """
    Render accessible single- or multiple-select quizzes with answer checking.

    Type :: defaults to single for backwards compatibility. Repeated Answer ::
    lines define the correct set for simple Option :: choices. Rich choices use
    bounded Option/END Option blocks with Correct :: and optional Feedback ::.
    Hint :: is optional.
    Explanation :: begins rich explanation content; subsequent paragraphs,
    lists, tables and equations are preserved until END Quiz.
    """
    lines = content.split("\n")
    new_lines = []
    count = 0
    i = 0
    quiz_index = 0

    def esc(text: str) -> str:
        return (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
        )

    while i < len(lines):
        stripped = lines[i].strip()

        if not re.match(r"^(?:#+\s*)?Quiz\s*$", stripped, re.IGNORECASE):
            new_lines.append(lines[i])
            i += 1
            continue

        question = ""
        options = []
        quiz_type = "single"
        answers = []
        hint = ""
        explanation_lines = []
        explanation_started = False
        i += 1
        quiz_index += 1
        quiz_name = f"quiz_{quiz_index}"
        found_end = False

        while i < len(lines):
            current_line = lines[i]
            s = current_line.strip()

            if re.match(r"^(?:#+\s*)?END Quiz\s*$", s, re.IGNORECASE):
                found_end = True
                i += 1
                break

            q_match = re.match(r"^Question\s*::\s*(.*)$", s, re.IGNORECASE)
            t_match = re.match(r"^Type\s*::\s*(.*)$", s, re.IGNORECASE)
            o_match = re.match(r"^Option\s*::\s*(.*)$", s, re.IGNORECASE)
            a_match = re.match(r"^Answer\s*::\s*(.*)$", s, re.IGNORECASE)
            h_match = re.match(r"^Hint\s*::\s*(.*)$", s, re.IGNORECASE)
            e_match = re.match(r"^Explanation\s*::\s*(.*)$", s, re.IGNORECASE)

            if re.match(r"^(?:#+\s*)?Option\s*$", s, re.IGNORECASE):
                option_content = []
                option_feedback = []
                option_correct = False
                feedback_started = False
                option_found_end = False
                i += 1

                while i < len(lines):
                    option_line = lines[i]
                    option_s = option_line.strip()

                    if re.match(r"^(?:#+\s*)?END Option\s*$", option_s, re.IGNORECASE):
                        option_found_end = True
                        i += 1
                        break
                    if re.match(r"^(?:#+\s*)?END Quiz\s*$", option_s, re.IGNORECASE):
                        break

                    correct_match = re.match(r"^Correct\s*::\s*(.*)$", option_s, re.IGNORECASE)
                    feedback_match = re.match(r"^Feedback\s*::\s*(.*)$", option_s, re.IGNORECASE)
                    text_match = re.match(r"^Text\s*::\s*(.*)$", option_s, re.IGNORECASE)

                    if (
                        correct_match
                        and not any(line.strip() for line in option_content)
                        and not feedback_started
                    ):
                        option_correct = correct_match.group(1).strip().lower() in {
                            "yes", "true", "correct", "1"
                        }
                    elif feedback_match:
                        feedback_started = True
                        option_feedback.append(feedback_match.group(1).strip())
                    elif feedback_started:
                        option_feedback.append(option_line)
                    elif text_match:
                        option_content.append(text_match.group(1).strip())
                    else:
                        option_content.append(option_line)
                    i += 1

                while option_content and not option_content[0].strip():
                    option_content.pop(0)
                while option_content and not option_content[-1].strip():
                    option_content.pop()
                while option_feedback and not option_feedback[0].strip():
                    option_feedback.pop(0)
                while option_feedback and not option_feedback[-1].strip():
                    option_feedback.pop()

                options.append({
                    "content": option_content,
                    "plain_text": " ".join(line.strip() for line in option_content if line.strip()),
                    "correct": option_correct,
                    "feedback": option_feedback,
                    "rich": True,
                })
                if not option_found_end:
                    click.echo(
                        click.style(
                            "Warning: rich Option block has no END Option tag.",
                            fg="yellow",
                        )
                    )
                continue
            elif q_match:
                question = q_match.group(1).strip()
            elif t_match:
                candidate_type = t_match.group(1).strip().lower()
                quiz_type = candidate_type if candidate_type in {"single", "multiple"} else "single"
            elif o_match:
                option_text = o_match.group(1).strip()
                options.append({
                    "content": [option_text],
                    "plain_text": option_text,
                    "correct": False,
                    "feedback": [],
                    "rich": False,
                })
            elif a_match:
                answers.append(a_match.group(1).strip())
            elif h_match:
                hint = h_match.group(1).strip()
            elif e_match:
                explanation_started = True
                explanation_lines.append(e_match.group(1).strip())
            elif explanation_started:
                explanation_lines.append(current_line)

            i += 1

        new_lines.append("")
        new_lines.append("## Quiz")
        new_lines.append("")

        if question:
            new_lines.append(question)
            new_lines.append("")

        if options:
            input_type = "checkbox" if quiz_type == "multiple" else "radio"
            instruction = "Select all that apply." if quiz_type == "multiple" else "Select one answer."
            correct_answers = {answer.casefold() for answer in answers}
            for option in options:
                if option["plain_text"].casefold() in correct_answers:
                    option["correct"] = True
            # Pandoc fenced divisions keep rich Markdown, equations and code
            # structurally valid in HTML, PDF and DOCX. Raw nested HTML divs
            # caused unclosed-Div warnings in combined handbooks.
            new_lines.append(
                f':::::: {{#{quiz_name} .quiz-block data-quiz-type="{quiz_type}"}}'
            )
            new_lines.append("")
            new_lines.append(f'*{instruction}*')
            new_lines.append("")
            for idx, option in enumerate(options, start=1):
                option_id = f"{quiz_name}_opt_{idx}"
                content_id = f"{option_id}_content"
                is_correct = "true" if option["correct"] else "false"
                new_lines.append('::::: {.quiz-option}')
                new_lines.append(':::: {.quiz-option-control}')
                new_lines.append(
                    f'<input type="{input_type}" id="{option_id}" name="{quiz_name}" '
                    f'data-correct="{is_correct}" aria-labelledby="{content_id}">'
                )
                new_lines.append("")
                if option["rich"]:
                    new_lines.append(
                        f'::: {{#{content_id} .quiz-option-content data-for="{option_id}"}}'
                    )
                    new_lines.append("")
                    new_lines.extend(option["content"])
                    new_lines.append("")
                    new_lines.append(':::')
                else:
                    new_lines.append(
                        f'<label id="{content_id}" class="quiz-option-content" '
                        f'for="{option_id}">{esc(option["plain_text"])}</label>'
                    )
                new_lines.append("")
                new_lines.append('::::')
                if option["feedback"]:
                    new_lines.append(':::: {.quiz-option-feedback hidden="hidden"}')
                    new_lines.append("")
                    new_lines.extend(option["feedback"])
                    new_lines.append("")
                    new_lines.append('::::')
                new_lines.append(':::::')
                new_lines.append("")
            new_lines.append(
                '<p class="quiz-actions">'
                '<button type="button" class="quiz-check">Check answer</button> '
                '<button type="reset" class="quiz-reset">Try again</button>'
                '</p>'
            )
            new_lines.append('<p class="quiz-feedback" role="status" aria-live="polite"></p>')
            new_lines.append("")
            new_lines.append('::::: {.quiz-explanation hidden="hidden"}')
            new_lines.append("")
            if explanation_lines:
                new_lines.append("**Explanation:**")
                new_lines.append("")
                while explanation_lines and not explanation_lines[0].strip():
                    explanation_lines.pop(0)
                while explanation_lines and not explanation_lines[-1].strip():
                    explanation_lines.pop()
                new_lines.extend(explanation_lines)
            new_lines.append("")
            new_lines.append(':::::')
            new_lines.append("")
            new_lines.append('::::::')
            new_lines.append("")

        if hint:
            new_lines.append('<details class="quiz-hint">')
            new_lines.append('<summary><strong>Show hint</strong></summary>')
            new_lines.append(f'<p>{esc(hint)}</p>')
            new_lines.append('</details>')
            new_lines.append("")

        if options:
            new_lines.extend([
                "<script>",
                "(() => {",
                f"  const quiz = document.getElementById('{quiz_name}');",
                "  if (!quiz) return;",
                "  const feedback = quiz.querySelector('.quiz-feedback');",
                "  const explanation = quiz.querySelector('.quiz-explanation');",
                "  quiz.querySelectorAll('.quiz-option-content[data-for]').forEach(content => {",
                "    content.addEventListener('click', () => {",
                "      const input = document.getElementById(content.dataset.for);",
                "      if (input.type === 'radio') input.checked = true;",
                "      else input.checked = !input.checked;",
                "    });",
                "  });",
                "  quiz.querySelector('.quiz-check').addEventListener('click', () => {",
                "    const inputs = [...quiz.querySelectorAll('input')];",
                "    const selected = inputs.filter(input => input.checked);",
                "    if (selected.length === 0) {",
                "      feedback.textContent = 'Please select an answer before checking.';",
                "      feedback.className = 'quiz-feedback quiz-unanswered';",
                "      explanation.hidden = true;",
                "      return;",
                "    }",
                "    const correct = inputs.every(input => input.checked === (input.dataset.correct === 'true'));",
                "    feedback.textContent = correct ? 'Correct.' : 'Not quite. Review your selection and try again.';",
                "    feedback.className = `quiz-feedback ${correct ? 'quiz-correct' : 'quiz-incorrect'}`;",
                "    quiz.querySelectorAll('.quiz-option').forEach(option => {",
                "      const input = option.querySelector('input');",
                "      const optionFeedback = option.querySelector('.quiz-option-feedback');",
                "      if (optionFeedback) optionFeedback.hidden = !input.checked;",
                "    });",
                "    explanation.hidden = false;",
                "  });",
                "  quiz.querySelector('.quiz-reset').addEventListener('click', () => {",
                "    quiz.querySelectorAll('input').forEach(input => { input.checked = false; });",
                "    feedback.textContent = '';",
                "    feedback.className = 'quiz-feedback';",
                "    explanation.hidden = true;",
                "    quiz.querySelectorAll('.quiz-option-feedback').forEach(item => { item.hidden = true; });",
                "  });",
                "})();",
                "</script>",
                "<style>",
                ".quiz-block { border: 1px solid #d9d9d9; border-radius: .4rem; padding: 1rem; margin: 1rem 0; }",
                ".quiz-option { border-radius: .25rem; margin: .5rem 0; padding: .35rem; }",
                ".quiz-option-control { align-items: flex-start; display: flex; gap: .6rem; }",
                ".quiz-option-control input { flex: 0 0 auto; margin-top: .35rem; }",
                ".quiz-option-content { cursor: pointer; flex: 1 1 auto; }",
                ".quiz-option-content > :last-child { margin-bottom: 0; }",
                ".quiz-option-feedback { background: #f5f5f5; border-left: .2rem solid #6c757d; margin: .5rem 0 0 1.5rem; padding: .5rem .75rem; }",
                ".quiz-actions { margin: 1rem 0 .5rem; }",
                ".quiz-feedback { font-weight: 600; min-height: 1.5em; }",
                ".quiz-correct { color: #137333; }",
                ".quiz-incorrect, .quiz-unanswered { color: #b3261e; }",
                ".quiz-explanation { border-left: .25rem solid #6c757d; margin-top: .75rem; padding-left: .75rem; }",
                ".quiz-hint { margin: .75rem 0 1rem; }",
                "</style>",
                "",
            ])
        count += 1

        if not found_end:
            click.echo(
                click.style(
                    "Warning: Quiz block has no END Quiz tag; "
                    "content continued to the end of the document.",
                    fg="yellow",
                )
            )

    if count > 0:
        click.echo(click.style("Detected quiz blocks", fg="blue"))
        click.echo(f"  Rendering {count} interactive quiz blocks")

    return "\n".join(new_lines), count


def parse_html_embeds(
    content: str,
    qmd_path: Path,
    course_dir: Path,
) -> tuple[str, int]:
    """Render trusted, local, standalone HTML activities in accessible iframes."""
    lines = content.split("\n")
    new_lines = []
    count = 0
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()
        match = re.match(
            r"^(?:#+\s*)?HTML Embed\s*::\s*(.+)$",
            stripped,
            re.IGNORECASE,
        )

        if not match:
            new_lines.append(lines[i])
            i += 1
            continue

        raw_path = match.group(1).strip().replace("\\", "/")
        path_object = Path(raw_path)
        if (
            not raw_path.startswith("resources/html/")
            or path_object.suffix.lower() not in {".html", ".htm"}
            or ".." in path_object.parts
            or path_object.is_absolute()
        ):
            raise ValueError(
                "HTML Embed must reference a trusted local file under "
                f"resources/html/: {raw_path}"
            )
        source_file = course_dir / raw_path
        if not source_file.is_file():
            raise FileNotFoundError(f"HTML Embed source not found: {source_file}")

        title = path_object.stem.replace("_", " ").replace("-", " ").strip()
        height = 700
        fallback_image = ""
        found_end = False
        i += 1

        while i < len(lines):
            current_line = lines[i]
            current_text = current_line.strip()

            if re.match(
                r"^(?:#+\s*)?END HTML Embed\s*$",
                current_text,
                re.IGNORECASE,
            ):
                found_end = True
                i += 1
                break

            if is_markdown_heading(current_line) or is_interaction_header(current_line):
                break

            title_match = re.match(
                r"^Title\s*::\s*(.*)$",
                current_text,
                re.IGNORECASE,
            )
            height_match = re.match(
                r"^Height\s*::\s*(.*)$",
                current_text,
                re.IGNORECASE,
            )
            fallback_match = re.match(
                r"^Fallback Image\s*::\s*(.*)$",
                current_text,
                re.IGNORECASE,
            )

            if title_match and title_match.group(1).strip():
                title = title_match.group(1).strip()
            elif height_match:
                height_value = height_match.group(1).strip()
                if height_value.isdigit() and 300 <= int(height_value) <= 2000:
                    height = int(height_value)
            elif fallback_match:
                fallback_image = fallback_match.group(1).strip().replace("\\", "/")

            i += 1

        if not found_end:
            click.echo(
                click.style(
                    "Warning: HTML Embed block has no END HTML Embed tag.",
                    fg="yellow",
                )
            )

        path = rewrite_asset_path(raw_path, qmd_path, course_dir)
        safe_path = html.escape(path, quote=True)
        safe_title = html.escape(title, quote=True)
        link_label = title.replace("[", "\\[").replace("]", "\\]")

        new_lines.append('::: {.content-visible when-format="html"}')
        new_lines.append("")
        new_lines.append(
            f'<iframe class="html-embed" src="{safe_path}" '
            f'title="{safe_title}" width="100%" height="{height}" '
            f'style="border: 0;" '
            f'loading="lazy" sandbox="allow-scripts allow-downloads" '
            f'referrerpolicy="no-referrer"></iframe>'
        )
        new_lines.append("")
        new_lines.append(
            f'[{link_label} — open in a new window]({path})'
            '{target="_blank" rel="noopener"}'
        )
        new_lines.append("")
        new_lines.append(":::")
        new_lines.append("")

        new_lines.append('::: {.content-visible unless-format="html"}')
        new_lines.append("")
        if fallback_image:
            fallback_object = Path(fallback_image)
            if (
                not fallback_image.startswith("resources/images/")
                or fallback_object.suffix.lower()
                not in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
                or ".." in fallback_object.parts
                or fallback_object.is_absolute()
            ):
                raise ValueError(
                    "Fallback Image must reference a local image under "
                    f"resources/images/: {fallback_image}"
                )
            fallback_source = course_dir / fallback_image
            if not fallback_source.is_file():
                raise FileNotFoundError(
                    f"HTML Embed fallback image not found: {fallback_source}"
                )
            fallback_path = rewrite_asset_path(fallback_image, qmd_path, course_dir)
            new_lines.append(f"![{link_label}]({fallback_path})")
            new_lines.append("")
        new_lines.append(f"[{link_label} — open the interactive version]({path})")
        new_lines.append("")
        new_lines.append(":::")
        new_lines.append("")
        count += 1

    if count > 0:
        click.echo(click.style("Detected HTML embeds", fg="blue"))
        click.echo(f"  Rendering {count} standalone HTML interaction(s)")

    return "\n".join(new_lines), count


def parse_images(content: str, qmd_path: Path, course_dir: Path) -> tuple[str, int]:
    """Render Image blocks, preferring END Image and retaining legacy implicit endings."""
    lines = content.split("\n")
    new_lines = []
    count = 0
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()
        match = re.match(r"^(?:#+\s*)?Image\s*::\s*(.+)$", stripped, re.IGNORECASE)

        if not match:
            new_lines.append(lines[i])
            i += 1
            continue

        raw_path = match.group(1).strip()
        path = rewrite_asset_path(raw_path, qmd_path, course_dir)
        alt = ""
        caption = ""
        width = ""
        i += 1

        while i < len(lines):
            s = lines[i].strip()
            if re.match(r"^(?:#+\s*)?END Image\s*$", s, re.IGNORECASE):
                i += 1
                break
            if is_markdown_heading(lines[i]) or is_interaction_header(lines[i]):
                break

            alt_match = re.match(r"^Alt\s*::\s*(.*)$", s, re.IGNORECASE)
            cap_match = re.match(r"^Caption\s*::\s*(.*)$", s, re.IGNORECASE)
            width_match = re.match(r"^Width\s*::\s*(.*)$", s, re.IGNORECASE)

            if alt_match:
                alt = alt_match.group(1).strip()
            elif cap_match:
                caption = cap_match.group(1).strip()
            elif width_match:
                width = width_match.group(1).strip()

            i += 1

        visible_caption = caption or ""
        image_line = f"![{visible_caption}]({path})"

        attributes = []
        if width:
            attributes.append(f"width='{width}'")
        if alt:
            attributes.append(f'fig-alt="{alt}"')

        if attributes:
            image_line += "{" + " ".join(attributes) + "}"

        new_lines.append(image_line)
        new_lines.append("")
        count += 1

    if count > 0:
        click.echo(click.style("Detected image blocks", fg="blue"))
        click.echo(f"  Rendering {count} images")

    return "\n".join(new_lines), count


def parse_files(content: str, qmd_path: Path, course_dir: Path) -> tuple[str, int]:
    """Render File blocks, preferring END File and retaining legacy implicit endings."""
    lines = content.split("\n")
    new_lines = []
    count = 0
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()
        match = re.match(r"^(?:#+\s*)?File\s*::\s*(.+)$", stripped, re.IGNORECASE)

        if not match:
            new_lines.append(lines[i])
            i += 1
            continue

        raw_path = match.group(1).strip()
        path = rewrite_asset_path(raw_path, qmd_path, course_dir)
        label = "Download file"
        display = ""
        i += 1

        while i < len(lines):
            s = lines[i].strip()
            if re.match(r"^(?:#+\s*)?END File\s*$", s, re.IGNORECASE):
                i += 1
                break
            if is_markdown_heading(lines[i]) or is_interaction_header(lines[i]):
                break

            label_match = re.match(r"^Label\s*::\s*(.*)$", s, re.IGNORECASE)
            display_match = re.match(r"^Display\s*::\s*(.*)$", s, re.IGNORECASE)

            if label_match:
                label = label_match.group(1).strip()
            elif display_match:
                display = display_match.group(1).strip().lower()

            i += 1

        if display == "embed" and path.lower().endswith(".pdf"):
            iframe_title = f"Embedded PDF: {label}" if label else "Embedded PDF document"
            new_lines.append(
                f'<iframe src="{path}" title="{iframe_title}" width="100%" height="600" loading="lazy"></iframe>'
            )
            new_lines.append("")
            new_lines.append(f"[{label}]({path})")
            new_lines.append("")
        else:
            new_lines.append(f"[{label}]({path})")
            new_lines.append("")

        count += 1

    if count > 0:
        click.echo(click.style("Detected file links", fg="blue"))
        click.echo(f"  Rendering {count} file links")

    return "\n".join(new_lines), count


def parse_embeds(content: str) -> tuple[str, int]:
    """
    Parse simple single-line embed directives:

    YouTubeEmbed :: <url>
    PanoptoEmbed :: <url>
    """
    lines = content.split("\n")
    new_lines = []
    count = 0

    for line in lines:
        stripped = line.strip()

        yt_match = re.match(r"^(?:#+\s*)?YouTubeEmbed\s*::\s*(.+)$", stripped, re.IGNORECASE)
        pan_match = re.match(r"^(?:#+\s*)?PanoptoEmbed\s*::\s*(.+)$", stripped, re.IGNORECASE)

        if yt_match:
            url = yt_match.group(1).strip()
            new_lines.append(render_youtube_iframe(url))
            new_lines.append("")
            count += 1
        elif pan_match:
            url = pan_match.group(1).strip()
            new_lines.append(render_panopto_iframe(url))
            new_lines.append("")
            count += 1
        else:
            new_lines.append(line)

    if count > 0:
        click.echo(click.style("Detected video embeds", fg="blue"))
        click.echo(f"  Rendering {count} YouTube/Panopto embeds")

    return "\n".join(new_lines), count


def parse_interactions(content: str, qmd_path: Path, course_dir: Path) -> str:
    """Coordinator function for parsing supported interaction types."""
    total_interactions = 0

    content = normalize_metadata_blocks(content)
    content = normalize_math_blocks(content)

    content, count = parse_tabs(content)
    total_interactions += count

    content, count = parse_r_example(content)
    total_interactions += count

    content, count = parse_r_code(content)
    total_interactions += count

    content, count = parse_callouts(content)
    total_interactions += count

    content, count = parse_selfcheck(content)
    total_interactions += count

    content, count = parse_reveal(content)
    total_interactions += count

    content, count = parse_quiz(content)
    total_interactions += count

    content, count = parse_html_embeds(content, qmd_path, course_dir)
    total_interactions += count

    content, count = parse_images(content, qmd_path, course_dir)
    total_interactions += count

    content, count = parse_files(content, qmd_path, course_dir)
    total_interactions += count

    content, count = parse_embeds(content)
    total_interactions += count

    if total_interactions == 0:
        click.echo("  No interaction patterns detected")

    return content


def insert_markdown_into_qmd(md_path: Path, qmd_path: Path, course_dir: Path):
    """
    Inserts Markdown content into a QMD file.
    - Creates a .bak backup.
    - Uses IMPORT_START/END markers for idempotency.
    - If markers are missing, inserts after the frontmatter's second ---.
    """
    if not qmd_path.exists():
        raise FileNotFoundError(f"Target QMD file not found: {qmd_path}")

    with open(md_path, "r") as f:
        imported_content = f.read()

    imported_content = copy_imported_media_and_rewrite_paths(
        imported_content,
        md_path,
        qmd_path,
        course_dir,
    )

    imported_content = apply_following_alt_text_to_images(imported_content)

    imported_content = parse_interactions(imported_content, qmd_path, course_dir).strip()

    imported_content = re.sub(r"^\s*#\s+[^\n]*\n*", "", imported_content, count=1)
    imported_content = re.sub(r"^\s*Title:\s*[^\n]*\n*", "", imported_content, count=1, flags=re.IGNORECASE)
    imported_content = imported_content.strip()

    with open(qmd_path, "r") as f:
        qmd_content = f.read()

    backup_path = qmd_path.with_suffix(qmd_path.suffix + ".bak")
    shutil.copy2(qmd_path, backup_path)

    new_imported_block = f"\n\n{IMPORT_START}\n\n{imported_content}\n\n{IMPORT_END}\n"

    if IMPORT_START in qmd_content and IMPORT_END in qmd_content:
        pattern = re.escape(IMPORT_START) + r".*?" + re.escape(IMPORT_END)
        new_qmd_content = re.sub(
            pattern,
            lambda m: f"{IMPORT_START}\n\n{imported_content}\n\n{IMPORT_END}",
            qmd_content,
            flags=re.DOTALL,
        )
    else:
        fm_pattern = r"^---\s*\n.*?\n---\s*\n"
        fm_match = re.search(fm_pattern, qmd_content, re.DOTALL)

        if fm_match:
            insert_pos = fm_match.end()
            new_qmd_content = qmd_content[:insert_pos] + new_imported_block + qmd_content[insert_pos:]
        else:
            new_qmd_content = new_imported_block + qmd_content

    with open(qmd_path, "w") as f:
        f.write(new_qmd_content)


def _iter_pages(config):
    """Yield all effective pages in module order."""
    for session in config.sessions:
        for section in session.sections:
            for page in section.effective_pages:
                yield session, section, page

    # Course-level pages use the same import pipeline but do not belong to a
    # session or section. None placeholders preserve the existing tuple shape.
    for page in config.standalone_pages:
        yield None, None, page


def _find_target_qmd(course_dir: Path, page_id: str) -> Path | None:
    """Locate generated QMD file by page ID-derived filename."""
    target_qmd_name = f"{page_id}.qmd"
    for root, _, files in os.walk(course_dir):
        if target_qmd_name in files:
            return Path(root) / target_qmd_name
    return None


def run_import(config_path: str):
    """Orchestrates the import workflow using YAML-declared source_docx paths."""
    if not check_pandoc():
        click.echo(
            click.style("Pandoc is not installed. Please install Pandoc to use import-word.", fg="red"),
            err=True,
        )
        return

    try:
        config = ConfigLoader.load(config_path)
        course_id = config.module.id.lower()
        click.echo(f"Importing Word content for course: {course_id}")

        import_dir = Path("imports") / "courses" / course_id
        md_dir = import_dir / "md"
        md_dir.mkdir(parents=True, exist_ok=True)

        course_dir = Path("build") / "courses" / course_id
        if not course_dir.exists():
            parent = course_dir.parent
            options = [d for d in parent.iterdir() if d.is_dir() and d.name.startswith(course_id)] if parent.exists() else []
            if not options:
                click.echo(
                    click.style(f"Error: Course directory {course_dir} not found. Run 'build' first.", fg="red"),
                    err=True,
                )
                return
            course_dir = sorted(options)[-1]

        click.echo(f"Locating target files in: {course_dir}")

        copy_site_resources(course_dir)

        imported_count = 0
        skipped_count = 0
        webr_required = False
        html_resources_required = False

        for _, _, page in _iter_pages(config):
            if not getattr(page, "source_docx", None):
                skipped_count += 1
                click.echo(click.style(f"Skipping page '{page.id}' (no source_docx)", fg="yellow"))
                continue

            docx_path = Path(page.source_docx)

            if not docx_path.exists():
                skipped_count += 1
                click.echo(click.style(f"Warning: {docx_path} not found. Skipping page '{page.id}'.", fg="yellow"))
                continue

            md_path = md_dir / docx_path.with_suffix(".md").name

            click.echo(f"Converting {docx_path.name} to Markdown for page {page.id}")
            media_dir = convert_docx_to_md(docx_path, md_path)
            click.echo(f"  Saved to {md_path}")
            if media_dir.exists():
                media_count = len([
                    p for p in media_dir.rglob("*")
                    if p.is_file() and p.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"]
                ])
                if media_count:
                    click.echo(f"  Extracted {media_count} embedded media file(s) to {media_dir}")

            with open(md_path, "r") as f:
                raw_md = f.read()

            if contains_webr_directive(raw_md):
                webr_required = True

            if contains_html_embed_directive(raw_md):
                html_resources_required = True

            warnings = validate_import_content(raw_md, page.id, project_root=Path("."))
            print_validation_warnings(warnings)

            target_path = _find_target_qmd(course_dir, page.id)
            if target_path:
                click.echo(f"Inserting converted content into {target_path}")
                insert_markdown_into_qmd(md_path, target_path, course_dir)
                imported_count += 1
            else:
                skipped_count += 1
                click.echo(
                    click.style(f"Error: Target QMD for page '{page.id}' not found in {course_dir}.", fg="red")
                )

        if webr_required:
            click.echo(click.style("WebR content detected", fg="blue"))
            ensure_webr_support(course_dir)
        else:
            click.echo("No WebR content detected; WebR setup not required")

        if html_resources_required:
            click.echo(click.style("Standalone HTML content detected", fg="blue"))
            ensure_html_resources(course_dir)

        click.echo(click.style(f"✅ Import complete. Imported: {imported_count}, Skipped: {skipped_count}", fg="green"))

    except Exception as e:
        click.echo(click.style(f"Error: {str(e)}", fg="red"), err=True)
