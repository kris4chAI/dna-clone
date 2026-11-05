# Keystone Navigator

A conversational, self-guided UI for the Virtusa × CJLA Keystone proposal (v.6). It walks a team from **discovery to monitoring** and catalogs every agent, skill, tool and framework from slides 30–37. It also gives you curation workspaces for persona journeys (slides 18–20), insights (21–24) and the logistics industry data model (25–29).

**Stack:** React 18 + Vite · FastAPI · PostgreSQL 16 (one small database, no ORM)

## What's inside

| Area | What you can do | Source slides |
|---|---|---|
| **Guided workflow** | A 10-step flow map grouped by delivery phase, with the G1/G2/G3 human gates and the loop that feeds build learnings back into Discover. For each step you get a checklist (progress saved in Postgres), the lead role, agents with their skills and tools, Helio frameworks, Snowflake components, outputs, gate evidence and metrics. Prev/Next buttons walk you through in order. | 30–37 |
| **Toolkit catalog** | A stage × component coverage heatmap. 55 agents, 46 skills, 36 tools, 7 Helio frameworks and 47 Snowflake components, each linked to the stages and agents that use it. Search, add or edit. | 30–37 |
| **Persona journeys** | 7 personas and 29 journey moments (question → experience → metrics, plus doing / today for the customer). Add personas and moments, or edit them. | 18–20 |
| **Insights** | 4 dashboards, each built on four questions: what happened, why, what will happen, what you can do. Every dashboard links to its persona. Add dashboards and insights, or edit them. | 21–24 |
| **Data models** | 4 domains and 20 subject areas, Bronze/Silver/Gold layers, conformed dimensions, 45 facts and dimensions with 168 attributes, a star-schema view of each fact, and a 32-KPI library with E/O/C audience filters. Everything is editable. | 25–29 |
| **Keystone guide (chat)** | Ask about a stage, agent, skill (`/reconcile`), KPI, persona or dashboard. Answers come with cards that take you to the right screen, and "What's next?" follows the guided flow. Works offline using intent rules and retrieval over the Postgres `search_index` view. If you set `ANTHROPIC_API_KEY`, Claude phrases the answer using only the retrieved context. | all |

Rows loaded from the proposal are tagged `origin='seed'`. Anything added or edited in the UI is tagged `curated` and shows a **Curated** badge.

## Run with Docker

```bash
docker compose up --build
# UI  → http://localhost:5173
# API → http://localhost:8000/docs
```

The first time the API starts, it creates the schema and seeds the database (`python -m app.seed --if-empty`).

## Run locally

```bash
# 1. Postgres (any 14+). Create the role and database:
createuser -s keystone && createdb -O keystone keystone   # password: keystone

# 2. API
cd backend
pip install -r requirements.txt
export DATABASE_URL=postgresql://keystone:keystone@localhost:5432/keystone
python -m app.seed            # drops and reloads everything
uvicorn app.main:app --reload --port 8000

# 3. UI (dev server proxies /api to :8000)
cd ../frontend
npm install && npm run dev    # http://localhost:5173
```

Single-process option: run `npm run build` in `frontend/`, and FastAPI will serve `frontend/dist` at http://localhost:8000.

## Project layout

```
backend/app/
  seed_data.py   # all proposal content: stages, agents, skills, tools, personas, insights, data model, KPIs
  schema.sql     # tables + search_index view
  seed.py        # loader
  main.py        # REST API: workflow, catalog, progress, curation CRUD, chat
  chat.py        # conversational guide (rules + retrieval, optional Claude)
frontend/src/
  views/         # Workflow, Catalog, Journeys, Insights, DataModels
  components/    # Chat, shared UI (editor modal, chips, markdown)
```

## API quick reference

- `GET /api/stages`, `GET /api/stages/{code}`: the workflow stages and the detail for one stage
- `GET /api/components?kind=agent|skill|tool|framework|snowflake`
- `GET /api/personas`, `GET /api/insights`, `GET /api/datamodel`
- `POST|PUT|DELETE /api/curate/{table}[/{id}]`: works on `persona`, `journey_step`, `insight_dashboard`, `insight_question`, `domain`, `subject_area`, `data_entity`, `attribute`, `kpi`, `conformed_dim`, `component`
- `GET /api/progress/{session}`, `POST /api/progress`
- `POST /api/chat` `{message, session_id, context:{stage}}`

## Notes

- Dashboard figures are illustrative, as they are in the proposal. OneTrack and Rebus content is flagged as discovery only.
- Each KPI's `source_fact` is a suggested mapping to confirm in discovery. Facts without detailed attributes on the slides get a placeholder attribute so they can be curated.
- To re-seed from scratch, run `python -m app.seed`. This drops curated edits.
