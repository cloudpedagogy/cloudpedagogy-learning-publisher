import re
from pathlib import Path

import click

from ...core.parsing import is_markdown_heading, is_interaction_header
from ..webr.data import (
    extract_webr_data_resources,
    build_webr_data_bootstrap_script,
)
from ..webr.packages import (
    webr_code_may_need_packages,
    build_webr_lazy_package_bootstrap_script,
)
from .cleaning import clean_r_code
from .source import resolve_r_code_source


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

def parse_r_code(
    content: str,
    course_source_dir: Path | None = None,
    qmd_path: Path | None = None,
    course_dir: Path | None = None,
) -> tuple[str, int]:
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

    External code may be supplied instead of inline code:

    R Code
    Source :: code/example.R
    Mode :: static
    Echo :: true
    Output :: true
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

    WebR course data:
    - literal paths under resources/data/ are detected only in WebR blocks
    - referenced files are validated against the course source package
    - small referenced files are Base64-embedded at import time, so no runtime
      HTTP/file fetch is required
    - browser JavaScript resolves R's actual getwd() and writes the embedded
      bytes beneath that directory using WebR's public FS API
    - data-aware WebR execution uses a best-effort readiness guard
    - no hidden WebR execution cell is generated
    - the learner-visible R code is preserved unchanged
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
    source = ""
    staged_webr_resources = set()
    webr_package_bootstrap_added = False

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
        nonlocal code_lines, new_lines, fig_alt, fig_cap, r_mode, echo, output, source
        nonlocal staged_webr_resources
        nonlocal webr_package_bootstrap_added

        inline_code = clean_r_code("\n".join(code_lines))
        if source:
            if inline_code:
                raise ValueError(
                    "R Code cannot contain both Source :: and inline R code."
                )
            if course_source_dir is None:
                raise ValueError(
                    "An R Code Source :: requires the course configuration directory."
                )
            cleaned_code = clean_r_code(
                resolve_r_code_source(source, course_source_dir)
            )
        else:
            cleaned_code = inline_code

        if not cleaned_code:
            raise ValueError(
                "R Code requires either Source :: or inline R code."
            )
        chunk_engine = "webr-r" if r_mode.lower() == "webr" else "r"
        echo_value = normalize_bool(echo, default="true")
        output_value = normalize_bool(output, default="true")

        # WebR runs inside a browser-side virtual filesystem. A normal site
        # resource such as resources/data/example.csv therefore must be staged
        # into WebR before learner code can read that same relative path.
        #
        # This is deliberately limited to literal resources/data/... strings
        # inside WebR cells. Static R and WebR cells without course data are
        # unchanged. Small referenced files are embedded at import time and
        # staged in browser JavaScript via WebR's FS API, with no runtime fetch
        # and no hidden R setup cell.
        if (
            chunk_engine == "webr-r"
            and not webr_package_bootstrap_added
            and webr_code_may_need_packages(cleaned_code)
        ):
            new_lines.append(build_webr_lazy_package_bootstrap_script())
            new_lines.append("")
            webr_package_bootstrap_added = True
            click.echo("  Enabling lazy WebR package installation")

        if chunk_engine == "webr-r":
            referenced_resources = extract_webr_data_resources(cleaned_code)
            resources_to_stage = [
                path
                for path in referenced_resources
                if path not in staged_webr_resources
            ]

            if resources_to_stage:
                if (
                    course_source_dir is None
                    or qmd_path is None
                    or course_dir is None
                ):
                    raise ValueError(
                        "WebR code references resources/data/, but the importer "
                        "does not have enough course-path context to stage the data."
                    )

                bootstrap_script = build_webr_data_bootstrap_script(
                    resources_to_stage,
                    qmd_path=qmd_path,
                    course_dir=course_dir,
                    course_source_dir=course_source_dir,
                )
                if bootstrap_script:
                    new_lines.append(bootstrap_script)
                    new_lines.append("")
                    staged_webr_resources.update(resources_to_stage)
                    click.echo(
                        "  Embedding "
                        f"{len(resources_to_stage)} course data file(s) for WebR"
                    )

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
        source = ""

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
                source = ""
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
                mode_match = re.match(r"^(?:R\s+)?Mode\s*::\s*(.*)$", stripped, re.IGNORECASE)
                source_match = re.match(r"^Source\s*::\s*(.*)$", stripped, re.IGNORECASE)
                echo_match = re.match(r"^Echo\s*::\s*(.*)$", stripped, re.IGNORECASE)
                output_match = re.match(r"^Output\s*::\s*(.*)$", stripped, re.IGNORECASE)
                alt_match = re.match(r"^Alt\s*::\s*(.*)$", stripped, re.IGNORECASE)
                cap_match = re.match(r"^Caption\s*::\s*(.*)$", stripped, re.IGNORECASE)

                if mode_match:
                    r_mode = mode_match.group(1).strip().rstrip("\\").strip().lower()
                elif source_match:
                    source = source_match.group(1).strip().rstrip("\\").strip()
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
