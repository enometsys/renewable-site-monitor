"""Grounded NL->SQL agent.

The model only writes a read-only SELECT; SQLite returns the rows; the model then
answers from those rows alone. It never sees the data until after the query runs, so
it can't invent numbers. Works against any OpenAI-compatible endpoint (OpenAI cloud or
a local Ollama) via OPENAI_BASE_URL / OPENAI_API_KEY / OPENAI_MODEL.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3

from openai import OpenAI

import config

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
ROW_LIMIT = 200

SCHEMA = """
sites(site_id TEXT, name TEXT, region TEXT, latitude REAL, longitude REAL)
readings(site_id TEXT, timestamp TEXT, solar_radiation REAL, wind_speed REAL)
  -- timestamp is hourly, ISO-8601 Asia/Manila local time, last 30 days
  -- solar_radiation W/m^2, wind_speed m/s; join readings.site_id = sites.site_id
"""

_SITE_NAMES = ", ".join(f"'{s['name']}'" for s in config.SITES)

SQL_SYSTEM = f"""You translate questions about renewable-site weather into ONE SQLite
SELECT query. Schema:
{SCHEMA}
The only sites are: {_SITE_NAMES}. Match site names case-insensitively with
LIKE '%term%' (e.g. a question about "Nabas" -> name LIKE '%Nabas%').
Rules: read-only SELECT (or WITH) only; never modify data. Always SELECT the value
columns needed to answer plus the site name — including the metric you rank by. E.g.
"which site has the highest avg solar radiation" -> SELECT name, AVG(solar_radiation)
... ORDER BY 2 DESC LIMIT 1 (keep the AVG in the SELECT, not just name). For
"last week"/"last N days"/"past month", filter timestamp with
date(timestamp) >= date('now','-N days'). If the question can't be answered from this
schema, set answerable=false.
Reply ONLY with JSON: {{"answerable": bool, "sql": string}}."""

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|vacuum)\b",
    re.IGNORECASE,
)


def _client() -> OpenAI:
    # base_url unset -> OpenAI cloud; set to http://localhost:11434/v1 for Ollama
    return OpenAI(
        base_url=os.getenv("OPENAI_BASE_URL") or None,
        api_key=os.getenv("OPENAI_API_KEY", "ollama"),
    )


def _safe_select(sql: str) -> str:
    """Allow a single read-only SELECT/WITH; raise on anything else."""
    s = sql.strip().rstrip(";").strip()
    if ";" in s:
        raise ValueError("only a single statement is allowed")
    if not re.match(r"^\s*(select|with)\b", s, re.IGNORECASE):
        raise ValueError("only SELECT queries are allowed")
    if _FORBIDDEN.search(s):
        raise ValueError("query contains a forbidden keyword")
    if not re.search(r"\blimit\b", s, re.IGNORECASE):
        s += f" LIMIT {ROW_LIMIT}"
    return s


def _run(sql: str) -> list[dict]:
    uri = f"file:{config.DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql).fetchall()]
    finally:
        conn.close()


def _plan(client: OpenAI, question: str, fix: str | None = None) -> dict:
    """Ask the model for a SQL plan as JSON; one retry on malformed output.

    `fix` carries a prior SQL error back to the model for a repair attempt.
    """
    messages = [
        {"role": "system", "content": SQL_SYSTEM},
        {"role": "user", "content": question},
    ]
    if fix:
        messages.append({"role": "user", "content": fix})
    for _ in range(2):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0,
        )
        try:
            data = json.loads(resp.choices[0].message.content)
            return {"answerable": bool(data.get("answerable")), "sql": data.get("sql", "")}
        except (json.JSONDecodeError, TypeError):
            messages.append({"role": "user", "content": "Reply with valid JSON only."})
    raise ValueError("model did not return valid JSON")


def ask(question: str) -> dict:
    client = _client()
    plan = _plan(client, question)
    if not plan["answerable"] or not plan["sql"]:
        return {"answer": "I don't have data for that.", "sql": None, "rows": []}

    sql = _safe_select(plan["sql"])
    try:
        rows = _run(sql)
    except sqlite3.OperationalError as e:
        # one repair attempt: feed the error back to the model
        fail = {"answer": "I couldn't build a valid query for that.", "sql": sql, "rows": []}
        plan = _plan(client, question, fix=f"That SQL failed: {sql}\nSQLite error: {e}\nReturn corrected JSON.")
        try:
            sql = _safe_select(plan.get("sql", ""))
            rows = _run(sql)
        except (ValueError, sqlite3.OperationalError):
            return fail

    if not rows:
        return {"answer": "No matching data in the stored window.", "sql": sql, "rows": []}

    answer = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "The rows are the result of a query built to answer this "
                "question. Answer using ONLY these rows; a single returned site/value "
                "for a 'which/what' question IS the answer. Be concise. Do not invent "
                "numbers. Only say you lack data if the rows are empty or unrelated.",
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nRows (JSON):\n{json.dumps(rows)}",
            },
        ],
        temperature=0,
    ).choices[0].message.content

    # some models (e.g. Qwen3) emit <think>...</think> reasoning; drop it
    answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.DOTALL).strip()
    return {"answer": answer, "sql": sql, "rows": rows[:50]}
