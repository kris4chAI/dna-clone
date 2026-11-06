# Features

What each part of FlyHigh Navigator does. For setup see the [README](../README.md).

## Implementation lifecycle and solution content

| Area | What you can do |
|---|---|
| **Guided workflow** | A 10-step flow map grouped by delivery phase, with the G1/G2/G3 human gates and the loop that feeds build learnings back into Discover. For each step you get a checklist (progress saved in Postgres), the lead role, agents with their skills and tools, accelerator frameworks, Snowflake components, outputs, gate evidence and metrics. Prev/Next buttons walk you through in order. |
| **Toolkit catalog** | A stage × component coverage heatmap. 55 agents, 46 skills, 36 tools, 7 accelerator frameworks and 47 Snowflake components, each linked to the stages and agents that use it. Search, add or edit. |
| **Persona journeys** | 7 personas and 29 journey moments (question → experience → metrics, plus doing / today for the customer). Add personas and moments, or edit them. |
| **Insights** | 4 dashboards, each built on four questions: what happened, why, what will happen, what you can do. Every dashboard links to its persona. Add dashboards and insights, or edit them. |
| **Data models** | 4 domains and 20 subject areas, Bronze/Silver/Gold layers, conformed dimensions, 45 facts and dimensions with 168 attributes, a star-schema view of each fact, and a 32-KPI library with E/O/C audience filters. Everything is editable. |
| **FlyHigh guide (chat)** | Ask about a stage, agent, skill (`/reconcile`), KPI, persona or dashboard. Answers come with cards that take you to the right screen, and "What's next?" follows the guided flow. Works offline using intent rules and retrieval over the Postgres `search_index` view. If an LLM is configured in `.env`, it phrases the answer using only the retrieved context. | all |

Rows loaded from the reference content are tagged `origin='seed'`. Anything added or edited in the UI is tagged `curated` and shows a **Curated** badge.

## Pursuit lifecycle and persona lens

| Screen | Sales lens | Delivery lens | What it does |
|---|---|---|---|
| Lifecycle overview | ✓ | ✓ | The end-to-end map from pursuit (9 stages) to handover to implementation (10 steps). Locked segments are greyed out. Includes the access matrix. |
| Pursuit stages | all 9 | 5, 8, 9 only | Flow map by loop (Build, Review, Fix) with the critical path, parallel lanes and gates G0–G8. Each stage shows its questions checklist (saved), input tiers, artefacts (systems of record flagged), skills and tools, templates, and the implementation steps it hands over to. A method tab covers principles, targets, team 13 → 6, measures, roles, dependencies, input ceilings and guardrails (plus human inputs and objections for sales only). |
| Pursuit kit | all stages | shared stages | The 11 Word and Excel templates from `Stage templates/`, turned into editable sheets: 32 sheets in grid or section-form views, with cell edits saved to Postgres and a download link for each original file. Also covers the nine skill packages and the other skills and tools. FlyHigh samples are listed but not bundled (client-confidential). |
| Win room | ✓ | — | FlyHigh scorecard: summary tiles, a G7 test, the buying-group heatmap (18 people × 5 dimensions), a competitor archetype rubric and the pending actions, with editable status. |
| Response quality | all 14 sections | scores shared sections 7, 9, 10 | The 10-criterion rubric scorer. Points = weight × score ÷ 4, and a missing must-have caps the section at 89. The overall weighted score starts at the 66.6 baseline. |
| Journeys, Insights, Data models | ✓ | ✓ | Solution content: written in pursuit stage 4 and carried into implementation. |
| Guided workflow, Toolkit catalog | — | ✓ | The implementation lifecycle. |

**How the lens is enforced:** every API call carries `X-Persona`. The persona maps to a lens in `lens_role`, and `access_rule` decides which screens and pursuit stages each lens can open. Blocked calls return 403. The chat guide filters its answers the same way. Rules live in the database, so you can change them without touching code (e.g. `UPDATE access_rule SET delivery=TRUE WHERE code='commercials'`). The persona picker is a role lens, not authentication: in production, put SSO in front and derive the persona from IdP groups.

Pursuit content comes from `AI Native Sales Engineering Methodology.docx`, `AI Native Sales Engineering Workflow.pptx`, `00 Start here.docx`, `Stage templates/` and `Skills/`. Seeds are in `backend/app/pursuit_data.py` and `assets/seed/pursuit_kit.json`. The blank templates are in `assets/templates/`.

## Skills studio

**Skills studio** (both lenses) runs every skill against the app's own data and keeps a history of runs.

