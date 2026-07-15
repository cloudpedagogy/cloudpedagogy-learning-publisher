import os
import shutil
import subprocess
from pathlib import Path
import click
import re
from urllib.parse import urlparse, parse_qs
from ..core.config_loader import ConfigLoader

IMPORT_START = "<!-- IMPORT_START -->"
IMPORT_END = "<!-- IMPORT_END -->"


def check_pandoc():
    """Check if pandoc is installed and available in PATH."""
    return shutil.which("pandoc") is not None


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
        "Text ::",
        "Reveal",
        "SelfCheck",
        "Question ::",
        "Answer ::",
        "Option ::",
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
        "Interpretation ::",
        "Assumptions ::",
        "Limitations ::",
        "Image ::",
        "Width ::",
        "File ::",
        "Display ::",
        "Label ::",
        "Quiz",
        "YouTubeEmbed ::",
        "PanoptoEmbed ::",
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


def normalize_math_blocks(content: str) -> str:
    """
    Normalize LaTeX math emitted by Pandoc/Word.

    Fixes:
    - escaped $$ delimiters
    - over-escaped inline/display math delimiters
    - escaped exponent operators
    - double-escaped LaTeX commands
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

        # Fix double-escaped LaTeX commands
        line = line.replace(r"\\binom", r"\binom")

        normalized_lines.append(line)

    return "\n".join(normalized_lines)


def clean_r_code(code: str) -> str:
    """
    Clean R code after Pandoc conversion.

    Fixes:
    - trailing backslashes
    - escaped symbols
    - removes artificial blank lines from Word/Pandoc
    """
    cleaned_lines = []

    for raw_line in code.splitlines():
        line = raw_line.rstrip()

        if line.endswith("\\"):
            line = line[:-1].rstrip()

        line = line.replace(r"\<-", "<-")
        line = line.replace(r"\"", '"')
        line = line.replace(r"\<", "<")
        line = line.replace(r"\>", ">")
        line = line.replace(r"\$", "$")
        line = line.replace(r"\~", "~")


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
            r"^(?:#+\s*)?Reveal\s*$",
            r"^(?:#+\s*)?Quiz\s*$",
            r"^(?:#+\s*)?SelfCheck\s*$",
            r"^(?:#+\s*)?Callout\s*::",
            r"^(?:#+\s*)?Image\s*::",
            r"^(?:#+\s*)?File\s*::",
            r"^(?:#+\s*)?YouTubeEmbed\s*::",
            r"^(?:#+\s*)?PanoptoEmbed\s*::",
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
    warnings = []
    lines = content.split("\n")
    project_root = project_root or Path(".")

    quiz_open = False
    quiz_start_line = None
    quiz_has_question = False
    quiz_option_count = 0
    quiz_has_answer = False

    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        if not line:
            continue

        malformed_match = re.match(
            r"^(YouTubeEmbed|PanoptoEmbed|Image|File|Callout|Question|Option|Answer|Caption|Alt|Width|Display|Label|R Mode|Echo|Output)\s*:\s+\S+",
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
            continue

        if quiz_open and (is_markdown_heading(raw_line) or is_interaction_header(raw_line)):
            if not quiz_has_question:
                warnings.append(f"{page_id} line {quiz_start_line}: Quiz block missing Question ::")
            if quiz_option_count < 2:
                warnings.append(f"{page_id} line {quiz_start_line}: Quiz block has fewer than 2 Option :: lines")
            if not quiz_has_answer:
                warnings.append(f"{page_id} line {quiz_start_line}: Quiz block missing Answer ::")
            quiz_open = False
            quiz_start_line = None

        if quiz_open:
            if re.match(r"^Question\s*::\s*(.+)$", line, re.IGNORECASE):
                quiz_has_question = True
            elif re.match(r"^Option\s*::\s*(.+)$", line, re.IGNORECASE):
                quiz_option_count += 1
            elif re.match(r"^Answer\s*::\s*(.+)$", line, re.IGNORECASE):
                quiz_has_answer = True

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

    if quiz_open:
        if not quiz_has_question:
            warnings.append(f"{page_id} line {quiz_start_line}: Quiz block missing Question ::")
        if quiz_option_count < 2:
            warnings.append(f"{page_id} line {quiz_start_line}: Quiz block has fewer than 2 Option :: lines")
        if not quiz_has_answer:
            warnings.append(f"{page_id} line {quiz_start_line}: Quiz block missing Answer ::")

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
    """Detect and render localized Tab interactions (Quarto tabset)."""
    lines = content.split("\n")
    new_lines = []
    count = 0

    in_tabs = False
    current_tab_title = None
    tab_content_lines = []

    def flush_tab():
        if current_tab_title:
            new_lines.append(f"## {current_tab_title}")
            new_lines.append("\n".join(tab_content_lines).strip())
            new_lines.append("")

    for line in lines:
        stripped = line.strip()

        if not in_tabs:
            if re.match(r"^(?:#+\s*)?Tabs\s*$", stripped, re.IGNORECASE):
                in_tabs = True
                new_lines.append("::: {.panel-tabset}")
                count += 1
                current_tab_title = None
                tab_content_lines = []
                continue
            else:
                new_lines.append(line)
        else:
            if is_markdown_heading(line) or (
                is_interaction_header(line)
                and not re.match(r"^(?:#+\s*)?Tabs\s*$", stripped, re.IGNORECASE)
            ):
                flush_tab()
                new_lines.append(":::")
                new_lines.append(line)
                in_tabs = False
                current_tab_title = None
                tab_content_lines = []
            elif "::" in stripped:
                flush_tab()
                current_tab_title, tab_content = stripped.split("::", 1)
                current_tab_title = current_tab_title.strip()
                tab_content_lines = [tab_content.strip()]
            else:
                if current_tab_title is not None:
                    tab_content_lines.append(line)
                elif stripped:
                    tab_content_lines.append(line)

    if in_tabs:
        flush_tab()
        new_lines.append(":::")

    if count > 0:
        click.echo(click.style("Detected tabs interaction", fg="blue"))
        click.echo("  Rendering as tabset")

    return "\n".join(new_lines), count


def parse_callouts(content: str) -> tuple[str, int]:
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
        text_lines = []
        i += 1

        while i < len(lines):
            s = lines[i].strip()
            if is_markdown_heading(lines[i]) or is_interaction_header(lines[i]):
                break

            field_match = re.match(r"^Text\s*::\s*(.*)$", s, re.IGNORECASE)
            if field_match:
                text_lines.append(field_match.group(1).strip())
            elif s:
                text_lines.append(lines[i].strip())

            i += 1

        new_lines.append(f"::: {{.callout-{callout_type}}}")
        if text_lines:
            new_lines.append("\n".join(text_lines).strip())
        new_lines.append(":::")
        new_lines.append("")
        count += 1

    if count > 0:
        click.echo(click.style("Detected callouts", fg="blue"))
        click.echo(f"  Rendering {count} callout blocks")

    return "\n".join(new_lines), count


def parse_selfcheck(content: str) -> tuple[str, int]:
    lines = content.split("\n")
    new_lines = []
    count = 0
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()

        if not re.match(r"^(?:#+\s*)?SelfCheck\s*$", stripped, re.IGNORECASE):
            new_lines.append(lines[i])
            i += 1
            continue

        question = ""
        answer_lines = []
        i += 1

        while i < len(lines):
            s = lines[i].strip()
            if is_markdown_heading(lines[i]) or is_interaction_header(lines[i]):
                break

            q_match = re.match(r"^Question\s*::\s*(.*)$", s, re.IGNORECASE)
            a_match = re.match(r"^Answer\s*::\s*(.*)$", s, re.IGNORECASE)

            if q_match:
                question = q_match.group(1).strip()
            elif a_match:
                answer_lines.append(a_match.group(1).strip())
            elif s:
                answer_lines.append(lines[i].strip())

            i += 1

        new_lines.append("::: {.callout-tip}")
        if question:
            new_lines.append(f"**Self-check:** {question}")
            new_lines.append("")
        if answer_lines:
            new_lines.append("**Suggested answer**")
            new_lines.append("")
            new_lines.append("\n".join(answer_lines).strip())
        new_lines.append(":::")
        new_lines.append("")
        count += 1

    if count > 0:
        click.echo(click.style("Detected self-check blocks", fg="blue"))
        click.echo(f"  Rendering {count} self-check interactions")

    return "\n".join(new_lines), count


def parse_reveal(content: str) -> tuple[str, int]:
    lines = content.split("\n")
    new_lines = []
    count = 0
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()

        if not re.match(r"^(?:#+\s*)?Reveal\s*$", stripped, re.IGNORECASE):
            new_lines.append(lines[i])
            i += 1
            continue

        step_lines = []
        i += 1

        while i < len(lines):
            s = lines[i].strip()
            if is_markdown_heading(lines[i]) or is_interaction_header(lines[i]):
                break

            if s:
                step_lines.append(lines[i].strip())
            i += 1

        new_lines.append("<details>")
        new_lines.append("<summary><strong>Show steps</strong></summary>")
        new_lines.append("")

        for step in step_lines:
            new_lines.append(f"- {step}")

        if step_lines:
            new_lines.append("")

        new_lines.append("</details>")
        new_lines.append("")
        count += 1

    if count > 0:
        click.echo(click.style("Detected reveal blocks", fg="blue"))
        click.echo(f"  Rendering {count} reveal interactions")

    return "\n".join(new_lines), count


def parse_quiz(content: str) -> tuple[str, int]:
    """Parse Word-authored Quiz blocks into a static formative quiz UI."""
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
        answer = ""
        explanation_lines = []
        i += 1
        quiz_index += 1
        quiz_name = f"quiz_{quiz_index}"

        while i < len(lines):
            s = lines[i].strip()

            if is_markdown_heading(lines[i]) or is_interaction_header(lines[i]):
                break

            q_match = re.match(r"^Question\s*::\s*(.*)$", s, re.IGNORECASE)
            o_match = re.match(r"^Option\s*::\s*(.*)$", s, re.IGNORECASE)
            a_match = re.match(r"^Answer\s*::\s*(.*)$", s, re.IGNORECASE)
            e_match = re.match(r"^Explanation\s*::\s*(.*)$", s, re.IGNORECASE)

            if q_match:
                question = q_match.group(1).strip()
            elif o_match:
                options.append(o_match.group(1).strip())
            elif a_match:
                answer = a_match.group(1).strip()
            elif e_match:
                explanation_lines.append(e_match.group(1).strip())
            elif s:
                explanation_lines.append(lines[i].strip())

            i += 1

        new_lines.append("")
        new_lines.append("## Quiz")
        new_lines.append("")

        if question:
            new_lines.append(question)
            new_lines.append("")

        if options:
            new_lines.append(f'<form class="quiz-block" data-quiz="{quiz_name}">')
            for idx, option in enumerate(options, start=1):
                option_id = f"{quiz_name}_opt_{idx}"
                option_html = esc(option)
                new_lines.append(
                    f'<div class="quiz-option">'
                    f'<input type="radio" id="{option_id}" name="{quiz_name}" value="{option_html}"> '
                    f'<label for="{option_id}">{option_html}</label>'
                    f'</div>'
                )
            new_lines.append("</form>")
            new_lines.append("")

        new_lines.append("<details>")
        new_lines.append("<summary><strong>Show answer</strong></summary>")
        new_lines.append("")

        if answer:
            new_lines.append(f"**Answer:** {esc(answer)}")
            new_lines.append("")

        if explanation_lines:
            new_lines.append("**Explanation:**")
            new_lines.append("")
            new_lines.append("\n".join(explanation_lines).strip())
            new_lines.append("")

        new_lines.append("</details>")
        new_lines.append("")
        count += 1

    if count > 0:
        click.echo(click.style("Detected quiz blocks", fg="blue"))
        click.echo(f"  Rendering {count} static single-select quizzes")

    return "\n".join(new_lines), count


def parse_images(content: str, qmd_path: Path, course_dir: Path) -> tuple[str, int]:
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

        click.echo(click.style(f"✅ Import complete. Imported: {imported_count}, Skipped: {skipped_count}", fg="green"))

    except Exception as e:
        click.echo(click.style(f"Error: {str(e)}", fg="red"), err=True)