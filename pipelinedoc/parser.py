"""
parser.py — Extracts structural information from Python source files
--------------------------------------------------------------------
This module reads .py files and pulls out the "skeleton" of the code
WITHOUT running it. We use Python's built-in `ast` module for this.

What is an AST?
  AST stands for Abstract Syntax Tree. When Python reads your code,
  it first converts it into a tree of objects representing the code's
  structure — functions, imports, assignments, etc. We can walk that
  tree to learn things about the code without executing it.

  Why not use regex?
    Regex on code is fragile. `import pandas` and `from pandas import DataFrame`
    are different patterns. The AST handles all valid Python syntax correctly.

Two main functions live here:
  - extract_structure(filepath)  → reads one file, returns a dict
  - scan_folder(folder_path)     → scans a directory, returns a list of dicts
"""

import ast          # Standard library: parses Python source into a syntax tree
import os           # Standard library: file path operations and directory walking
import re           # Standard library: used for URL detection via regular expressions

from pipelinedoc.config import SUPPORTED_EXTENSIONS


# -------------------------------------------------------------------
# HELPER: Find all string literals in the AST that look like URLs
# -------------------------------------------------------------------
# This regex matches strings that start with http:// or https://
URL_PATTERN = re.compile(r'https?://[^\s\'"<>]+')


def _find_urls(tree: ast.AST) -> list[str]:
    """
    Walk the entire AST looking for string literals that contain URLs.
    Returns a deduplicated list of URLs found anywhere in the file.
    """
    found_urls = []

    # ast.walk() visits every node in the tree, depth-first
    for node in ast.walk(tree):
        # ast.Constant represents any literal value: strings, numbers, booleans
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            # Search the string value for URL-shaped text
            matches = URL_PATTERN.findall(node.value)
            found_urls.extend(matches)

    # list(set(...)) removes duplicates; sorted() gives consistent ordering
    return sorted(list(set(found_urls)))


def _find_db_connections(tree: ast.AST) -> list[str]:
    """
    Look for common database connection strings in string literals.
    Returns a list of detected connection string prefixes.

    We check for common database URL schemes like:
      postgresql://, mysql://, sqlite:///, mongodb://, etc.
    """
    # These are the prefixes that signal a database connection string
    db_prefixes = [
        "postgresql://",
        "postgres://",
        "mysql://",
        "sqlite:///",
        "sqlite://",
        "mongodb://",
        "mongodb+srv://",
        "oracle://",
        "mssql://",
        "redshift://",
    ]

    found_dbs = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            for prefix in db_prefixes:
                # Check if this string starts with a known DB prefix
                if node.value.lower().startswith(prefix):
                    found_dbs.append(node.value)
                    break  # No need to check other prefixes once one matches

    return sorted(list(set(found_dbs)))


def _extract_function_calls(func_node: ast.FunctionDef) -> list[str]:
    """
    Given a function definition node, find all function/method calls inside it.

    Examples of what this catches:
      requests.get(url)   → "requests.get"
      pd.read_csv(path)   → "pd.read_csv"
      print("hello")      → "print"
    """
    calls = []

    for node in ast.walk(func_node):
        # ast.Call represents any function call expression
        if isinstance(node, ast.Call):
            # node.func is the thing being called
            if isinstance(node.func, ast.Attribute):
                # This handles calls like: obj.method()
                # node.func.value is "obj", node.func.attr is "method"
                if isinstance(node.func.value, ast.Name):
                    calls.append(f"{node.func.value.id}.{node.func.attr}")
                else:
                    # Could be chained: obj.attr.method() — just take the attr
                    calls.append(node.func.attr)
            elif isinstance(node.func, ast.Name):
                # This handles simple calls like: print(), open(), my_function()
                calls.append(node.func.id)

    # Deduplicate while preserving order using dict.fromkeys()
    return list(dict.fromkeys(calls))


# -------------------------------------------------------------------
# MAIN FUNCTION 1: Extract structure from a single file
# -------------------------------------------------------------------

