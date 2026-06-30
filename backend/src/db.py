import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

SCHEMA = """
CREATE TABLE IF NOT EXISTS sites (
    site_id   TEXT PRIMARY KEY,
    name      TEXT NOT NULL,
    region    TEXT,
    latitude  REAL NOT NULL,
    longitude REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS readings (
    site_id         TEXT NOT NULL,
    timestamp       TEXT NOT NULL,          -- ISO-8601, Asia/Manila local time
    solar_radiation REAL,                   -- W/m^2 (NULL if missing/invalid)
    wind_speed      REAL,                   -- m/s   (NULL if missing/invalid)
    PRIMARY KEY (site_id, timestamp),
    FOREIGN KEY (site_id) REFERENCES sites(site_id)
);

CREATE INDEX IF NOT EXISTS idx_readings_ts ON readings(timestamp);
"""


@contextmanager
def connect(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def upsert_sites(conn: sqlite3.Connection, sites: list[dict]) -> None:
    conn.executemany(
        """INSERT INTO sites (site_id, name, region, latitude, longitude)
           VALUES (:site_id, :name, :region, :latitude, :longitude)
           ON CONFLICT(site_id) DO UPDATE SET
               name=excluded.name, region=excluded.region,
               latitude=excluded.latitude, longitude=excluded.longitude""",
        sites,
    )


def upsert_readings(conn: sqlite3.Connection, df: pd.DataFrame) -> int:
    rows = df[["site_id", "timestamp", "solar_radiation", "wind_speed"]].itertuples(
        index=False, name=None
    )
    cur = conn.executemany(
        """INSERT INTO readings (site_id, timestamp, solar_radiation, wind_speed)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(site_id, timestamp) DO UPDATE SET
               solar_radiation=excluded.solar_radiation,
               wind_speed=excluded.wind_speed""",
        list(rows),
    )
    return cur.rowcount


def load_sites(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM sites ORDER BY name", conn)


def load_readings(
    conn: sqlite3.Connection,
    site_id: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    clauses, params = [], []
    if site_id:
        clauses.append("site_id = ?")
        params.append(site_id)
    if start:
        clauses.append("timestamp >= ?")
        params.append(start)
    if end:
        clauses.append("timestamp <= ?")
        params.append(end)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    df = pd.read_sql_query(
        f"SELECT * FROM readings {where} ORDER BY timestamp", conn, params=params
    )
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df
