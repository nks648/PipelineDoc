"""
cli.py — The command-line interface for PipelineDoc
----------------------------------------------------
This is the entry point — the code that runs when someone types
`pipelinedoc` in the terminal.

We use the `click` library to define the CLI. Click handles:
  - Parsing arguments and options from the command line
  - Showing --help text automatically
  - Printing nice error messages for bad input

We use the `rich` library for colorful, readable terminal output.

The main command flow is:
  1. User runs: pipelinedoc run ./my_pipelines
  2. CLI validates the folder exists
  3. parser.scan_folder()  → extracts code structure from each .py file
  4. analyzer.analyze_all() → sends each structure to Claude for analysis
  5. renderer.render_markdown() → writes output/pipeline-map.md
  6. renderer.render_html()     → writes output/pipeline-map.html
  7. Print success summary
"""

import os                           # Standard library: path checking
import sys                          # Standard library: sys.exit() for clean exits

import click                        # Third-party: CLI framework
from rich.console import Console    # Third-party: colored terminal output
from rich.panel import Panel        # Third-party: bordered text panels
from rich.table import Table        # Third-party: formatted tables
from rich import print as rprint    # Third-party: rich-aware print function

# Import our own modules
from pipelinedoc import parser, analyzer, renderer

# Create a Rich console — this is the object we use to print to the terminal
console = Console()


# -------------------------------------------------------------------
# CLI GROUP: `pipelinedoc`
# -------------------------------------------------------------------
# @click.group() means this is a parent command that has subcommands.
# For example: `pipelinedoc run`, `pipelinedoc version`

@click.group()
def cli():
    """
    PipelineDoc — Auto-generate documentation for Python data pipelines.

    Use 'pipelinedoc run <folder>' to analyze a folder of pipeline scripts.
    """
    # This function body is intentionally empty.
    # @click.group() uses the docstring for --help text.
    pass


# -------------------------------------------------------------------
# SUBCOMMAND: `pipelinedoc run`
# -------------------------------------------------------------------

@cli.command()
@click.argument(
    "folder",
    default=".",                              # Default to current directory
    type=click.Path(exists=True, file_okay=False, dir_okay=True),  # Must be a real dir
)
@click.option(
    "--output-dir",
    default=None,
    help="Override the output directory (default: ./output)",
)
@click.option(
    "--no-html",
    is_flag=True,
    default=False,
    help="Skip generating the HTML file — only produce Markdown.",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Show extra details during processing.",
)
def run(folder: str, output_dir: str, no_html: bool, verbose: bool):
    """
    Scan FOLDER and generate documentation for all Python pipeline files.

    FOLDER defaults to the current directory if not specified.

    Examples:\n
        pipelinedoc run ./pipelines\n
        pipelinedoc run ./src --no-html\n
        pipelinedoc run . --output-dir ./docs
    """

    # ---- Welcome banner ----
    console.print(Panel.fit(
        "[bold blue]PipelineDoc[/bold blue] — AI-powered pipeline documentation",
        border_style="blue",
    ))

    # ---- Override output dir if --output-dir was passed ----
    if output_dir:
        # Patch the config constants so renderer uses the custom dir
        import pipelinedoc.config as cfg
        cfg.OUTPUT_DIR = output_dir
        cfg.OUTPUT_MARKDOWN = os.path.join(output_dir, "pipeline-map.md")
        cfg.OUTPUT_HTML = os.path.join(output_dir, "pipeline-map.html")
        # Also patch renderer's imported names (they were already imported)
        import pipelinedoc.renderer as rnd
        rnd.OUTPUT_DIR = output_dir
        rnd.OUTPUT_MARKDOWN = cfg.OUTPUT_MARKDOWN
        rnd.OUTPUT_HTML = cfg.OUTPUT_HTML

    # ---- STEP 1: Scan the folder ----
    console.print(f"\n[bold]Step 1/3[/bold] Scanning folder: [cyan]{folder}[/cyan]")

    structures = parser.scan_folder(folder)

    if not structures:
        console.print(
            "[yellow]⚠  No Python files found in the specified folder.[/yellow]\n"
            "   Make sure the folder contains .py files and isn't empty."
        )
        sys.exit(0)

    console.print(f"   Found [green]{len(structures)}[/green] Python file(s) to analyze.")

    # If verbose, show a table of discovered files
    if verbose:
        table = Table(title="Discovered Files", show_header=True)
        table.add_column("File", style="cyan")
        table.add_column("Functions", justify="right")
        table.add_column("Imports", justify="right")
        for s in structures:
            table.add_row(
                s.get("filename", "?"),
                str(len(s.get("functions", []))),
                str(len(s.get("imports", []))),
            )
        console.print(table)

    # ---- STEP 2: Analyze with Claude ----
    console.print(f"\n[bold]Step 2/3[/bold] Sending files to Claude for analysis...")

    try:
        analyses = analyzer.analyze_all(structures)
    except EnvironmentError as e:
        # This fires if the API key is missing (from config.py)
        console.print(f"[red]Configuration error:[/red]\n{e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error during analysis:[/red] {e}")
        sys.exit(1)

    # ---- STEP 3: Render output ----
    console.print(f"\n[bold]Step 3/3[/bold] Generating documentation...")

    md_path = renderer.render_markdown(analyses, folder)
    console.print(f"   [green]✓[/green] Markdown: [cyan]{md_path}[/cyan]")

    if not no_html:
        html_path = renderer.render_html(analyses, folder)
        console.print(f"   [green]✓[/green] HTML:     [cyan]{html_path}[/cyan]")

    # ---- Success summary ----
    successful = sum(1 for a in analyses if "error" not in a)
    failed = len(analyses) - successful

    console.print(Panel(
        f"[bold green]Documentation generated![/bold green]\n\n"
        f"  Files analyzed:  [green]{successful}[/green] succeeded"
        + (f", [red]{failed}[/red] failed" if failed else "")
        + f"\n  Markdown output: [cyan]{md_path}[/cyan]\n"
        + (f"  HTML output:     [cyan]{html_path}[/cyan]\n" if not no_html else ""),
        border_style="green",
        title="Done",
    ))


# -------------------------------------------------------------------
# SUBCOMMAND: `pipelinedoc version`
# -------------------------------------------------------------------

@cli.command()
def version():
    """Show the installed version of PipelineDoc."""
    try:
        from importlib.metadata import version as pkg_version
        v = pkg_version("pipelinedoc")
    except Exception:
        v = "development"
    console.print(f"PipelineDoc version [bold]{v}[/bold]")


# -------------------------------------------------------------------
# ENTRY POINT
# -------------------------------------------------------------------
# This block runs when you call `python cli.py` directly.
# When installed as a package, pyproject.toml maps `pipelinedoc` → cli:cli

if __name__ == "__main__":
    cli()
