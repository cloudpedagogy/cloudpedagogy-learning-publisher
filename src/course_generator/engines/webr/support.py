import re
import shutil
import subprocess
from pathlib import Path

import click
import yaml


def contains_webr_directive(content: str) -> bool:
    """Return True when imported Markdown requests browser-based WebR."""
    normalized = re.sub(r"\\\s*\n", "\n", content)
    return re.search(
        r"^\s*(?:R\s+)?Mode\s*::\s*webr\s*$",
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
