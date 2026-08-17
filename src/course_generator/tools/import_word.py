import os
import base64
import shutil
import subprocess
from pathlib import Path
import click
import re
import html
import json
import yaml
from urllib.parse import urlparse, parse_qs
from ..core.config_loader import ConfigLoader
from ..core.parsing import is_markdown_heading, is_interaction_header
from ..engines.webr.support import (
    contains_webr_directive,
    ensure_webr_support,
)
from ..engines.webr.data import (
    extract_webr_data_resources,
    build_webr_data_bootstrap_script,
)
from ..engines.r.cleaning import clean_r_code
from ..engines.r.source import resolve_r_code_source
from ..engines.r.parser import parse_r_example, parse_r_code
from ..engines.code_parser import parse_generic_code_blocks
from ..interactions.tabs import parse_tabs
from ..interactions.callout import parse_callouts
from ..interactions.selfcheck import parse_selfcheck
from ..interactions.reveal import parse_reveal
from ..core.assets import rewrite_asset_path
from ..interactions.images import parse_images
from ..interactions.files import parse_files
from ..interactions.html_embed import parse_html_embeds
from ..interactions.javascript import parse_javascript_interactions
from ..interactions.quiz import parse_quiz
from ..interactions.media import (
    extract_youtube_id,
    extract_panopto_id,
    parse_embeds,
)

IMPORT_START = "<!-- IMPORT_START -->"
IMPORT_END = "<!-- IMPORT_END -->"


def check_pandoc():
    """Check if pandoc is installed and available in PATH."""
    return shutil.which("pandoc") is not None


def contains_html_embed_directive(content: str) -> bool:
    """Return True when imported Markdown contains a local HTML Embed block."""
    normalized = re.sub(r"\\\s*\n", "\n", content)
    return re.search(
        r"^\s*(?:#+\s*)?HTML Embed\s*::\s*.+$",
        normalized,
        re.IGNORECASE | re.MULTILINE,
    ) is not None


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
        "Code",
        "END Code",
        "Language ::",
        "END R Code",
        "JavaScript Interaction",
        "END JavaScript Interaction",
        "Container ID ::",
        "Interaction ::",
        "R Example",
        "END R Example",
        "R Mode ::",
        "Mode ::",
        "Source ::",
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


def normalize_adjacent_inline_code(content: str) -> str:
    """
    Merge immediately adjacent Pandoc inline-code spans.

    Word can contain one visually continuous code expression split across
    multiple character-style runs. Pandoc then emits adjacent Markdown spans,
    for example::

        `library``(rio)`

    This normalises them to::

        `library(rio)`

    Only single-backtick inline-code spans with no whitespace between them are
    merged. Fenced code blocks and ordinary separated inline-code spans are
    unaffected.
    """
    pattern = re.compile(r"`([^`\n]+)``([^`\n]+)`")

    previous = None
    while content != previous:
        previous = content
        content = pattern.sub(r"`\1\2`", content)

    return content


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


