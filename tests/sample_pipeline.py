"""
sample_pipeline.py — A minimal pipeline used as a test fixture
--------------------------------------------------------------
This file is used by test_parser.py to verify that the parser
correctly extracts imports, functions, URLs, and other features.

It is intentionally simple and predictable so tests can make
exact assertions about what the parser should return.
"""

import os
import requests
import pandas as pd
from sqlalchemy import create_engine

# A string containing a URL — the parser should detect this
API_ENDPOINT = "https://api.example.com/data/v1/records"

# A database connection string — the parser should detect this
DB_URL = "postgresql://user:pass@localhost:5432/testdb"


def fetch_records(api_key: str) -> list:
    """Fetches raw records from the example API."""
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(API_ENDPOINT, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json().get("records", [])


def clean_records(records: list) -> pd.DataFrame:
    """Converts records list to a cleaned DataFrame."""
    df = pd.DataFrame(records)
    df = df.dropna()
    df["name"] = df["name"].str.strip().str.lower()
    return df


def save_to_db(df: pd.DataFrame) -> None:
    """Saves the cleaned DataFrame to PostgreSQL."""
    engine = create_engine(DB_URL)
    df.to_sql("clean_records", con=engine, if_exists="replace", index=False)
    engine.dispose()


def main():
    """Orchestrates the full mini-pipeline."""
    api_key = os.environ.get("API_KEY", "")
    records = fetch_records(api_key)
    df = clean_records(records)
    save_to_db(df)
    print(f"Loaded {len(df)} records.")
