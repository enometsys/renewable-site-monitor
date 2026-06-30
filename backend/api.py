from __future__ import annotations

import os

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
from src import agent, anomaly, db

app = FastAPI(title="Renewable Site Monitor API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

METRICS = {"solar_radiation", "wind_speed"}


def _na(value):  # NaN -> None, numpy scalar -> float, for JSON
    return None if pd.isna(value) else float(value)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/sites")
def get_sites():
    with db.connect(config.DB_PATH) as conn:
        sites = db.load_sites(conn)
    if sites.empty:
        raise HTTPException(503, "No data loaded. Run `python -m src.etl` first.")
    return sites.to_dict(orient="records")


@app.get("/api/readings")
def get_readings(
    site_id: str,
    metric: str = "solar_radiation",
    start: str | None = None,
    end: str | None = None,
    k: float = Query(1.5, ge=0.5, le=4.0),
):
    if metric not in METRICS:
        raise HTTPException(422, f"metric must be one of {sorted(METRICS)}")

    with db.connect(config.DB_PATH) as conn:
        df = db.load_readings(conn, site_id=site_id, start=start, end=end)
    if df.empty:
        raise HTTPException(404, "No readings for the given site/range.")

    df = anomaly.flag_anomalies(df, metric, k=k)
    values = pd.to_numeric(df[metric], errors="coerce")

    series = [
        {"timestamp": ts.isoformat(), "value": _na(v), "isAnomaly": bool(a)}
        for ts, v, a in zip(df["timestamp"], values, df["is_anomaly"])
    ]
    return {
        "siteId": site_id,
        "metric": metric,
        "k": k,
        "summary": {
            "count": int(len(df)),
            "average": _na(values.mean()),
            "peak": _na(values.max()),
            "anomalies": int(df["is_anomaly"].sum()),
        },
        "series": series,
    }


class AskRequest(BaseModel):
    question: str


@app.post("/api/ask")
def ask(req: AskRequest):
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_BASE_URL")):
        raise HTTPException(
            503,
            "No LLM configured. Set OPENAI_API_KEY (cloud) or OPENAI_BASE_URL "
            "(e.g. http://localhost:11434/v1 for Ollama).",
        )
    if not req.question.strip():
        raise HTTPException(422, "question is required")
    try:
        return agent.ask(req.question)
    except ValueError as e:
        raise HTTPException(400, str(e))
