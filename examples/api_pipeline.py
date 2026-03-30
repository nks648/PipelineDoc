"""
api_pipeline.py — Example: Multi-source API aggregation pipeline
-----------------------------------------------------------------
This pipeline fetches data from three different APIs (Stripe for payments,
Slack for notifications, and a weather service), merges them into a
combined report, and saves the result to a local SQLite database and
a JSON file for downstream consumption.

This is a different pattern from etl_pipeline.py — it's a fan-in pipeline
(multiple sources → one destination) rather than a simple linear ETL.
"""

import requests
import sqlite3
import json
import os
from datetime import datetime
from typing import Optional

# --- Configuration ---
STRIPE_API_BASE = "https://api.stripe.com/v1"
# Load the Slack webhook URL from an environment variable (never hardcode real webhook URLs)
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"
LOCAL_DB_PATH = "sqlite:///pipeline_data.db"
OUTPUT_JSON_PATH = "output/daily_report.json"

# API keys loaded from environment variables (safer than hardcoding)
STRIPE_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
WEATHER_KEY = os.environ.get("OPENWEATHER_API_KEY", "")


def fetch_stripe_revenue(date: str) -> dict:
    """
    Fetches daily charge totals from the Stripe API.

    Args:
        date: Date string in YYYY-MM-DD format

    Returns:
        Dict with total_charges, successful_charges, and failed_charges
    """
    headers = {"Authorization": f"Bearer {STRIPE_KEY}"}

    # Stripe uses Unix timestamps, so we convert our date string
    import time
    start_ts = int(datetime.strptime(date, "%Y-%m-%d").timestamp())
    end_ts = start_ts + 86400  # Add 24 hours (86400 seconds)

    response = requests.get(
        f"{STRIPE_API_BASE}/charges",
        headers=headers,
        params={
            "created[gte]": start_ts,
            "created[lt]": end_ts,
            "limit": 100,
        },
        timeout=15,
    )
    response.raise_for_status()

    charges = response.json().get("data", [])

    # Summarize the charges
    successful = [c for c in charges if c["status"] == "succeeded"]
    failed = [c for c in charges if c["status"] == "failed"]

    return {
        "total_charges": len(charges),
        "successful_charges": len(successful),
        "failed_charges": len(failed),
        "total_revenue_cents": sum(c["amount"] for c in successful),
    }


def fetch_weather_summary(city: str = "New York") -> dict:
    """
    Fetches current weather data from OpenWeatherMap.
    Used to correlate weather with sales patterns.

    Args:
        city: City name to fetch weather for

    Returns:
        Dict with temperature, conditions, and humidity
    """
    response = requests.get(
        WEATHER_API_URL,
        params={
            "q": city,
            "appid": WEATHER_KEY,
            "units": "imperial",  # Fahrenheit
        },
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()

    return {
        "city": city,
        "temperature_f": data["main"]["temp"],
        "conditions": data["weather"][0]["description"],
        "humidity_pct": data["main"]["humidity"],
    }


def send_slack_notification(message: str, channel: str = "#data-alerts") -> bool:
    """
    Sends a pipeline status notification to a Slack channel via webhook.

    Args:
        message: The text to send
        channel: Slack channel name (only informational with webhooks)

    Returns:
        True if the message was sent successfully, False otherwise
    """
    payload = {
        "text": message,
        "username": "PipelineBot",
        "icon_emoji": ":bar_chart:",
    }

    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        # Non-fatal: if Slack is down, we don't want to fail the pipeline
        return False


def save_to_sqlite(report: dict, db_path: str = "pipeline_data.db") -> None:
    """
    Persists the daily report to a local SQLite database.

    SQLite is a file-based database — no server needed.
    Great for local development and small pipelines.

    Args:
        report: The final merged report dict
        db_path: Path to the SQLite database file
    """
    # sqlite3.connect() creates the file if it doesn't exist
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # CREATE TABLE IF NOT EXISTS: only creates the table on first run
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_reports (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date TEXT NOT NULL,
            data        TEXT NOT NULL,       -- Store full report as JSON string
            created_at  TEXT NOT NULL
        )
    """)

    cursor.execute(
        "INSERT INTO daily_reports (report_date, data, created_at) VALUES (?, ?, ?)",
        (
            report["date"],
            json.dumps(report),          # Serialize the whole dict to JSON
            datetime.utcnow().isoformat(),
        ),
    )

    conn.commit()
    conn.close()


def save_to_json(report: dict, output_path: str = OUTPUT_JSON_PATH) -> None:
    """
    Saves the report as a JSON file for downstream systems to consume.

    Args:
        report: The final merged report dict
        output_path: Where to write the JSON file
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)


def run_pipeline(date: Optional[str] = None) -> dict:
    """
    Main entry point: fetches all data sources and produces a merged report.

    Args:
        date: Date to run for, in YYYY-MM-DD format. Defaults to today.

    Returns:
        The complete merged report dict
    """
    if date is None:
        date = datetime.utcnow().strftime("%Y-%m-%d")

    print(f"Running API aggregation pipeline for {date}...")

    # --- Fan-in: fetch from all sources ---
    stripe_data = fetch_stripe_revenue(date)
    weather_data = fetch_weather_summary("New York")

    # --- Merge into one report ---
    report = {
        "date": date,
        "generated_at": datetime.utcnow().isoformat(),
        "payments": stripe_data,
        "weather": weather_data,
    }

    # --- Save outputs ---
    save_to_sqlite(report)
    save_to_json(report)

    # --- Notify team ---
    revenue_usd = stripe_data["total_revenue_cents"] / 100
    send_slack_notification(
        f"Daily report for {date}: "
        f"${revenue_usd:,.2f} revenue, "
        f"{stripe_data['failed_charges']} failed charges. "
        f"Weather: {weather_data['conditions']}, {weather_data['temperature_f']}°F"
    )

    print("Pipeline complete.")
    return report


if __name__ == "__main__":
    run_pipeline()
