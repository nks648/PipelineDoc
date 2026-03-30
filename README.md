# PipelineDoc

**Auto-generate living documentation for your Python data pipelines using Claude AI.**

You point PipelineDoc at a folder of `.py` files. It reads every file, sends the structure to Claude, and writes a clean Markdown + HTML documentation page explaining what each pipeline does, where data comes from, where it goes, and what could break.

No manual writing. No stale docs. Every git push regenerates everything automatically.

---

## Table of Contents

1. [What it produces](#what-it-produces)
2. [Before you start — requirements](#before-you-start--requirements)
3. [Step 1 — Get the code](#step-1--get-the-code)
4. [Step 2 — Create a virtual environment](#step-2--create-a-virtual-environment)
5. [Step 3 — Install PipelineDoc](#step-3--install-pipelinedoc)
6. [Step 4 — Get an Anthropic API key](#step-4--get-an-anthropic-api-key)
7. [Step 5 — Configure your API key](#step-5--configure-your-api-key)
8. [Step 6 — Run it on the examples](#step-6--run-it-on-the-examples)
9. [Step 7 — Run it on your own pipelines](#step-7--run-it-on-your-own-pipelines)
10. [Step 8 — Set up automatic docs on every git push](#step-8--set-up-automatic-docs-on-every-git-push)
11. [All CLI options](#all-cli-options)
12. [How it works internally](#how-it-works-internally)
13. [Running the tests](#running-the-tests)
14. [Troubleshooting](#troubleshooting)

---

## What it produces

After running PipelineDoc you get two files in the `output/` folder:

**`output/pipeline-map.md`** — a Markdown document with:
- A one-paragraph overview of your entire pipeline ecosystem
- A card for each file: purpose, data sources, full AI analysis
- A dependency table listing libraries and external services per file
- A compiled risks section pulling together every warning across all files

**`output/pipeline-map.html`** — the same content as a styled web page you can open in any browser or share with teammates who don't use a code editor.

---

## Before you start — requirements

| Requirement | Why |
|---|---|
| Python 3.11 or newer | The code uses modern Python syntax |
| git | To clone this repository |
| An Anthropic API key | PipelineDoc uses Claude to analyze your files |
| Internet connection | To reach the Claude API |

**Check your Python version:**
```bash
python --version
# You need 3.11 or higher
# If you see 2.x or 3.10 or lower, install a newer Python first
```

**Don't have Python 3.11+?**
- Mac: `brew install python@3.11`
- Windows: Download from [python.org](https://www.python.org/downloads/)
- Linux: `sudo apt install python3.11` (Ubuntu/Debian)

---

## Step 1 — Get the code

Open your terminal and run:

```bash
git clone https://github.com/nks648/pipelinedoc.git
cd pipelinedoc
```

You should now be inside the `pipelinedoc/` folder. Verify it:

```bash
ls
# You should see: README.md  pyproject.toml  pipelinedoc/  examples/  tests/  output/
```

---

## Step 2 — Create a virtual environment

A virtual environment keeps PipelineDoc's dependencies separate from other Python projects on your machine. This prevents version conflicts.

**Mac / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (Command Prompt):**
```bash
python -m venv .venv
.venv\Scripts\activate.bat
```

**Windows (PowerShell):**
```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
```

After activating, your terminal prompt will change to show `(.venv)` at the start. That means it's working.

> **Tip:** Every time you open a new terminal window to use PipelineDoc, you need to run the `activate` command again. The virtual environment only stays active in the current terminal session.

---

## Step 3 — Install PipelineDoc

With your virtual environment active, run:

```bash
pip install -e .
```

The `-e` flag means "editable install" — it installs the package but links it directly to this folder. If you edit any source files, the changes take effect immediately without reinstalling.

This will install these dependencies automatically:
- `anthropic` — the official Python client for the Claude API
- `click` — builds the `pipelinedoc` command-line interface
- `rich` — prints colored output and progress bars in the terminal
- `python-dotenv` — reads your `.env` file to load your API key
- `jinja2` — generates the HTML output from a template

**Verify the install worked:**
```bash
pipelinedoc --help
```

You should see:
```
Usage: pipelinedoc [OPTIONS] COMMAND [ARGS]...

  PipelineDoc — Auto-generate documentation for Python data pipelines.
  ...
```

If you see `command not found`, make sure your virtual environment is activated (check for `(.venv)` in your prompt).

---

## Step 4 — Get an Anthropic API key

PipelineDoc uses Claude to read and understand your pipeline files. You need an API key to use it.

1. Go to [console.anthropic.com](https://console.anthropic.com/)
2. Sign up or log in
3. Click **API Keys** in the left sidebar
4. Click **Create Key**
5. Give it a name like `pipelinedoc`
6. Copy the key — it starts with `sk-ant-...`

> **Keep this key secret.** Never paste it into a file you commit to git. Never share it. The `.env` file you'll create in the next step is already listed in `.gitignore` so git will never see it.

---

## Step 5 — Configure your API key

PipelineDoc reads your API key from a `.env` file. Create it from the template:

```bash
cp .env.example .env
```

Now open `.env` in any text editor:

```bash
# Mac / Linux
open .env          # opens in default editor
nano .env          # or use nano in the terminal

# Windows
notepad .env
```

The file looks like this:
```
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

Replace `your-anthropic-api-key-here` with your actual key:
```
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Save the file. That's it — PipelineDoc will read this automatically every time it runs.

**Verify the key is loaded correctly:**
```bash
pipelinedoc version
# Should print: PipelineDoc version 0.1.0
# (If the key is missing, you'd see an error here)
```

---

## Step 6 — Run it on the examples

The repo includes two realistic example pipeline files in the `examples/` folder. Try running PipelineDoc on them first to confirm everything works before pointing it at your own code.

```bash
pipelinedoc run ./examples
```

You'll see output like this in your terminal:

```
╭─────────────────────────────────────────────────────╮
│ PipelineDoc — AI-powered pipeline documentation     │
╰─────────────────────────────────────────────────────╯

Step 1/3  Scanning folder: ./examples
   Found 2 Python file(s) to analyze.

Step 2/3  Sending files to Claude for analysis...
  Analyzing etl_pipeline.py  ████████████████  1/2
  Analyzing api_pipeline.py  ████████████████  2/2

Step 3/3  Generating documentation...
   ✓  Markdown: output/pipeline-map.md
   ✓  HTML:     output/pipeline-map.html

╭── Done ──────────────────────────────────────────────╮
│ Documentation generated!                             │
│   Files analyzed:  2 succeeded                       │
│   Markdown output: output/pipeline-map.md            │
│   HTML output:     output/pipeline-map.html          │
╰──────────────────────────────────────────────────────╯
```

**View the Markdown output:**
```bash
cat output/pipeline-map.md
```

**View the HTML output** — open it in your browser:
```bash
# Mac
open output/pipeline-map.html

# Windows
start output/pipeline-map.html

# Linux
xdg-open output/pipeline-map.html
```

---

## Step 7 — Run it on your own pipelines

Point PipelineDoc at any folder containing `.py` files:

```bash
pipelinedoc run /path/to/your/pipelines
```

**Examples:**

```bash
# Current directory
pipelinedoc run .

# A subfolder of the current project
pipelinedoc run ./src/pipelines

# An absolute path
pipelinedoc run /home/you/projects/etl/pipelines

# Save docs to a custom folder instead of output/
pipelinedoc run ./pipelines --output-dir ./docs

# Skip the HTML file (faster, Markdown only)
pipelinedoc run ./pipelines --no-html

# Show a table of discovered files before analyzing
pipelinedoc run ./pipelines --verbose
```

**What files does PipelineDoc scan?**

It scans every `.py` file it finds, and automatically skips:
- `__pycache__/` directories
- `.git/`, `.venv/`, `node_modules/` directories
- Files whose names start with `test_` (your test files)

**How much does it cost?**

Each file uses roughly 1,000–3,000 tokens (input + output). At current Claude Opus pricing, analyzing 10 files costs about $0.05–$0.15. Check [anthropic.com/pricing](https://www.anthropic.com/pricing) for current rates.

---

## Step 8 — Set up automatic docs on every git push

The `.github/workflows/doc-gen.yml` file already contains a GitHub Actions workflow. Once configured, every push to your `main` branch will automatically regenerate your documentation and commit it back to the repo.

### 8a. Add your API key as a GitHub secret

Your `.env` file is never committed to git (it's in `.gitignore`). GitHub Actions needs the key through a different mechanism: repository secrets.

1. Go to your repository on GitHub
2. Click **Settings** (top menu of the repo page)
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Name: `ANTHROPIC_API_KEY`
6. Value: paste your `sk-ant-...` key
7. Click **Add secret**

### 8b. Tell the workflow where your pipelines live

Open `.github/workflows/doc-gen.yml` and find this line:

```yaml
PIPELINE_FOLDER: ${{ github.event.inputs.pipeline_folder || 'pipelines' }}
```

Change `'pipelines'` to match your actual folder name. For example, if your pipeline files are in `src/etl/`:

```yaml
PIPELINE_FOLDER: ${{ github.event.inputs.pipeline_folder || 'src/etl' }}
```

### 8c. Push to trigger it

```bash
git add .github/workflows/doc-gen.yml
git commit -m "configure pipeline folder for doc-gen workflow"
git push
```

Go to your repo on GitHub → **Actions** tab → you'll see the workflow running. When it finishes, the generated `output/pipeline-map.md` and `output/pipeline-map.html` files will be committed back to your repo automatically.

### 8d. Run it manually anytime

You can also trigger it on demand without pushing code:

1. GitHub → **Actions** tab
2. Click **Generate Pipeline Documentation** in the left sidebar
3. Click **Run workflow** → **Run workflow**

---

## All CLI options

```
pipelinedoc run [OPTIONS] [FOLDER]

  Scan FOLDER and generate documentation for all Python pipeline files.
  FOLDER defaults to the current directory if not specified.

Arguments:
  FOLDER        Path to the folder to scan. Defaults to "."

Options:
  --output-dir  PATH    Save output files to this folder instead of ./output
  --no-html             Only generate Markdown, skip the HTML file
  --verbose, -v         Show a table of discovered files before analyzing
  --help                Show this message and exit

Other commands:
  pipelinedoc version   Show the installed version
  pipelinedoc --help    Show all commands
```

---

## How it works internally

Understanding the internals helps if something breaks or you want to extend it.

```
Your .py files
      │
      ▼
 parser.py          Reads each file using Python's AST module.
                    Extracts: imports, function names, function calls,
                    URLs in strings, database connection strings,
                    framework flags (Airflow, Prefect, Pandas).
                    Never runs your code.
      │
      ▼
 analyzer.py        Sends each file's extracted structure to Claude
                    as a structured prompt. Parses the response to
                    extract 6 sections: PURPOSE, DATA SOURCES,
                    TRANSFORMATIONS, OUTPUT, DEPENDENCIES, RISKS.
      │
      ▼
 renderer.py        Takes all analyses and builds the final documents.
                    render_markdown() → output/pipeline-map.md
                    render_html()     → output/pipeline-map.html
```

**File layout:**
```
pipelinedoc/
├── pipelinedoc/
│   ├── config.py       Loads .env, defines constants (model name, output paths)
│   ├── parser.py       AST-based code structure extractor
│   ├── analyzer.py     Claude API calls, prompt engineering, response parsing
│   ├── renderer.py     Markdown and HTML generation (Jinja2 for HTML)
│   └── cli.py          The `pipelinedoc` command (built with Click)
├── examples/
│   ├── etl_pipeline.py     Example: Salesforce API → pandas → PostgreSQL
│   └── api_pipeline.py     Example: Stripe + Weather APIs → SQLite + JSON
├── tests/
│   ├── test_parser.py       27 unit tests for the parser (no API calls needed)
│   └── sample_pipeline.py   The test fixture file the tests run against
├── output/
│   └── .gitkeep            Keeps the output/ folder in git while ignoring its contents
├── .github/workflows/
│   └── doc-gen.yml         GitHub Actions: auto-generate docs on every push
├── pyproject.toml          Package definition and dependencies
├── .env.example            Template for your .env file
└── .gitignore              Prevents secrets and build artifacts from being committed
```

---

## Running the tests

The test suite covers the parser module. It runs entirely offline — no API key or internet connection needed.

```bash
# Install dev dependencies (adds pytest)
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=pipelinedoc --cov-report=term-missing
```

Expected output: **27 passed**.

---

## Troubleshooting

**`command not found: pipelinedoc`**
Your virtual environment isn't active. Run `source .venv/bin/activate` (Mac/Linux) or `.venv\Scripts\activate` (Windows) first.

---

**`ERROR: ANTHROPIC_API_KEY is not set`**
Your `.env` file is missing or the key isn't set correctly. Check:
```bash
cat .env
# Should show: ANTHROPIC_API_KEY=sk-ant-...
```
Make sure there are no spaces around the `=` sign.

---

**`No Python files found in the specified folder`**
The folder path you passed is empty or contains no `.py` files. Check:
```bash
ls ./your-folder
# Do you see any .py files listed?
```

---

**API errors / rate limits**
If Claude returns a rate limit error, PipelineDoc waits 10 seconds and retries once. If it fails again, it logs a warning and continues to the next file — it won't crash. Check your [Anthropic console](https://console.anthropic.com/) usage limits if this happens repeatedly.

---

**GitHub Actions workflow isn't triggering**
The workflow only runs when `.py` files change (to save API costs). Push a change to a `.py` file, or trigger it manually from the Actions tab.

---

**The HTML file looks broken**
Try opening it by double-clicking in your file explorer rather than via a terminal command. Some terminal `open` commands don't set the correct MIME type.

---

## License

MIT — free to use, modify, and distribute.
