"""
analyzer.py — Sends parsed file structures to Claude for AI analysis
--------------------------------------------------------------------
This module is the bridge between the raw code structure (from parser.py)
and the human-readable documentation (from renderer.py).

It takes the dict that parser.py produces and:
  1. Formats it into a clear prompt for Claude
  2. Sends it to the Anthropic API
  3. Parses the response to extract key sections
  4. Returns a new dict with both the raw analysis and extracted fields

Two main functions:
  - analyze_file(structure)        → analyze one file
  - analyze_all(structures)        → analyze a list of files with a progress bar
"""

import time          # Standard library: used for sleep() when handling rate limits

import anthropic      # Anthropic SDK: the official client for Claude API calls
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.console import Console

from pipelinedoc.config import ANTHROPIC_API_KEY, MODEL, MAX_TOKENS

# Create a Rich console for printing colored output to the terminal
console = Console()

# Initialize the Anthropic client once (not inside the function, for efficiency)
# The client automatically uses ANTHROPIC_API_KEY from the environment
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _build_prompt(structure: dict) -> str:
    """
    Builds the prompt we send to Claude for a single file.

    We format the structure dict into readable text so Claude can understand
    the file's contents clearly. The prompt is carefully engineered to get
    specific, structured output that we can parse later.
    """

    # Format the list of functions as a readable string
    function_names = ", ".join(
        f["name"] for f in structure.get("functions", [])
    ) or "None detected"

    # Format URLs as a readable string
    urls = ", ".join(structure.get("urls", [])) or "None detected"

    # Format DB connections (truncate long connection strings for the prompt)
    db_list = structure.get("db_connections", [])
    db_connections = ", ".join(db[:60] for db in db_list) if db_list else "None detected"

    # Format imports
    imports = ", ".join(structure.get("imports", [])) or "None"

    # Build the full prompt string using an f-string (multiline)
    prompt = f"""You are a technical documentation expert analyzing a Python data pipeline file.

Here is the extracted structure of the file:
- Filename: {structure.get("filename", "unknown")}
- Imports used: {imports}
- Functions defined: {function_names}
- External URLs detected: {urls}
- Database connections detected: {db_connections}
- Uses Airflow: {structure.get("has_airflow", False)}
- Uses Prefect: {structure.get("has_prefect", False)}
- Uses Pandas: {structure.get("has_pandas", False)}
- File preview: {structure.get("raw_summary", "")}

Based on this, write a concise technical summary covering:
1. PURPOSE: What does this pipeline do in one sentence?
2. DATA SOURCES: Where does data come from? (APIs, databases, files, etc.)
3. TRANSFORMATIONS: What happens to the data in the middle?
4. OUTPUT: Where does the data go at the end?
5. DEPENDENCIES: What key libraries or services does this rely on?
6. RISKS: Any obvious failure points or things that could break?

Be specific. If you see a URL like https://api.stripe.com, say "Stripe API".
Do not say "the code does things with data." Be precise.
Write for a senior engineer reading this for the first time.

Format each section exactly as:
1. PURPOSE: <your answer>
2. DATA SOURCES: <your answer>
3. TRANSFORMATIONS: <your answer>
4. OUTPUT: <your answer>
5. DEPENDENCIES: <your answer>
6. RISKS: <your answer>"""

    return prompt


def _extract_section(analysis_text: str, section_number: int, section_name: str) -> str:
    """
    Extracts a specific numbered section from Claude's response text.

    For example, given analysis_text containing:
      "1. PURPOSE: Loads data from Stripe API..."
    and section_number=1, section_name="PURPOSE",
    this returns "Loads data from Stripe API..."

    Args:
        analysis_text: The full text response from Claude
        section_number: The number prefix of the section (1, 2, 3...)
        section_name: The section label (PURPOSE, DATA SOURCES, etc.)

    Returns:
        The extracted section text, or empty string if not found
    """
    import re

    # Build a pattern that matches "1. PURPOSE: <content until next numbered section>"
    # The (?:...) is a non-capturing group
    # The [^\n]* matches everything until the end of the line
    # We use MULTILINE and IGNORECASE flags for flexibility
    pattern = rf"{section_number}\.\s+{section_name}:\s*(.+?)(?=\n\d+\.|$)"

    match = re.search(pattern, analysis_text, re.IGNORECASE | re.DOTALL)

    if match:
        # Strip whitespace and return the captured content
        return match.group(1).strip()

    return ""


# -------------------------------------------------------------------
# MAIN FUNCTION 1: Analyze a single file
# -------------------------------------------------------------------

