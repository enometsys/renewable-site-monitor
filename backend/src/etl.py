"""Fetch hourly weather from Open-Meteo, clean it, load into SQLite.

Run: python -m src.etl
"""

from __future__ import annotations

import sys

import pandas as pd
import requests

import config
from src import db


def fetch_site(site: dict) -> pd.DataFrame:
    params = {
        "latitude": site["latitude"],
        "longitude": site["longitude"],
        "hourly": ",".join(config.HOURLY_VARS),
        "wind_speed_unit": config.WIND_SPEED_UNIT,
        "timezone": config.TIMEZONE,
        "past_days": config.PAST_DAYS,
        "forecast_days": 0,
    }
    resp = requests.get(config.OPEN_METEO_URL, params=params, timeout=30)
    resp.raise_for_status()
    h = resp.json()["hourly"]
    return pd.DataFrame({
        "site_id": site["site_id"],
        "timestamp": pd.to_datetime(h["time"]),
        "solar_radiation": h["shortwave_radiation"],
        "wind_speed": h["wind_speed_10m"],
    })


def clean_site(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Drop impossible values, bridge short gaps. Statistical outliers are left
    for anomaly.py to flag, not removed here."""
    df = df.sort_values("timestamp").reset_index(drop=True)
    report = {"site_id": df["site_id"].iloc[0], "rows": len(df)}

    df["solar_radiation"] = df["solar_radiation"].clip(lower=0)        # night = 0
    df.loc[df["wind_speed"] < 0, "wind_speed"] = pd.NA
    df.loc[df["solar_radiation"] > config.SOLAR_MAX_WM2, "solar_radiation"] = pd.NA
    df.loc[df["wind_speed"] > config.WIND_MAX_MS, "wind_speed"] = pd.NA

    for col in ("solar_radiation", "wind_speed"):
        gaps = int(df[col].isna().sum())
        # bridge gaps up to 2h; longer ones stay NULL
        df[col] = df[col].astype("float64").interpolate(limit=2, limit_area="inside")
        report[f"{col}_missing"] = gaps
        report[f"{col}_unfilled"] = int(df[col].isna().sum())

    df = df.astype(object).where(pd.notna(df), None)  # pandas NA -> None for sqlite
    return df, report


def run() -> None:
    frames, reports = [], []
    for site in config.SITES:
        print(f"fetching {site['name']}...")
        clean, report = clean_site(fetch_site(site))
        frames.append(clean)
        reports.append(report)

    data = pd.concat(frames, ignore_index=True)
    data["timestamp"] = pd.to_datetime(data["timestamp"]).dt.strftime("%Y-%m-%dT%H:%M")

    with db.connect(config.DB_PATH) as conn:
        db.init_schema(conn)
        db.upsert_sites(conn, config.SITES)
        db.upsert_readings(conn, data)

    print(f"\nloaded {len(data)} rows into {config.DB_PATH}\n")
    for r in reports:
        print(f"  {r['site_id']:7} {r['rows']} rows  "
              f"missing(solar/wind)={r['solar_radiation_missing']}/{r['wind_speed_missing']}  "
              f"unfilled={r['solar_radiation_unfilled']}/{r['wind_speed_unfilled']}")


if __name__ == "__main__":
    try:
        run()
    except requests.HTTPError as e:
        sys.exit(f"API error: {e}")
