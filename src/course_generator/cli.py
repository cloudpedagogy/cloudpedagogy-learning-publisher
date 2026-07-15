import click
import os
from pathlib import Path
from .core.config_loader import ConfigLoader
from .core.generator import Generator


@click.group()
def main():
    """CloudPedagogy Quarto Course Generator"""
    pass


@main.command()
@click.argument("config_path", type=click.Path(exists=True))
def validate(config_path):
    """Validate a course configuration YAML."""
    try:
        ConfigLoader.load(config_path)
        click.echo(click.style(f"✅ Configuration {config_path} is valid.", fg="green"))
    except Exception as e:
        click.echo(click.style(f"❌ Validation Error: {str(e)}", fg="red"), err=True)


@main.command()
@click.argument("config_path", type=click.Path(exists=True))
def inspect(config_path):
    """Show a readable summary of the course structure."""
    try:
        config = ConfigLoader.load(config_path)
        click.echo(
            click.style(
                f"\nModule: {config.module.id} ({config.module.code}) - {config.module.title}",
                bold=True,
            )
        )
        click.echo(f"Description: {config.module.description}")
        click.echo(f"Default Render Mode: {config.module.default_render_mode}")
        click.echo("-" * 40)

        for i, session in enumerate(config.sessions, 1):
            mode = session.render_mode or config.module.default_render_mode
            click.echo(f"Session {i}: {session.code} - {session.title} [{mode}]")
            for section in session.sections:
                click.echo(f"  Section {section.number}: {section.title} ({section.kind})")
                for page in section.pages:
                    click.echo(f"    - {page.title} ({page.kind})")

        click.echo("")

    except Exception as e:
        click.echo(click.style(f"Error: {str(e)}", fg="red"), err=True)


def _get_versioned_path(path_str):
    """Find the next available versioned path if the base path exists."""
    path = Path(path_str)

    if not path.exists():
        return str(path)

    parent = path.parent
    base_name = path.name
    counter = 1

    while True:
        new_path = parent / f"{base_name}_v{counter}"
        if not new_path.exists():
            return str(new_path)
        counter += 1


@main.command()
@click.argument("config_path", type=click.Path(exists=True))
@click.option(
    "--output-dir",
    "-o",
    default=None,
    help="Output directory for the generated course scaffold.",
)
@click.option(
    "--render-mode",
    "-m",
    type=click.Choice(["single_page", "multi_page"]),
    help="Override render mode.",
)
@click.option(
    "--templates-dir",
    "-t",
    default="templates",
    help="Directory containing Jinja2 templates.",
)
@click.option("--force", is_flag=True, help="Overwrite existing files.")
@click.option(
    "--versioned/--no-versioned",
    "versioning",
    is_flag=True,
    default=True,
    help="Use versioned folder, for example _v1, if target exists.",
)
def build(config_path, output_dir, render_mode, templates_dir, force, versioning):
    """
    Build a full course scaffold from a YAML config.

    Default output:
        build/courses/<module_id>/

    This is the generated Quarto working folder, not the final rendered site.
    """
    try:
        config = ConfigLoader.load(config_path)
        module_id = config.module.id.lower()

        config_dir = os.path.dirname(os.path.abspath(config_path))

        for other_file in os.listdir(config_dir):
            if other_file.endswith((".yml", ".yaml")) and other_file != os.path.basename(config_path):
                try:
                    other_config = ConfigLoader.load(os.path.join(config_dir, other_file))
                    if other_config.module.id.lower() == module_id:
                        click.echo(
                            click.style(
                                f"⚠️  WARNING: Config '{other_file}' also uses ID '{config.module.id}'.",
                                fg="yellow",
                            )
                        )
                        click.echo(
                            click.style(
                                f"   They will target the same build folder: build/courses/{module_id}",
                                fg="yellow",
                            )
                        )
                except Exception:
                    pass

        if output_dir is None:
            output_dir = os.path.join("build", "courses", module_id)

        if versioning:
            output_dir = _get_versioned_path(output_dir)

        generator = Generator(config, output_dir, templates_dir)
        generator.build(force=force, global_render_mode=render_mode)

        click.echo(click.style(f"Successfully generated course scaffold in {output_dir}", fg="green"))

    except Exception as e:
        click.echo(click.style(f"Error: {str(e)}", fg="red"), err=True)


@main.command()
@click.argument("config_path", type=click.Path(exists=True))
@click.option(
    "--source-dir",
    "-s",
    default=None,
    help="Source directory of the generated course scaffold.",
)
@click.option(
    "--output-dir",
    "-o",
    default=None,
    help="Output directory for the rendered site.",
)
@click.option(
    "--versioned/--no-versioned",
    is_flag=True,
    default=True,
    help="Enable versioning for the output directory.",
)
def render(config_path, source_dir, output_dir, versioned):
    """
    Render the full course project using Quarto.

    Default source:
        build/courses/<module_id>/

    Default output:
        output/courses/<module_id>/
    """
    try:
        config = ConfigLoader.load(config_path)
        module_id = config.module.id.lower()

        if source_dir is None:
            source_dir = os.path.join("build", "courses", module_id)

        if not os.path.exists(source_dir):
            click.echo(
                click.style(
                    f"Error: Source directory {source_dir} not found. Build it first.",
                    fg="red",
                ),
                err=True,
            )
            return

        if output_dir is None:
            output_dir = os.path.join("output", "courses", module_id)

        if versioned:
            output_dir = _get_versioned_path(output_dir)

        click.echo(f"Rendering {source_dir} to {output_dir}...")

        import subprocess

        rel_output_dir = os.path.relpath(output_dir, source_dir)
        cmd = ["quarto", "render", source_dir, "--output-dir", rel_output_dir]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            click.echo(click.style(f"✅ Successfully rendered course to {output_dir}", fg="green"))
        else:
            click.echo(click.style(f"❌ Quarto Render Error:\n{result.stderr}", fg="red"), err=True)

    except Exception as e:
        click.echo(click.style(f"Error: {str(e)}", fg="red"), err=True)


@main.command()
@click.argument("qmd_path", type=click.Path(exists=True))
def preview(qmd_path):
    """Preview a single page for fast authoring feedback."""
    try:
        click.echo(f"Previewing {qmd_path}...")

        import subprocess

        preview_dir = os.path.abspath(".preview")
        os.makedirs(preview_dir, exist_ok=True)

        cmd = ["quarto", "render", qmd_path, "--to", "html", "--output-dir", preview_dir]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            file_name = Path(qmd_path).stem + ".html"
            preview_file = os.path.join(preview_dir, file_name)
            click.echo(click.style(f"✅ Preview ready: {preview_file}", fg="green"))
        else:
            click.echo(click.style(f"❌ Quarto Preview Error:\n{result.stderr}", fg="red"), err=True)

    except Exception as e:
        click.echo(click.style(f"Error: {str(e)}", fg="red"), err=True)


@main.command()
@click.argument("config_dir", type=click.Path(exists=True), default="config")
@click.option("--force", is_flag=True, help="Overwrite existing files.")
@click.option("--no-version", is_flag=True, help="Disable versioning.")
def build_all(config_dir, force, no_version):
    """
    Build all courses found in the config directory.

    Default output for each course:
        build/courses/<module_id>/
    """
    try:
        files = [f for f in os.listdir(config_dir) if f.endswith((".yml", ".yaml"))]

        if not files:
            click.echo("No configuration files found.")
            return

        for f in files:
            path = os.path.join(config_dir, f)
            click.echo(f"Building {path}...")

            config = ConfigLoader.load(path)
            module_id = config.module.id.lower()

            output_dir = os.path.join("build", "courses", module_id)

            if not no_version:
                output_dir = _get_versioned_path(output_dir)

            generator = Generator(config, output_dir, "templates")
            generator.build(force=force)

        click.echo(click.style("✅ All courses built successfully.", fg="green"))

    except Exception as e:
        click.echo(click.style(f"Error: {str(e)}", fg="red"), err=True)


@main.command()
@click.option(
    "--path",
    "-p",
    default="config/course.yml",
    help="Path to create the template file.",
)
def init(path):
    """Create a default course configuration template."""
    content = """module:
  code: EPM102
  title: Example Module
  description: Example description
  default_render_mode: multi_page

sessions:
  - code: SE01
    title: Example Session
    sections:
      - number: 1
        title: Example Section
        subpages:
          - title: Example Page
            kind: text_page
"""

    try:
        if os.path.exists(path):
            if not click.confirm(f"File {path} already exists. Overwrite?"):
                return

        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

        with open(path, "w") as f:
            f.write(content)

        click.echo(click.style(f"✅ Created template at {path}", fg="green"))

    except Exception as e:
        click.echo(click.style(f"Error: {str(e)}", fg="red"), err=True)


@main.command()
@click.argument("config_path", type=click.Path(exists=True))
def import_word(config_path):
    """Import Word content into a generated course scaffold."""
    from .tools.import_word import run_import

    run_import(config_path)


if __name__ == "__main__":
    main()