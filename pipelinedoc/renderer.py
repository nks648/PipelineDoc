"""
renderer.py — Converts AI analyses into Markdown and HTML documentation
-----------------------------------------------------------------------
This module takes the list of analysis dicts (from analyzer.py) and
renders them into two output files:
  1. pipeline-map.md  — a clean Markdown document
  2. pipeline-map.html — a styled HTML page (using Jinja2 templating)

Why two formats?
  Markdown is great for developers (readable in GitHub, VS Code, etc.)
  HTML is great for sharing with non-technical stakeholders via a browser.

Two main functions:
  - render_markdown(analyses, folder_path)  → writes .md, returns the path
  - render_html(analyses, folder_path)      → writes .html, returns the path
"""

import os                        # Standard library: file path handling
from datetime import datetime    # Standard library: for the timestamp in the header
from jinja2 import Environment, BaseLoader  # Third-party: HTML template engine

from pipelinedoc.config import OUTPUT_MARKDOWN, OUTPUT_HTML, OUTPUT_DIR


# -------------------------------------------------------------------
# HELPER: Ensure the output directory exists
# -------------------------------------------------------------------

def _ensure_output_dir():
    """Creates the output/ directory if it doesn't already exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


# -------------------------------------------------------------------
# HELPER: Build the dependency table rows
# -------------------------------------------------------------------

def _build_dep_table_rows(analyses: list[dict]) -> list[dict]:
    """
    For each analyzed file, extract the key libraries and external services
    to populate the dependency table in the documentation.

    Returns a list of dicts with: filename, libraries, services
    """
    rows = []

    for item in analyses:
        filename = item.get("filename", "unknown")
        dependencies = item.get("dependencies", "")
        sources = item.get("sources", "")

        # Combine dependencies and sources text for display
        # Truncate to keep the table readable
        lib_text = dependencies[:80] + "..." if len(dependencies) > 80 else dependencies
        src_text = sources[:80] + "..." if len(sources) > 80 else sources

        rows.append({
            "filename": filename,
            "libraries": lib_text or "—",
            "services": src_text or "—",
        })

    return rows


# -------------------------------------------------------------------
# HELPER: Compile all RISKS sections into one list
# -------------------------------------------------------------------

def _compile_risks(analyses: list[dict]) -> list[str]:
    """
    Gathers all risk entries from every file's analysis into one flat list.
    Each entry is formatted as "filename: risk text" for attribution.
    """
    all_risks = []

    for item in analyses:
        filename = item.get("filename", "unknown")
        risks = item.get("risks", "").strip()

        if risks and risks != "Analysis failed":
            all_risks.append(f"**{filename}**: {risks}")

    return all_risks


# -------------------------------------------------------------------
# HELPER: Build the ecosystem overview paragraph
# -------------------------------------------------------------------

def _build_overview(analyses: list[dict]) -> str:
    """
    Combines the PURPOSE field from every file to build a brief
    high-level paragraph describing the entire pipeline ecosystem.
    """
    purposes = [
        item.get("purpose", "").strip()
        for item in analyses
        if item.get("purpose") and item.get("purpose") != "Analysis failed"
    ]

    if not purposes:
        return "No pipeline files could be analyzed successfully."

    # Join all purposes into a readable paragraph
    combined = " ".join(purposes)
    return combined


# -------------------------------------------------------------------
# MAIN FUNCTION 1: Render Markdown
# -------------------------------------------------------------------

def render_markdown(analyses: list[dict], folder_path: str) -> str:
    """
    Generates a complete Markdown documentation file from all analyses.

    Args:
        analyses: List of analysis dicts from analyzer.analyze_all()
        folder_path: The source folder that was scanned (shown in the header)

    Returns:
        The path to the written .md file
    """
    _ensure_output_dir()

    # Current timestamp for the "generated on" line
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Count only successfully analyzed files
    successful = [a for a in analyses if "error" not in a]
    file_count = len(analyses)

    # Build supporting data for the various sections
    dep_rows = _build_dep_table_rows(analyses)
    risks = _compile_risks(analyses)
    overview = _build_overview(analyses)

    # -------------------------------------------------------------------
    # Build the Markdown string section by section
    # -------------------------------------------------------------------

    # We use a list of strings and join at the end — it's faster than
    # concatenating strings one by one with +=
    lines = []

    # ---- HEADER ----
    lines.append("# Pipeline Documentation\n")
    lines.append(f"> Auto-generated by PipelineDoc on {timestamp}  ")
    lines.append(f"> Source folder: `{folder_path}`  ")
    lines.append(f"> Files analyzed: {file_count}  ")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ---- ECOSYSTEM OVERVIEW ----
    lines.append("## Pipeline Overview\n")
    lines.append(overview)
    lines.append("")
    lines.append("---")
    lines.append("")

    # ---- FILE-BY-FILE ANALYSIS ----
    lines.append("## File-by-File Analysis\n")

    for item in analyses:
        filename = item.get("filename", "unknown")
        purpose = item.get("purpose", "").strip()
        sources = item.get("sources", "").strip()
        analysis = item.get("analysis", "").strip()

        lines.append(f"### {filename}\n")

        if purpose:
            lines.append(f"**Purpose:** {purpose}  ")
        if sources:
            lines.append(f"**Data Sources:** {sources}  ")

        lines.append("")
        lines.append(analysis)
        lines.append("")
        lines.append("---")
        lines.append("")

    # ---- DEPENDENCY MAP TABLE ----
    lines.append("## Dependency Map\n")
    lines.append("| File | Key Libraries & Dependencies | External Services & Sources |")
    lines.append("|------|------------------------------|------------------------------|")

    for row in dep_rows:
        # Escape pipe characters in cell content to avoid breaking the table
        filename = row["filename"].replace("|", "\\|")
        libraries = row["libraries"].replace("|", "\\|")
        services = row["services"].replace("|", "\\|")
        lines.append(f"| {filename} | {libraries} | {services} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    # ---- RISKS SECTION ----
    lines.append("## Risks & Watch Points\n")

    if risks:
        for risk in risks:
            lines.append(f"- {risk}")
    else:
        lines.append("_No specific risks were identified._")

    lines.append("")
    lines.append("---")
    lines.append("")

    # ---- FOOTER ----
    lines.append(
        "_Generated by [PipelineDoc](https://github.com/nks648/pipelinedoc) "
        "— free and open source_"
    )
    lines.append("")

    # Join all lines with newlines to produce the final document
    markdown_content = "\n".join(lines)

    # Write to disk
    with open(OUTPUT_MARKDOWN, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    return OUTPUT_MARKDOWN


# -------------------------------------------------------------------
# JINJA2 HTML TEMPLATE
# -------------------------------------------------------------------
# We define the HTML template as a Python string here so the project
# stays self-contained (no separate template file needed).
# Jinja2 uses {{ variable }} for substitution and {% for %} for loops.

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Pipeline Documentation</title>
  <style>
    /* ---- Reset & base ---- */
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      font-size: 16px;
      line-height: 1.65;
      color: #1a1a2e;
      background: #f8f9fc;
    }

    /* ---- Layout ---- */
    .container { max-width: 960px; margin: 0 auto; padding: 2rem 1.5rem; }

    /* ---- Header ---- */
    header {
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      color: white;
      padding: 3rem 2rem;
      border-radius: 12px;
      margin-bottom: 2.5rem;
      box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }
    header h1 { font-size: 2.2rem; font-weight: 700; margin-bottom: 0.5rem; }
    header .meta { opacity: 0.75; font-size: 0.9rem; margin-top: 0.75rem; }
    header .meta span { display: inline-block; margin-right: 1.5rem; }

    /* ---- Sections ---- */
    .section {
      background: white;
      border-radius: 10px;
      padding: 2rem;
      margin-bottom: 2rem;
      box-shadow: 0 2px 10px rgba(0,0,0,0.07);
    }
    .section h2 {
      font-size: 1.4rem;
      font-weight: 700;
      margin-bottom: 1.25rem;
      padding-bottom: 0.75rem;
      border-bottom: 2px solid #e8ecf0;
      color: #16213e;
    }

    /* ---- File cards ---- */
    .file-card {
      border: 1px solid #e8ecf0;
      border-radius: 8px;
      padding: 1.5rem;
      margin-bottom: 1.5rem;
      transition: box-shadow 0.2s ease;
    }
    .file-card:hover { box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
    .file-card h3 {
      font-size: 1.1rem;
      font-weight: 600;
      color: #0f3460;
      margin-bottom: 0.75rem;
      font-family: "SFMono-Regular", Consolas, monospace;
    }
    .badge {
      display: inline-block;
      background: #e8f4fd;
      color: #0f6cbd;
      border-radius: 4px;
      padding: 0.15rem 0.5rem;
      font-size: 0.8rem;
      font-weight: 600;
      margin-bottom: 0.6rem;
      margin-right: 0.4rem;
    }
    .file-meta { margin-bottom: 0.75rem; }
    .file-meta .label { font-weight: 600; color: #444; }
    .analysis-text {
      font-size: 0.92rem;
      color: #333;
      white-space: pre-wrap;
      background: #f8f9fc;
      border-radius: 6px;
      padding: 1rem;
      margin-top: 0.75rem;
      border-left: 3px solid #0f6cbd;
    }

    /* ---- Overview ---- */
    .overview-text {
      font-size: 1rem;
      color: #333;
      background: #f0f7ff;
      border-radius: 8px;
      padding: 1.25rem;
      border-left: 4px solid #0f6cbd;
    }

    /* ---- Dependency table ---- */
    table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    th {
      background: #1a1a2e;
      color: white;
      text-align: left;
      padding: 0.75rem 1rem;
    }
    th:first-child { border-radius: 6px 0 0 0; }
    th:last-child  { border-radius: 0 6px 0 0; }
    td { padding: 0.65rem 1rem; border-bottom: 1px solid #e8ecf0; }
    tr:hover td { background: #f8f9fc; }
    td:first-child { font-family: monospace; font-size: 0.85rem; color: #0f3460; }

    /* ---- Risks ---- */
    .risk-item {
      padding: 0.65rem 1rem;
      border-left: 3px solid #e74c3c;
      background: #fff8f8;
      border-radius: 0 6px 6px 0;
      margin-bottom: 0.65rem;
      font-size: 0.92rem;
    }
    .risk-item strong { color: #c0392b; }

    /* ---- Footer ---- */
    footer {
      text-align: center;
      padding: 2rem;
      color: #888;
      font-size: 0.85rem;
    }
    footer a { color: #0f6cbd; text-decoration: none; }
    footer a:hover { text-decoration: underline; }
  </style>
</head>
<body>
<div class="container">

  <!-- HEADER -->
  <header>
    <h1>Pipeline Documentation</h1>
    <div class="meta">
      <span>Generated: {{ timestamp }}</span>
      <span>Source: <code>{{ folder_path }}</code></span>
      <span>Files: {{ file_count }}</span>
    </div>
  </header>

  <!-- OVERVIEW -->
  <div class="section">
    <h2>Pipeline Overview</h2>
    <div class="overview-text">{{ overview }}</div>
  </div>

  <!-- FILE-BY-FILE ANALYSIS -->
  <div class="section">
    <h2>File-by-File Analysis</h2>
    {% for item in analyses %}
    <div class="file-card">
      <h3>{{ item.filename }}</h3>
      {% if item.purpose %}
      <div class="file-meta">
        <span class="label">Purpose:</span> {{ item.purpose }}
      </div>
      {% endif %}
      {% if item.sources %}
      <div class="file-meta">
        <span class="label">Data Sources:</span> {{ item.sources }}
      </div>
      {% endif %}
      {% if item.analysis %}
      <div class="analysis-text">{{ item.analysis }}</div>
      {% endif %}
    </div>
    {% endfor %}
  </div>

  <!-- DEPENDENCY TABLE -->
  <div class="section">
    <h2>Dependency Map</h2>
    <table>
      <thead>
        <tr>
          <th>File</th>
          <th>Key Libraries &amp; Dependencies</th>
          <th>External Services &amp; Sources</th>
        </tr>
      </thead>
      <tbody>
        {% for row in dep_rows %}
        <tr>
          <td>{{ row.filename }}</td>
          <td>{{ row.libraries }}</td>
          <td>{{ row.services }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <!-- RISKS -->
  <div class="section">
    <h2>Risks &amp; Watch Points</h2>
    {% if risks %}
      {% for risk in risks %}
      <div class="risk-item">{{ risk }}</div>
      {% endfor %}
    {% else %}
      <p><em>No specific risks were identified.</em></p>
    {% endif %}
  </div>

  <footer>
    Generated by <a href="https://github.com/nks648/pipelinedoc" target="_blank">PipelineDoc</a>
    — free and open source
  </footer>

</div>
</body>
</html>"""


