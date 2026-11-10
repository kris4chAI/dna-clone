# Operations

## Everyday

```bash
./start.sh                       # build if needed, start, wait for health, open the browser
docker compose ps                # both services should be "healthy"
docker compose logs -f app       # app logs (first lines show the database, seed and LLM status)
docker compose restart app       # pick up .env changes (or: docker compose up -d)
docker compose down              # stop; data stays in the pgdata volume
```

## Verify an install

```bash
python3 tools/smoke_test.py                  # default http://localhost:8080
python3 tools/smoke_test.py http://host:port
```

The script runs 73 checks, which together exercise all 64 skills:

- health and the UI;
- the persona lens (401 without a persona, 403 across the pursuit, delivery, assurance and PMO lenses);
- every screen's API, the PMO and assurance screens (including test generation and a plan run), and the chat guide in all four lenses;
- every pursuit, PMO and assurance skill engine and all 46 Snowflake delivery skills.

## Reset, upgrade, back up

| Task | How |
|---|---|
| Reload the seed content (drops curated edits, gate log, runs) | Set `RESET_DB=true` in `.env`, run `docker compose up -d`, then set it back to `false` |
| Start completely fresh | `docker compose down -v && docker compose up -d --build` |
| Upgrade to a new version of the folder | `docker compose up -d --build`. The entrypoint reloads content automatically when the schema version changes |
| Back up | `docker compose exec db pg_dump -U flyhigh flyhigh > flyhigh-backup.sql` |
| Restore | `docker compose exec -T db psql -U flyhigh -d flyhigh < flyhigh-backup.sql` |

## Change content and skills

| What | Where | Then |
|---|---|---|
| Implementation stages, agents, tools, personas, insights, data model, KPIs | `backend/app/seed_data.py` | `RESET_DB=true`, then `docker compose up -d --build` |
| Pursuit stages, lenses, roles, lens rules, rubric, sections | `backend/app/pursuit_data.py` | same as above |
| Delivery playbook content (PMO lens) | `assets/seed/delivery_playbook.json`; seed working data in `backend/app/pmo_api.py` | same as above |
| Stage templates | Replace the files in `assets/templates/`, then run `python tools/extract_kit.py <folder> assets/seed/pursuit_kit.json` | same as above |
| A pursuit or PMO skill | `skills/pursuit/<name>/SKILL.md` or `skills/pmo/<name>/SKILL.md` | `python tools/package_skills.py`, then rebuild |
| A Snowflake delivery skill | `skills/delivery/snowskills/*.py` (each skill is one decorated function) | `python tools/package_skills.py`, then rebuild |

Most screens also allow curation in place: personas, journeys, insights, the data model, KPIs, the kit sheets, readiness answers, checklists, KPI actuals, use-case ratings, the RAID log and estimate scenarios. Those edits are stored in the database and survive restarts.

## Develop without Docker

You need PostgreSQL 14 or later, Python 3.12 or later and Node 20 or later.

```bash
createuser -s flyhigh && createdb -O flyhigh flyhigh          # password: flyhigh
export DATABASE_URL=postgresql://flyhigh:flyhigh@localhost:5432/flyhigh
cd backend && pip install -r requirements.txt && python -m app.seed && uvicorn app.main:app --reload --port 8000
cd frontend && npm ci && npm run dev                            # http://localhost:5173 (proxies /api to :8000)
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `start.sh`: "Docker is not running" | Start Docker Desktop and wait until it says it is running |
| Port 8080 already in use | Set `FLYHIGH_PORT=8090` in `.env` |
| Build cannot pull images or packages | You are behind a proxy or mirror; see [configuration.md](configuration.md#corporate-networks) |
| The app restarts in a loop | Run `docker compose logs app`. A database password change after the first start needs `docker compose down -v` |
| "LLM not configured" although a key is set | Check that `LLM_PROVIDER` matches the key, then run `docker compose up -d` (`restart` alone does not reload `.env`) |
| LLM errors on Draft | The error is shown in the result panel. Check the model or deployment name and the base URL |
| Apple Silicon | Supported: every dependency ships arm64 wheels or builds |