def copy_site_resources(course_source_dir: Path, course_dir: Path):
    """Copy authored resources into the generated course directory.

    Prefer the self-contained course ``resources/`` folder. The old top-level
    ``resources/`` location remains as a compatibility fallback.
    """
    source_resources = course_source_dir / "resources"
    if not source_resources.exists():
        source_resources = Path("resources")
    if not source_resources.exists():
        click.echo(click.style("No course or top-level resources/ directory found; skipping resource copy", fg="yellow"))
        return

    dest_resources = course_dir / "resources"

    if dest_resources.exists():
        shutil.rmtree(dest_resources)

    shutil.copytree(source_resources, dest_resources)
    click.echo(f"Copied site resources to: {dest_resources}")


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
    legacy_r_code_open = False
    generic_code_open = False
    generic_code_language = ""
    bounded_blocks = {
        "callout": "Callout",
        "reveal": "Reveal",
        "selfcheck": "SelfCheck",
        "tabs": "Tabs",
        "quiz": "Quiz",
        "r code": "R Code",
        "code": "Code",
        "javascript interaction": "JavaScript Interaction",
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
            r"^(?:#+\s*)?END\s+(Callout|Reveal|SelfCheck|Tabs|Quiz|R Code|R Example|Code|JavaScript Interaction|Image|File|HTML Embed)\s*$",
            line,
            re.IGNORECASE,
        )
        if end_match:
            end_name = end_match.group(1).lower()
            if end_name == "r code":
                legacy_r_code_open = False
            elif end_name == "code":
                generic_code_open = False
                generic_code_language = ""
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
            r"^(?:#+\s*)?(Callout\s*::\s*.+|Reveal|SelfCheck|Tabs|Quiz|R Code|R Example|Code|JavaScript Interaction|Image\s*::\s*.+|File\s*::\s*.+|HTML Embed\s*::\s*.+)\s*$",
            line,
            re.IGNORECASE,
        )
        if opener_match:
            opener = opener_match.group(1)
            name = re.split(r"\s*::", opener, maxsplit=1)[0].strip().lower()
            block_stack.append((name, idx))
            if name == "r code":
                legacy_r_code_open = True
            elif name == "code":
                generic_code_open = True
                generic_code_language = ""

        if generic_code_open:
            language_match = re.match(
                r"^Language\s*::\s*(.+)$",
                line,
                re.IGNORECASE,
            )
            if language_match:
                generic_code_language = language_match.group(1).strip().lower()

        malformed_match = re.match(
            r"^(YouTubeEmbed|PanoptoEmbed|HTML Embed|JavaScript Interaction|Image|File|Callout|Title|Question|Type|Option|Answer|Correct|Feedback|Hint|Explanation|Caption|Alt|Width|Height|Fallback Image|Display|Label|R Mode|Mode|Source|Container ID|Interaction|Echo|Output)\s*:\s+\S+",
            line,
            re.IGNORECASE,
        )
        if malformed_match:
            warnings.append(f"{page_id} line {idx}: possible directive syntax error. Use '::' not ':'.")

        r_mode_match = re.match(r"^(?:R\s+)?Mode\s*::\s*(.+)$", line, re.IGNORECASE)
        if r_mode_match:
            mode = r_mode_match.group(1).strip().rstrip("\\").strip().lower()

            if legacy_r_code_open:
                if mode not in ["static", "r", "webr"]:
                    warnings.append(
                        f"{page_id} line {idx}: unknown R Mode '{mode}'. "
                        "Use 'static' or 'webr'."
                    )

            elif generic_code_open:
                if generic_code_language == "python":
                    if mode not in ["static", "python", "pyodide"]:
                        warnings.append(
                            f"{page_id} line {idx}: unknown Python Mode '{mode}'. "
                            "Use 'static' or 'pyodide'."
                        )
                elif generic_code_language == "r":
                    if mode not in ["static", "r", "webr"]:
                        warnings.append(
                            f"{page_id} line {idx}: unknown R Mode '{mode}'. "
                            "Use 'static' or 'webr'."
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


def parse_interactions(
    content: str,
    qmd_path: Path,
    course_dir: Path,
    course_source_dir: Path | None = None,
) -> str:
    """Coordinator function for parsing supported interaction types."""
    total_interactions = 0

    content = normalize_metadata_blocks(content)
    content = normalize_math_blocks(content)

    content, count = parse_tabs(content)
    total_interactions += count

    content, count = parse_generic_code_blocks(
        content,
        course_source_dir=course_source_dir,
    )
    total_interactions += count

    content, count = parse_r_example(content)
    total_interactions += count

    content, count = parse_r_code(
        content,
        course_source_dir=course_source_dir,
        qmd_path=qmd_path,
        course_dir=course_dir,
    )
    total_interactions += count

    content, count = parse_javascript_interactions(
        content,
        course_source_dir=course_source_dir,
    )
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


def insert_markdown_into_qmd(
    md_path: Path,
    qmd_path: Path,
    course_dir: Path,
    course_source_dir: Path | None = None,
):
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

    # Repair a narrow Word/Pandoc artefact where one visual inline-code
    # expression is emitted as adjacent Markdown code spans.
    imported_content = normalize_adjacent_inline_code(imported_content)

    imported_content = parse_interactions(
        imported_content,
        qmd_path,
        course_dir,
        course_source_dir=course_source_dir,
    ).strip()

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
        config_file = Path(config_path).resolve()
        course_source_dir = config_file.parent
        config = ConfigLoader.load(str(config_file))
        course_id = config.module.id.lower()
        click.echo(f"Importing Word content for course: {course_id}")

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

        md_dir = course_dir / "imported" / "md"
        md_dir.mkdir(parents=True, exist_ok=True)

        click.echo(f"Locating target files in: {course_dir}")

        copy_site_resources(course_source_dir, course_dir)

        imported_count = 0
        skipped_count = 0
        webr_required = False
        html_resources_required = False

        for _, _, page in _iter_pages(config):
            if not getattr(page, "source_docx", None):
                skipped_count += 1
                click.echo(click.style(f"Skipping page '{page.id}' (no source_docx)", fg="yellow"))
                continue

            declared_docx_path = Path(page.source_docx)
            docx_path = (
                declared_docx_path
                if declared_docx_path.is_absolute()
                else course_source_dir / declared_docx_path
            ).resolve()

            # Compatibility fallback for older configurations whose paths were
            # intentionally relative to the project working directory.
            if not docx_path.exists() and not declared_docx_path.is_absolute():
                legacy_docx_path = declared_docx_path.resolve()
                if legacy_docx_path.exists():
                    docx_path = legacy_docx_path

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

            warnings = validate_import_content(
                raw_md,
                page.id,
                project_root=course_source_dir,
            )
            print_validation_warnings(warnings)

            target_path = _find_target_qmd(course_dir, page.id)
            if target_path:
                click.echo(f"Inserting converted content into {target_path}")
                insert_markdown_into_qmd(
                    md_path,
                    target_path,
                    course_dir,
                    course_source_dir=course_source_dir,
                )
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