# -------------------------------------------------------------------
# MAIN FUNCTION 2: Render HTML
# -------------------------------------------------------------------

def render_html(analyses: list[dict], folder_path: str) -> str:
    """
    Generates a styled HTML documentation page from all analyses.

    Uses Jinja2 to fill in the HTML_TEMPLATE string defined above.

    Args:
        analyses: List of analysis dicts from analyzer.analyze_all()
        folder_path: The source folder that was scanned

    Returns:
        The path to the written .html file
    """
    _ensure_output_dir()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_count = len(analyses)

    dep_rows = _build_dep_table_rows(analyses)
    risks = _compile_risks(analyses)
    overview = _build_overview(analyses)

    # Create a Jinja2 environment that loads templates from a string
    # BaseLoader means "don't look for templates on disk — we'll provide the string"
    env = Environment(loader=BaseLoader(), autoescape=True)

    # Parse the template string into a Template object
    template = env.from_string(HTML_TEMPLATE)

    # Render the template by providing all the variables it references
    # ({{ timestamp }}, {{ analyses }}, etc.)
    html_content = template.render(
        timestamp=timestamp,
        folder_path=folder_path,
        file_count=file_count,
        analyses=analyses,
        dep_rows=dep_rows,
        risks=risks,
        overview=overview,
    )

    # Write to disk
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)

    return OUTPUT_HTML
