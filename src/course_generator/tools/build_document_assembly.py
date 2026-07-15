from pathlib import Path
import argparse
import shutil
import subprocess
import yaml


def check_tool(name: str) -> bool:
    """Return True if a command-line tool is available."""
    return shutil.which(name) is not None


def run_pandoc_docx_to_markdown(docx_path: Path) -> str:
    """Convert a DOCX file to Markdown using Pandoc."""
    result = subprocess.run(
        [
            "pandoc",
            str(docx_path),
            "-t",
            "markdown",
            "--wrap=none",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def load_source_content(file_path: str) -> str:
    """Load source content from DOCX, Markdown, QMD, or text files."""
    path = Path(file_path)

    if not path.exists():
        return f"> Missing source file: `{file_path}`\n"

    if path.suffix.lower() == ".docx":
        return run_pandoc_docx_to_markdown(path)

    if path.suffix.lower() in [".md", ".qmd", ".txt"]:
        return path.read_text(encoding="utf-8")

    return f"> Unsupported source file type: `{file_path}`\n"


def build_assembly(config_path: str, render: bool = True) -> Path:
    """
    Build a modular publication from a YAML assembly file.

    Run from the project root:
        python src/course_generator/tools/build_document_assembly.py assemblies/phm102_handbook.yml

    Build QMD only:
        python src/course_generator/tools/build_document_assembly.py assemblies/phm102_handbook.yml --no-render
    """
    project_root = Path.cwd()
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Assembly config not found: {config_file}")

    if not check_tool("pandoc"):
        raise RuntimeError("Pandoc is not installed or not available on PATH.")

    if render and not check_tool("quarto"):
        raise RuntimeError("Quarto is not installed or not available on PATH.")

    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))

    publication = config.get("publication", {})
    pub_id = publication.get("id", config_file.stem)
    title = publication.get("title", pub_id)
    subtitle = publication.get("subtitle", "")

    base_output_dir = project_root / "output" / "publications" / pub_id
    qmd_dir = base_output_dir / "qmd"
    log_dir = base_output_dir / "logs"
    qa_dir = base_output_dir / "qa"
    rendered_dir = base_output_dir / "rendered"

    qmd_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    qa_dir.mkdir(parents=True, exist_ok=True)
    rendered_dir.mkdir(parents=True, exist_ok=True)

    output_qmd = qmd_dir / "index.qmd"

    lines = [
        "---",
        f'title: "{title}"',
    ]

    if subtitle:
        lines.append(f'subtitle: "{subtitle}"')

    lines.extend(
        [
            "format:",
            "  html:",
            "    toc: true",
            "    theme: cosmo",
            "  docx: default",
            "  pdf:",
            "    toc: true",
            "---",
            "",
            "# About this document",
            "",
            "This is a demo modular publication assembled from shared core content and document-specific Word content.",
            "",
        ]
    )

    sources = config.get("sources", {})
    qa_lines = [
        "# Modular Publication QA Report",
        "",
        f"Assembly config: `{config_file}`",
        f"Publication ID: `{pub_id}`",
        f"Title: {title}",
        "",
        "## Source files",
        "",
    ]

    missing_count = 0
    unsupported_count = 0

    for group_name in ["shared", "local"]:
        files = sources.get(group_name, [])

        if files:
            lines.append(f"# {group_name.replace('_', ' ').title()} Content")
            lines.append("")
            qa_lines.append(f"### {group_name.replace('_', ' ').title()}")
            qa_lines.append("")

        for file_path in files:
            source_path = Path(file_path)

            if not source_path.exists():
                missing_count += 1
                qa_lines.append(f"- MISSING: `{file_path}`")
            elif source_path.suffix.lower() not in [".docx", ".md", ".qmd", ".txt"]:
                unsupported_count += 1
                qa_lines.append(f"- UNSUPPORTED: `{file_path}`")
            else:
                qa_lines.append(f"- OK: `{file_path}`")

            content = load_source_content(file_path)
            lines.append(content)
            lines.append("")

        if files:
            qa_lines.append("")

    output_qmd.write_text("\n".join(lines), encoding="utf-8")

    qa_lines.extend(
        [
            "## Summary",
            "",
            f"- Missing files: {missing_count}",
            f"- Unsupported files: {unsupported_count}",
            f"- QMD output: `{output_qmd}`",
            f"- Rendered output directory: `{rendered_dir}`",
            "",
        ]
    )
    qa_report = qa_dir / "assembly_qa.md"
    qa_report.write_text("\n".join(qa_lines), encoding="utf-8")

    print(f"Built assembly source: {output_qmd}")
    print(f"QA report: {qa_report}")

    if render:
        render_cmd = [
            "quarto",
            "render",
            "index.qmd",
            "--output-dir",
            "../rendered",
        ]

        print("Rendering publication with Quarto...")
        subprocess.run(render_cmd, cwd=qmd_dir, check=True)

        print(f"Rendered publication to: {rendered_dir}")
        print("Open HTML:")
        print(f"  open {rendered_dir / 'index.html'}")
    else:
        print("Rendering skipped.")
        print("To render manually:")
        print(f"  cd {qmd_dir}")
        print("  quarto render index.qmd --output-dir ../rendered")

    return output_qmd


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and optionally render a modular Quarto publication from a YAML assembly file."
    )
    parser.add_argument(
        "config_path",
        help="Path to the assembly YAML file, e.g. assemblies/phm102_handbook.yml",
    )
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="Build the QMD only; do not run Quarto render.",
    )
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    build_assembly(args.config_path, render=not args.no_render)