def extract_structure(filepath: str) -> dict:
    """
    Reads a single Python file and returns a dictionary describing its structure.

    Args:
        filepath: Absolute or relative path to the .py file

    Returns:
        A dict with keys: filename, imports, functions, urls, db_connections,
        has_airflow, has_prefect, has_pandas, raw_summary

    Raises:
        Exception if the file cannot be read or parsed
    """

    # --- Read the raw source code from disk ---
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        source_code = f.read()

    # --- Parse the source code into an AST ---
    # ast.parse() converts the string of source code into a tree of objects.
    # If the file has a syntax error, this will raise a SyntaxError.
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        # Return a minimal dict so the rest of the pipeline can continue
        return {
            "filename": os.path.basename(filepath),
            "filepath": filepath,
            "error": f"Syntax error in file: {e}",
            "imports": [],
            "functions": [],
            "urls": [],
            "db_connections": [],
            "has_airflow": False,
            "has_prefect": False,
            "has_pandas": False,
            "raw_summary": source_code[:300],
        }

    # --- Collect imports ---
    imports = []

    for node in ast.walk(tree):
        # `import pandas` → ast.Import, names = [alias(name='pandas')]
        if isinstance(node, ast.Import):
            for alias in node.names:
                # alias.name might be "pandas" or "os.path"
                # We take just the top-level package name
                top_level = alias.name.split(".")[0]
                imports.append(top_level)

        # `from pandas import DataFrame` → ast.ImportFrom, module = 'pandas'
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top_level = node.module.split(".")[0]
                imports.append(top_level)

    # Deduplicate and sort for consistency
    imports = sorted(list(set(imports)))

    # --- Collect function definitions ---
    functions = []

    for node in ast.walk(tree):
        # ast.FunctionDef covers regular functions; ast.AsyncFunctionDef covers async
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Skip private/dunder methods if they're very common noise
            # (we keep them — they might be important in pipelines)

            # ast.get_docstring() reads the first string literal in a function body
            docstring = ast.get_docstring(node) or ""

            functions.append({
                "name": node.name,
                "calls": _extract_function_calls(node),
                "docstring": docstring[:200],  # Truncate very long docstrings
            })

    # --- Check for specific frameworks ---
    # A simple "is this library imported?" check
    imports_set = set(imports)

    has_airflow = "airflow" in imports_set
    has_prefect = "prefect" in imports_set
    has_pandas = "pandas" in imports_set or "pd" in imports_set

    # Also check import aliases — `import pandas as pd` appears as "pandas" in imports
    # but check raw source too for extra safety
    if "pandas" in source_code or "import pandas" in source_code:
        has_pandas = True

    # --- Find URLs and DB connections ---
    urls = _find_urls(tree)
    db_connections = _find_db_connections(tree)

    # --- Raw summary: first 300 characters of the file ---
    # This gives Claude a quick "feel" for the file even if ast misses something
    raw_summary = source_code[:300].strip()

    return {
        "filename": os.path.basename(filepath),
        "filepath": filepath,
        "imports": imports,
        "functions": functions,
        "urls": urls,
        "db_connections": db_connections,
        "has_airflow": has_airflow,
        "has_prefect": has_prefect,
        "has_pandas": has_pandas,
        "raw_summary": raw_summary,
    }


# -------------------------------------------------------------------
# MAIN FUNCTION 2: Scan an entire folder for Python files
# -------------------------------------------------------------------

# Directories we never want to look inside
SKIP_DIRS = {"__pycache__", ".git", ".venv", "venv", "node_modules", ".tox", "dist", "build", ".eggs"}

# Filename patterns to skip (test files, example files)
SKIP_FILENAME_PREFIXES = ("test_",)
SKIP_FILENAME_SUFFIXES = ("_test.py",)


def scan_folder(folder_path: str) -> list[dict]:
    """
    Recursively walks a folder and extracts the structure of every Python file.

    Skips:
      - Hidden/cache directories (__pycache__, .git, .venv, etc.)
      - Test files (files starting with test_ or ending with _test.py)

    Args:
        folder_path: Path to the directory to scan

    Returns:
        A list of dicts (one per file), each from extract_structure()
        Returns an empty list if no .py files are found.
    """

    # Validate the folder exists before walking it
    if not os.path.isdir(folder_path):
        raise ValueError(f"'{folder_path}' is not a valid directory.")

    results = []

    # os.walk() yields (current_dir, list_of_subdirs, list_of_files) for every
    # directory in the tree. We modify `dirs` in-place to skip unwanted folders.
    for current_dir, subdirs, files in os.walk(folder_path):

        # --- Prune directories we don't want to descend into ---
        # We modify subdirs IN PLACE (important!) so os.walk won't enter them.
        # Using list comprehension to keep only dirs NOT in our skip set.
        subdirs[:] = [
            d for d in subdirs
            if d not in SKIP_DIRS and not d.startswith(".")
        ]

        # --- Process each file in the current directory ---
        for filename in files:
            # Get the file extension, e.g. ".py"
            _, ext = os.path.splitext(filename)

            # Skip files that aren't Python source files
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            # Skip test files
            if filename.startswith(SKIP_FILENAME_PREFIXES):
                continue
            if filename.endswith(SKIP_FILENAME_SUFFIXES):
                continue

            # Build the full path to this file
            full_path = os.path.join(current_dir, filename)

            # Extract structure and add to results
            try:
                structure = extract_structure(full_path)
                results.append(structure)
            except Exception as e:
                # Don't crash the whole scan if one file fails
                results.append({
                    "filename": filename,
                    "filepath": full_path,
                    "error": str(e),
                    "imports": [],
                    "functions": [],
                    "urls": [],
                    "db_connections": [],
                    "has_airflow": False,
                    "has_prefect": False,
                    "has_pandas": False,
                    "raw_summary": "",
                })

    return results
