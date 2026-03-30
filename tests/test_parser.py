"""
test_parser.py — Unit tests for pipelinedoc/parser.py
------------------------------------------------------
These tests verify that the parser correctly extracts structure from
real Python files without calling the Claude API (tests should be fast
and free to run).

We use the sample_pipeline.py file in this same tests/ directory as
our test fixture — a known file with predictable contents.

Run tests with:
    pytest tests/
    pytest tests/ -v        (verbose: shows each test name)
    pytest tests/ --cov     (with coverage report)
"""

import os
import pytest

# The function we're testing
from pipelinedoc.parser import extract_structure, scan_folder

# Build the absolute path to our test fixture file.
# os.path.dirname(__file__) gives us the directory this test file is in.
# We then join it with the sample file name.
SAMPLE_FILE = os.path.join(os.path.dirname(__file__), "sample_pipeline.py")
TESTS_DIR = os.path.dirname(__file__)


# ============================================================
# Tests for extract_structure()
# ============================================================

class TestExtractStructure:
    """Tests for the single-file structure extractor."""

    def setup_method(self):
        """
        setup_method() runs before each test method in this class.
        We parse the sample file once and store the result so every
        test doesn't have to re-parse it.
        """
        self.result = extract_structure(SAMPLE_FILE)

    def test_returns_dict(self):
        """The function should always return a dictionary."""
        assert isinstance(self.result, dict)

    def test_filename_correct(self):
        """Should extract just the filename, not the full path."""
        assert self.result["filename"] == "sample_pipeline.py"

    def test_filepath_is_absolute(self):
        """The filepath key should hold the full path."""
        assert "filepath" in self.result
        assert self.result["filepath"].endswith("sample_pipeline.py")

    def test_detects_pandas_import(self):
        """Should detect `import pandas as pd` as a pandas import."""
        assert "pandas" in self.result["imports"]

    def test_detects_requests_import(self):
        """Should detect `import requests`."""
        assert "requests" in self.result["imports"]

    def test_detects_os_import(self):
        """Should detect `import os`."""
        assert "os" in self.result["imports"]

    def test_detects_sqlalchemy_import(self):
        """Should detect `from sqlalchemy import create_engine`."""
        assert "sqlalchemy" in self.result["imports"]

    def test_imports_are_deduplicated(self):
        """If a library is imported twice, it should only appear once."""
        imports = self.result["imports"]
        assert len(imports) == len(set(imports)), "Imports contain duplicates"

    def test_detects_functions(self):
        """Should find all top-level function definitions."""
        function_names = [f["name"] for f in self.result["functions"]]
        assert "fetch_records" in function_names
        assert "clean_records" in function_names
        assert "save_to_db" in function_names
        assert "main" in function_names

    def test_function_has_required_keys(self):
        """Each function dict should have name, calls, and docstring."""
        for func in self.result["functions"]:
            assert "name" in func
            assert "calls" in func
            assert "docstring" in func

    def test_function_docstrings_extracted(self):
        """Should extract docstrings from functions."""
        func_map = {f["name"]: f for f in self.result["functions"]}
        # fetch_records has a docstring in sample_pipeline.py
        assert "Fetches raw records" in func_map["fetch_records"]["docstring"]

    def test_function_calls_detected(self):
        """Should detect function calls inside function bodies."""
        func_map = {f["name"]: f for f in self.result["functions"]}
        # fetch_records calls requests.get
        fetch_calls = func_map["fetch_records"]["calls"]
        assert any("get" in call for call in fetch_calls), (
            f"Expected 'requests.get' in calls, got: {fetch_calls}"
        )

    def test_detects_url(self):
        """Should find the https://api.example.com URL in the file."""
        assert len(self.result["urls"]) > 0
        assert any("api.example.com" in url for url in self.result["urls"])

    def test_detects_db_connection(self):
        """Should detect the postgresql:// connection string."""
        assert len(self.result["db_connections"]) > 0
        assert any(
            "postgresql://" in conn
            for conn in self.result["db_connections"]
        )

    def test_has_pandas_flag(self):
        """has_pandas should be True since sample_pipeline imports pandas."""
        assert self.result["has_pandas"] is True

    def test_has_airflow_flag_false(self):
        """has_airflow should be False since sample_pipeline doesn't use Airflow."""
        assert self.result["has_airflow"] is False

    def test_has_prefect_flag_false(self):
        """has_prefect should be False since sample_pipeline doesn't use Prefect."""
        assert self.result["has_prefect"] is False

    def test_raw_summary_is_string(self):
        """raw_summary should be a non-empty string."""
        assert isinstance(self.result["raw_summary"], str)
        assert len(self.result["raw_summary"]) > 0

    def test_raw_summary_max_300_chars(self):
        """raw_summary should be at most 300 characters."""
        assert len(self.result["raw_summary"]) <= 300


class TestExtractStructureEdgeCases:
    """Tests for error handling in extract_structure()."""

    def test_nonexistent_file_raises(self):
        """Should raise an exception for a file that doesn't exist."""
        with pytest.raises((FileNotFoundError, OSError)):
            extract_structure("/nonexistent/path/file.py")

    def test_syntax_error_returns_error_dict(self):
        """
        A file with a Python syntax error should return a dict with
        an 'error' key instead of crashing.
        """
        # Write a temporary file with broken syntax
        import tempfile
        broken_code = "def broken(\n    # missing closing paren and colon\n    pass"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(broken_code)
            tmp_path = tmp.name

        try:
            result = extract_structure(tmp_path)
            # Should return a dict with an error key, not raise an exception
            assert "error" in result
        finally:
            os.unlink(tmp_path)  # Clean up the temp file

    def test_empty_file_returns_valid_structure(self):
        """An empty .py file should return a valid dict with empty lists."""
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write("")  # Empty file
            tmp_path = tmp.name

        try:
            result = extract_structure(tmp_path)
            assert isinstance(result, dict)
            assert result["imports"] == []
            assert result["functions"] == []
            assert result["urls"] == []
        finally:
            os.unlink(tmp_path)


# ============================================================
# Tests for scan_folder()
# ============================================================

class TestScanFolder:
    """Tests for the directory scanner."""

    def test_returns_list(self):
        """scan_folder should always return a list."""
        result = scan_folder(TESTS_DIR)
        assert isinstance(result, list)

    def test_finds_sample_pipeline(self):
        """Should find sample_pipeline.py in the tests directory."""
        result = scan_folder(TESTS_DIR)
        filenames = [r["filename"] for r in result]
        assert "sample_pipeline.py" in filenames

    def test_skips_test_files(self):
        """
        Files starting with test_ should be skipped.
        (test_parser.py itself should NOT appear in scan results)
        """
        result = scan_folder(TESTS_DIR)
        filenames = [r["filename"] for r in result]
        assert "test_parser.py" not in filenames

    def test_invalid_directory_raises(self):
        """Should raise ValueError for a path that isn't a directory."""
        with pytest.raises(ValueError):
            scan_folder("/nonexistent/directory")

    def test_result_items_have_required_keys(self):
        """Every item in the scan result should have the expected keys."""
        required_keys = {
            "filename", "filepath", "imports", "functions",
            "urls", "db_connections", "has_airflow", "has_prefect",
            "has_pandas", "raw_summary"
        }
        result = scan_folder(TESTS_DIR)
        for item in result:
            # If there's an error, the error key is present — still check basics
            missing = required_keys - set(item.keys()) - {"error"}
            assert not missing, f"Missing keys in result for {item.get('filename')}: {missing}"
