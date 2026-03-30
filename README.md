# PipelineDoc

**Auto-generate living documentation for your Python data pipelines using Claude AI.**

PipelineDoc scans a folder of Python ETL/pipeline/API scripts, uses Claude to understand what each file does, and generates a clean Markdown + HTML documentation site — automatically, on every git push.

---

## What it does

1. **Scans** your pipeline folder — finds all `.py` files using Python's AST (no running your code)
2. **Analyzes** each file with Claude — gets a plain-English breakdown of purpose, data sources, transformations, outputs, dependencies, and risks
3. **Renders** a `pipeline-map.md` and `pipeline-map.html` with:
   - A full ecosystem overview
   - Per-file analysis cards
   - A dependency map table
   - A compiled risks section
4. **Stays current** via a GitHub Action that runs on every push

---

## Quick Start

### 1. Install

```bash
# Clone the repo
git clone https://github.com/nks648/pipelinedoc.git
cd pipelinedoc

# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate

# Install the package and its dependencies
pip install -e .
```

### 2. Configure your API key

```bash
cp .env.example .env
# Now open .env and paste your Anthropic API key
# Get one at: https://console.anthropic.com/
```

### 3. Run it

```bash
# Analyze the included examples
pipelinedoc run ./examples

# Analyze your own pipeline folder
pipelinedoc run ./my_pipelines

# Options
pipelinedoc run ./pipelines --no-html          # Skip HTML output
pipelinedoc run ./pipelines --output-dir docs  # Custom output folder
pipelinedoc run ./pipelines --verbose          # Show file details
```

### 4. View the output

```
output/
├── pipeline-map.md    ← Open in VS Code, GitHub, Obsidian
└── pipeline-map.html  ← Open in any browser
```

---

## Automatic docs via GitHub Actions

Add your `ANTHROPIC_API_KEY` as a GitHub repository secret, then every push to `main` will regenerate your documentation automatically.

**Setup:**
1. GitHub repo → Settings → Secrets and variables → Actions
2. Add secret: `ANTHROPIC_API_KEY` = your key
3. The workflow in `.github/workflows/doc-gen.yml` handles the rest

> Change `PIPELINE_FOLDER` in the workflow file to match your actual pipelines directory.

---

## Project Structure

```
pipelinedoc/
├── pipelinedoc/
│   ├── config.py       # API key loading, constants
│   ├── parser.py       # AST-based code structure extraction
│   ├── analyzer.py     # Claude API calls and response parsing
│   ├── renderer.py     # Markdown and HTML generation
│   └── cli.py          # Command-line interface (the `pipelinedoc` command)
├── examples/           # Sample pipeline files to test against
├── tests/              # Unit tests (run with: pytest)
├── output/             # Generated docs land here
└── .github/workflows/  # GitHub Actions CI
```

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

Tests cover the parser module thoroughly without making any API calls.

---

## Requirements

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)

---

## License

MIT — free to use, modify, and distribute.
