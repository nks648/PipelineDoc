"""
config.py — Central configuration for PipelineDoc
--------------------------------------------------
This module does two things:
  1. Loads secrets (like your API key) from a .env file or environment variables
  2. Defines constants used throughout the whole project

Why have a config file?
  Instead of hardcoding values like output folder names or model names in
  multiple places, we define them once here. If you ever want to change the
  output folder from "output" to "docs", you change it in one place.
"""

import os  # Standard library: used to read environment variables
from dotenv import load_dotenv  # Third-party: reads .env files into os.environ

# -------------------------------------------------------------------
# Step 1: Load .env file
# -------------------------------------------------------------------
# load_dotenv() looks for a file called ".env" in the current directory
# and loads each line (like ANTHROPIC_API_KEY=sk-...) into os.environ.
# If the key is already set in the real environment, it won't overwrite it.
# This means production environments can set keys directly without a .env file.
load_dotenv()


# -------------------------------------------------------------------
# Step 2: Read the API key from the environment
# -------------------------------------------------------------------
# os.getenv() returns the value of an environment variable, or None if missing.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# -------------------------------------------------------------------
# Step 3: Validation function — called only when the API key is needed
# -------------------------------------------------------------------
# We do NOT raise at import time because modules like parser.py import
# config.py but never touch the API. Raising at import time would break
# `pytest` and any code that only uses the parser or renderer.
# Instead, analyzer.py calls this function before making its first API call.
def require_api_key() -> str:
    """
    Returns the API key if set, or raises a clear, friendly error if missing.

    Call this only in code that actually needs the Anthropic API (analyzer.py).
    Do NOT call it in parser.py, renderer.py, or tests.
    """
    if not ANTHROPIC_API_KEY:
        raise EnvironmentError(
            "\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ERROR: ANTHROPIC_API_KEY is not set\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "\n"
            "  PipelineDoc needs an Anthropic API key to analyze your files.\n"
            "\n"
            "  To fix this:\n"
            "    1. Copy .env.example to .env\n"
            "         cp .env.example .env\n"
            "\n"
            "    2. Open .env and paste your key:\n"
            "         ANTHROPIC_API_KEY=sk-ant-your-key-here\n"
            "\n"
            "    3. Get a key at: https://console.anthropic.com/\n"
            "\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
    return ANTHROPIC_API_KEY


# -------------------------------------------------------------------
# Step 3: Project-wide constants
# -------------------------------------------------------------------
# These are the "settings knobs" for the whole tool.
# You can change these values here and every other file picks up the change.

# Which file extensions are considered Python source files
SUPPORTED_EXTENSIONS = [".py"]

# The folder where generated documentation is saved
OUTPUT_DIR = "output"

# Full path for the generated Markdown file
OUTPUT_MARKDOWN = "output/pipeline-map.md"

# Full path for the generated HTML file
OUTPUT_HTML = "output/pipeline-map.html"

# Which Claude model to use for analysis
# claude-opus-4-6 is the most capable model as of 2025
MODEL = "claude-opus-4-6"

# Maximum number of tokens Claude can return in a single response
# 2000 tokens ≈ ~1500 words — enough for a detailed file summary
MAX_TOKENS = 2000