def analyze_file(structure: dict) -> dict:
    """
    Sends one file's structure to Claude and returns an analysis dict.

    Args:
        structure: The dict produced by parser.extract_structure()

    Returns:
        A dict with keys:
          - filename: the file's name
          - analysis: Claude's full response text
          - purpose: just the PURPOSE section
          - sources: just the DATA SOURCES section
          - transformations: just the TRANSFORMATIONS section
          - output: just the OUTPUT section
          - dependencies: just the DEPENDENCIES section
          - risks: just the RISKS section
          - error: set only if something went wrong
    """

    filename = structure.get("filename", "unknown")

    # If the parser flagged an error on this file, skip the API call
    if "error" in structure:
        return {
            "filename": filename,
            "analysis": f"Could not analyze: {structure['error']}",
            "purpose": "Parse error — see analysis field",
            "sources": "",
            "transformations": "",
            "output": "",
            "dependencies": "",
            "risks": "",
            "error": structure["error"],
        }

    # Build the prompt for this file
    prompt = _build_prompt(structure)

    # --- Call the Claude API ---
    # client.messages.create() is the main API call.
    # - model: which Claude model to use
    # - max_tokens: maximum length of the response
    # - messages: a list of conversation turns (we just have one user message)
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )

    # The response object has a .content list; each item is a content block.
    # For text responses, we want the first block's .text attribute.
    analysis_text = response.content[0].text

    # --- Extract individual sections from the full analysis ---
    purpose = _extract_section(analysis_text, 1, "PURPOSE")
    sources = _extract_section(analysis_text, 2, "DATA SOURCES")
    transformations = _extract_section(analysis_text, 3, "TRANSFORMATIONS")
    output = _extract_section(analysis_text, 4, "OUTPUT")
    dependencies = _extract_section(analysis_text, 5, "DEPENDENCIES")
    risks = _extract_section(analysis_text, 6, "RISKS")

    return {
        "filename": filename,
        "analysis": analysis_text,
        "purpose": purpose,
        "sources": sources,
        "transformations": transformations,
        "output": output,
        "dependencies": dependencies,
        "risks": risks,
    }


# -------------------------------------------------------------------
# MAIN FUNCTION 2: Analyze all files with a progress bar
# -------------------------------------------------------------------

def analyze_all(structures: list[dict]) -> list[dict]:
    """
    Analyzes every file structure in the list, showing a progress bar.

    Handles errors gracefully:
      - Rate limit errors: waits 10 seconds and retries once
      - Other errors: logs them and continues to the next file

    Args:
        structures: List of dicts from parser.scan_folder()

    Returns:
        List of analysis dicts (one per file)
    """

    results = []

    # Rich Progress creates a multi-column progress bar in the terminal.
    # SpinnerColumn: shows a spinning animation
    # TextColumn: shows the current file being processed
    # BarColumn: the visual progress bar
    # TaskProgressColumn: shows "3/10" style count
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:

        # Create a task in the progress bar with the total number of files
        task = progress.add_task(
            "Analyzing files with Claude...",
            total=len(structures)
        )

        for structure in structures:
            filename = structure.get("filename", "unknown")

            # Update the progress bar description to show current file
            progress.update(task, description=f"Analyzing [cyan]{filename}[/cyan]")

            try:
                # --- First attempt ---
                analysis = analyze_file(structure)
                results.append(analysis)

            except anthropic.RateLimitError:
                # Rate limit hit: Claude is telling us to slow down.
                # Wait 10 seconds and try once more before giving up.
                console.print(
                    f"\n[yellow]⚠️  Rate limit hit on {filename}. "
                    f"Waiting 10 seconds...[/yellow]"
                )
                time.sleep(10)

                try:
                    # --- Retry after waiting ---
                    analysis = analyze_file(structure)
                    results.append(analysis)
                except Exception as retry_error:
                    console.print(
                        f"[red]✗ Failed again on {filename}: {retry_error}[/red]"
                    )
                    # Add a placeholder result so the file still appears in output
                    results.append({
                        "filename": filename,
                        "analysis": f"Analysis failed after retry: {retry_error}",
                        "purpose": "Analysis failed",
                        "sources": "",
                        "transformations": "",
                        "output": "",
                        "dependencies": "",
                        "risks": "",
                        "error": str(retry_error),
                    })

            except anthropic.APIConnectionError as e:
                console.print(f"[red]✗ Network error on {filename}: {e}[/red]")
                results.append({
                    "filename": filename,
                    "analysis": f"Network error: {e}",
                    "purpose": "Analysis failed — network error",
                    "sources": "",
                    "transformations": "",
                    "output": "",
                    "dependencies": "",
                    "risks": "",
                    "error": str(e),
                })

            except Exception as e:
                # Catch-all: log the error and keep going
                console.print(f"[red]✗ Error analyzing {filename}: {e}[/red]")
                results.append({
                    "filename": filename,
                    "analysis": f"Analysis error: {e}",
                    "purpose": "Analysis failed",
                    "sources": "",
                    "transformations": "",
                    "output": "",
                    "dependencies": "",
                    "risks": "",
                    "error": str(e),
                })

            # Advance the progress bar by 1 regardless of success/failure
            progress.advance(task)

    return results