**Pursuit skills (9).** These are the AI Native Sales Engineering skills, run as engines. Their SKILL.md files are in `skills/pursuit/`.

| Skill | What the engine does in the app | Wired into |
|---|---|---|
| rfp-response-orchestrator | Gate readiness: open questions, bracketed template inputs, artefacts and stamps; records the named approver's decision in a gate log | Pursuit stage → "Check readiness and record the gate" |
| rfp-win-scorecard | Recomputes overall, RAG, simple and influence-weighted averages, competitor totals, projected score, the G7 test and pending actions; supports new scoring rounds | Win room → Rescore; scores editable inline |
| rfp-commercials-model | Prices options from hours × rate card, applies term discounts (flex = half of fixed), totals TCO and computes client-retained ROI and payback | Pursuit kit → Commercials workbook |
| rfp-section-rubric | Ranked fixes per section: must-haves first, then points lost | Skills studio |
| rfp-section-loop | Loop log per section with PASS, PLATEAU, BLOCKED or ESCALATE status (max four rounds) | Response quality → Record round |
| rfp-section-builder | Section brief: must-haves with status, fix list, stamps and rules | Response quality → Section brief |
| proposal-to-job-descriptions | One JD per role and location tier, with the tier must-haves taken from the skill | Skills studio (stage 5, shared) |
| niche-brand-guardian | Audit of titles and text: three-word titles, sentence case, INDICATIVE on money, competitor names, filler | Skills studio |
| niche-exec-offering | Slide spec JSON for a response section | Skills studio |

**Snowflake delivery skills (46).** These are the generators for every slash skill in the implementation lifecycle, in `skills/delivery/snowskills/`. They emit reviewable Snowflake artefacts:

- Snowflake SQL: database roles and future grants, tag-based masking, row access policies, SCIM, network and authentication policies, Snowpipe, streams and tasks, dynamic tables, semantic views, data metric functions, alerts, Time Travel rollback.
- schemachange scripts and dbt models.
- Terraform and GitHub Actions.
- Runbooks.

The skill chips on the guided workflow open the matching skill in the studio. Every skill is also packaged as a standalone `.skill` file that needs only the Python standard library:

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev
```

The packages are in `skills/packages/delivery/sf-*.skill` and `skills/packages/pursuit/*.skill`, with a CLI: `cd skills/delivery && python -m snowskills list`.

**Modes:**

- **Engine:** deterministic. The same inputs always give the same output.
- **Copy prompt for your LLM:** puts the skill, the inputs and the draft on the clipboard.
- **Draft with LLM:** needs an LLM configured in `.env` (see [configuration](configuration.md)).

**Lens rules:**

- Pursuit skills follow their stages: the win scorecard and commercials model are sales-only; the other pursuit skills are shared.
- The orchestrator only opens stages the lens can see.
- Delivery skills are delivery-only.

**SQL checks and execution:**

- Generated SQL is syntax-checked with sqlglot (Snowflake dialect). Snowflake-specific DDL that the validator cannot parse is reported as such.
- Delivery personas can execute reviewed SQL in a **DEV** account. The connector is already in the image; set these in `.env`: `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PRIVATE_KEY_FILE` (or `SNOWFLAKE_PASSWORD`), `SNOWFLAKE_ROLE`, `SNOWFLAKE_WAREHOUSE` and `SNOWFLAKE_ALLOW_EXECUTE=true`.
- Every execution needs an explicit "a person reviewed this" confirmation and is logged.

## API quick reference

- `GET /api/stages`, `GET /api/stages/{code}`: the workflow stages and the detail for one stage
- `GET /api/components?kind=agent|skill|tool|framework|snowflake`
- `GET /api/personas`, `GET /api/insights`, `GET /api/datamodel`
- `POST|PUT|DELETE /api/curate/{table}[/{id}]`: works on `persona`, `journey_step`, `insight_dashboard`, `insight_question`, `domain`, `subject_area`, `data_entity`, `attribute`, `kpi`, `conformed_dim`, `component`
- `GET /api/progress/{session}`, `POST /api/progress`
- `POST /api/chat` `{message, session_id, context:{stage}}`

## Notes

- Dashboard figures are illustrative, as in the reference content. fleet management system and labor management system content is flagged as discovery only.
- Each KPI's `source_fact` is a suggested mapping to confirm in discovery. Facts without detailed attributes in the reference content get a placeholder attribute so they can be curated.
- To re-seed from scratch, run `python -m app.seed`. This drops curated edits.
