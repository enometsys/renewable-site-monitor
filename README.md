# Renewable Site Monitor

Pulls 30 days of hourly weather for three renewable sites, cleans and stores it,
and serves a dashboard for watching solar radiation and wind speed with IQR anomaly
flagging.

ENGIE SSE Backend L3 take-home. Part 1 (ETL + dashboard) is done. Part 2 (the
conversational agent) is noted at the bottom but not built.

Python/FastAPI backend does the data engineering and exposes it over JSON; a separate
React frontend renders it. They only talk through `/api`.

## Run

Backend:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.etl                 # fetch + clean + load into data/weather.db
uvicorn api:app --port 8600
```

Frontend (second terminal):

```bash
cd frontend
pnpm install
pnpm dev                          # :5173, proxies /api -> :8600
```

The DB is git-ignored, so run the ETL once before the API.

## API

- `GET /api/sites`
- `GET /api/readings?site_id=&metric=&k=` — series with `isAnomaly` flags plus a
  `{count, average, peak, anomalies}` summary. `metric` is `solar_radiation` or
  `wind_speed`; `k` tunes the IQR fence (default 1.5).

## Decisions

- **Open-Meteo Forecast API** with `past_days=30, forecast_days=0`, not the Archive
  API. The archive lags ~5 days, so it wouldn't cover "the past 30 days". Cost: the
  most recent hours are now-cast, not finalised.
- **SQLite.** A few thousand rows across 3 sites. Single file, real SQL, nothing to
  run. DuckDB/Parquet would pay off at much larger scale; here it's overkill.
- **Cleaning** separates impossible values from merely-unusual ones. Impossible
  values are fixed here (clamp negative solar to 0, null out negative wind and
  readings past physical caps); short gaps (<=2h) are interpolated, longer ones left
  null. Unusual-but-valid values are left for the anomaly layer to flag, not deleted.
  Each run prints a per-site missing/unfilled count.
- **IQR over z-score.** Solar is zero-inflated and right-skewed, wind is right-skewed;
  z-score's mean/std get dragged around by the outliers we want to catch, quartiles
  don't. Solar uses a daytime-only baseline so nighttime zeros don't flag noon.

## Layout

```
backend/
  config.py    sites + settings
  api.py       FastAPI endpoints
  src/db.py    SQLite schema + queries
  src/etl.py   fetch -> clean -> load
  src/anomaly.py
  src/agent.py grounded NL->SQL agent (Part 2)
frontend/
  src/App.tsx, src/lib/api.ts, src/components/
```

Sites: Burgos Wind Farm (Ilocos Norte), Cadiz Solar (Negros Occidental), Nabas Wind
Farm (Aklan) — real PH renewable sites, spread across the grid.

## Part 2 (bonus): ask the data in plain English

`POST /api/ask {question}` runs a grounded NL-to-SQL agent and the dashboard's "Ask the
data" panel uses it. Flow: the model writes one **read-only** `SELECT`, SQLite runs it,
and the model answers **only from the returned rows** — it never sees the data until
after the query runs, so it can't invent numbers. Out-of-scope questions ("weather in
Tokyo") return "I don't have data for that" instead of a guess.

Grounding/safety: the generated SQL is validated (single `SELECT`/`WITH` only;
`INSERT/UPDATE/DELETE/DROP/PRAGMA/…` and multi-statement rejected; a `LIMIT` is forced)
and executed on a read-only SQLite connection. A failed query gets one repair attempt,
then degrades to a graceful message.

It speaks the **OpenAI API**, so it runs against OpenAI cloud or a local model:

```bash
# OpenAI cloud
export OPENAI_API_KEY=sk-...           # OPENAI_MODEL defaults to gpt-4o-mini

# or local, via Ollama (OpenAI-compatible endpoint)
ollama pull qwen3:4b
export OPENAI_BASE_URL=http://localhost:11434/v1 OPENAI_API_KEY=ollama OPENAI_MODEL=qwen3:4b
```

Without either set, `/api/ask` returns 503 and the rest of the dashboard works normally.
Answer quality scales with the model — tested locally with Ollama `qwen3:4b`; larger
models (e.g. `gpt-4o-mini`) produce more reliable SQL on edge cases.

## Not done / next

- No tests yet; the etl/anomaly functions are pure over DataFrames, so they're easy
  to cover.
- Anomaly detection is univariate; contextual cases (low solar on a clear day) need a
  clear-sky baseline.
- ETL is a manual run; a cron would keep the window rolling.
- The agent is single-turn; conversational follow-ups would need history threading.
