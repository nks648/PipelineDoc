"""
etl_pipeline.py — Example: Classic Extract-Transform-Load pipeline
-------------------------------------------------------------------
This is a realistic example of an ETL (Extract, Transform, Load) pipeline.
It pulls sales data from an external API, cleans it with pandas,
and writes the results into a PostgreSQL database.

This file exists so you can test PipelineDoc against real-looking code.
Run: pipelinedoc run ./examples
"""

import pandas as pd
import requests
import sqlalchemy
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import logging

# Configure logging so we can see what the pipeline is doing
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# --- Configuration ---
# In a real project these would come from environment variables, not be hardcoded
API_BASE_URL = "https://api.salesforce.com/v2/reports"
API_KEY = "your-api-key-here"  # Replace with real key or load from env
DB_CONNECTION = "postgresql://pipeline_user:password@localhost:5432/analytics_db"
TARGET_TABLE = "daily_sales_summary"


def extract_sales_data(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetches sales report data from the Salesforce API for a given date range.

    Args:
        start_date: ISO format date string, e.g. "2024-01-01"
        end_date:   ISO format date string, e.g. "2024-01-31"

    Returns:
        DataFrame with raw sales records
    """
    logger.info(f"Extracting sales data from {start_date} to {end_date}")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    params = {
        "start_date": start_date,
        "end_date": end_date,
        "format": "json",
    }

    response = requests.get(API_BASE_URL, headers=headers, params=params, timeout=30)

    # Raise an exception if the request failed (4xx or 5xx status)
    response.raise_for_status()

    data = response.json()
    df = pd.DataFrame(data["records"])

    logger.info(f"Extracted {len(df)} records")
    return df


def transform_sales_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans and aggregates the raw sales data.

    Transformations applied:
      - Remove rows where amount is null or zero
      - Convert date strings to proper datetime objects
      - Group by date and region to get daily totals
      - Calculate revenue per transaction metric

    Args:
        df: Raw DataFrame from extract_sales_data()

    Returns:
        Cleaned and aggregated DataFrame
    """
    logger.info("Transforming sales data...")

    # Drop rows with missing or zero amounts
    df = df.dropna(subset=["amount"])
    df = df[df["amount"] > 0]

    # Parse date column into datetime
    df["sale_date"] = pd.to_datetime(df["sale_date"])

    # Normalize region names to uppercase for consistency
    df["region"] = df["region"].str.upper().str.strip()

    # Aggregate: sum revenue and count transactions per day per region
    summary = df.groupby(["sale_date", "region"]).agg(
        total_revenue=("amount", "sum"),
        transaction_count=("transaction_id", "count"),
    ).reset_index()

    # Calculate average transaction value
    summary["avg_transaction_value"] = (
        summary["total_revenue"] / summary["transaction_count"]
    ).round(2)

    # Add a pipeline run timestamp for auditing
    summary["loaded_at"] = datetime.utcnow()

    logger.info(f"Transformed into {len(summary)} summary rows")
    return summary


def load_to_postgres(df: pd.DataFrame, table_name: str) -> None:
    """
    Writes the transformed DataFrame to PostgreSQL.

    Uses 'replace' strategy — drops and recreates the table on each run.
    For append-only behavior, change if_exists='replace' to if_exists='append'.

    Args:
        df: Cleaned DataFrame to write
        table_name: Target table name in the database
    """
    logger.info(f"Loading {len(df)} rows into {table_name}...")

    # create_engine() creates a connection pool to the database
    engine = create_engine(DB_CONNECTION)

    # to_sql() writes the entire DataFrame to the specified table
    df.to_sql(
        name=table_name,
        con=engine,
        if_exists="replace",   # Drop and recreate the table each run
        index=False,            # Don't write the DataFrame index as a column
        chunksize=1000,         # Write in batches of 1000 rows
    )

    # Always dispose of the engine to close connection pool
    engine.dispose()

    logger.info("Load complete.")


def run_pipeline():
    """
    Main orchestrator: runs the full ETL pipeline for yesterday's data.
    """
    # Calculate yesterday's date range
    yesterday = datetime.utcnow().date() - timedelta(days=1)
    start = yesterday.strftime("%Y-%m-%d")
    end = yesterday.strftime("%Y-%m-%d")

    # Run each stage in order
    raw_data = extract_sales_data(start, end)
    clean_data = transform_sales_data(raw_data)
    load_to_postgres(clean_data, TARGET_TABLE)

    logger.info("Pipeline completed successfully.")


# This block runs only when this script is executed directly (not imported)
if __name__ == "__main__":
    run_pipeline()
