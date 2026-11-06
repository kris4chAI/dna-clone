# Architecture

```
 Browser ──► app container (port 8080 → 8000)
            ├── React UI (built at image build time; served by FastAPI)
            ├── FastAPI API
            │    ├── access.py        persona → lens → access_rule.lenses (401/403 on every call)
            │    ├── main.py          implementation lifecycle, catalog, solution content, curation, chat
            │    ├── pursuit_api.py   lifecycle, pursuit stages, kit (sheets + template downloads), win room, response quality
            │    ├── pmo_api.py       PMO lens: playbook, readiness, plan, estimator, use cases, KPIs, governance, RAID, 4 PMO engines
            │    ├── skills_api.py    skills studio: 9 pursuit + 4 PMO engines, 46 Snowflake generators, SQL checks, gate log, execution
            │    ├── chat.py          lens-aware intent rules (pursuit, delivery, PMO) + retrieval over the search_index view (LLM optional)
            │    └── llm.py           Anthropic, OpenAI, Azure OpenAI, Gemini or any OpenAI-compatible server
            ├── skills/               SKILL.md files, snowskills library, .skill packages
            └── assets/               stage templates and seed data
                 │
                 ▼
            db container: PostgreSQL 16 (named volume pgdata)
                 │
                 └──► optional: your LLM provider · optional: Snowflake DEV account
```

## Data (PostgreSQL)

| Area | Tables |
|---|---|
| Implementation lifecycle | `phase`, `stage`, `component` (agents, skills, tools, frameworks, Snowflake components), `stage_component` |
| Solution content | `persona`, `journey_step`, `insight_dashboard`, `insight_question`, `domain`, `subject_area`, `data_entity`, `attribute`, `kpi`, `conformed_dim`, `data_layer` |
| Pursuit lifecycle | `pursuit_stage`, `pursuit_artefact`, `pursuit_skill`, `pursuit_ref`, `kit_template`, `kit_sheet`, `kit_row`, `rubric_criterion`, `response_section`, `section_score`, `section_musthave` |
| Persona lens | `lens`, `lens_role`, `access_rule` (resource = screen, pursuit_stage or skill; `lenses` array) |
| Program office | `pb_doc` (playbook content), `pmo_readiness`, `pmo_check`, `pmo_kpi`, `pmo_usecase`, `pmo_raid`, `pmo_estimate` |
| Activity | `guide_progress`, `chat_message`, `skill_run`, `skill_execution`, `gate_decision`, `section_round`, `app_meta` |

`search_index` is a view across all content, used by the chat guide.

## Start-up sequence

1. `db` becomes healthy (`pg_isready`).
2. `app` runs `docker/entrypoint.sh`:
   - wait for the database;
   - `python -m app.seed --if-empty`, which loads content on the first start or when `SCHEMA_VERSION` changes, and skips otherwise;
   - log the LLM status;
   - start uvicorn.
3. The Docker health check calls `/api/health`, which returns database status, version, LLM status and whether the UI is present.

## Skills

- **PMO skills:** `skills/pmo/*/SKILL.md` is the instruction set; the engines in `pmo_api.py` read and write the playbook working tables.
- **Pursuit skills:** `skills/pursuit/*/SKILL.md` is the instruction set. The app's engine for each skill (`skills_api.py`) reads and writes the kit, scorecard and rubric data.
- **Delivery skills:** `skills/delivery/snowskills/` holds the generators. They are pure Python, deterministic, and never connect to Snowflake. The app imports them directly. `tools/package_skills.py` packages each one with its own copy of the library, so a `.skill` runs anywhere with Python.
- **SQL check:** generated SQL is syntax-checked with sqlglot (Snowflake dialect). Statements the validator cannot parse are reported as Snowflake-specific and get their real check on execution in DEV.
