#!/bin/sh
# FlyHigh Navigator container entrypoint: wait for Postgres, load content (first run or schema upgrade), start the server.
set -e
cd "${FLYHIGH_HOME:-/srv}/backend"

echo "[flyhigh] waiting for the database..."
python - <<'PY'
import os, sys, time
import psycopg
url = os.environ["DATABASE_URL"]
for i in range(60):
    try:
        psycopg.connect(url, connect_timeout=3).close()
        print("[flyhigh] database is up")
        sys.exit(0)
    except Exception as e:
        time.sleep(2)
print("[flyhigh] database not reachable:", url, file=sys.stderr)
sys.exit(1)
PY

if [ "${RESET_DB:-false}" = "true" ]; then
  echo "[flyhigh] RESET_DB=true: reloading all content (curated edits are dropped)"
  python -m app.seed
else
  python -m app.seed --if-empty
fi

python - <<'PY'
from app import llm
s = llm.status()
print(f"[flyhigh] LLM: {s['provider']} · {s['model']}" if s["ready"] else "[flyhigh] LLM: not configured (prompt mode). Set LLM_PROVIDER and LLM_API_KEY in .env to enable drafting.")
PY

echo "[flyhigh] FlyHigh Navigator is starting on port ${PORT:-8000} (open http://localhost:${FLYHIGH_PORT:-8080})"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers
