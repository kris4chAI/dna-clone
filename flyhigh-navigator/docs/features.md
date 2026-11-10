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

| Screen | Pursuit lens | Delivery lens | PMO lens | What it does |
|---|---|---|---|---|
| Lifecycle overview | ✓ | ✓ | ✓ | The end-to-end map: pursuit (9 stages), program office (6 playbook stages) and implementation (10 steps). Locked segments are greyed out. Includes the access matrix for all lenses. |
| Pursuit stages | all 9 | 5, 8, 9 only | 5, 9 only | Flow map by loop (Build, Review, Fix) with the critical path, parallel lanes and gates G0–G8. Each stage shows its questions checklist (saved), input tiers, artefacts (systems of record flagged), skills and tools, templates, and the implementation steps it hands over to. A method tab covers principles, targets, team 13 → 6, measures, roles, dependencies, input ceilings and guardrails (plus human inputs and objections for the pursuit lens only). |
| Pursuit kit | all stages | shared stages | stages 5, 9 | The 11 Word and Excel templates from `Stage templates/`, turned into editable sheets: 32 sheets in grid or section-form views, with cell edits saved to Postgres and a download link for each original file. Also covers the nine skill packages and the other skills and tools. FlyHigh samples are listed but not bundled (client-confidential). |
| Win room | ✓ | — | — | FlyHigh scorecard: summary tiles, a G7 test, the buying-group heatmap (18 people × 5 dimensions), a competitor archetype rubric and the pending actions, with editable status. |
| Response quality | all 14 sections | scores shared sections 7, 9, 10 | — | The 10-criterion rubric scorer. Points = weight × score ÷ 4, and a missing must-have caps the section at 89. The overall weighted score starts at the 66.6 baseline. |
| Journeys, Insights, Data models | ✓ | ✓ | ✓ | Solution content: written in pursuit stage 4 and carried into implementation. |
| Guided workflow | — | ✓ | ✓ | The implementation lifecycle; the PMO follows it to run waves and gates. |
| Toolkit catalog | — | ✓ | — | Engineering agents, skills and tools. |

**How the lens is enforced:** every API call carries `X-Persona`. The persona maps to a lens in `lens_role`, and `access_rule.lenses` lists the lenses that can open each screen, pursuit stage and skill. Blocked calls return 403. The chat guide filters its answers the same way. Rules live in the database, so you can change them without touching code (e.g. `UPDATE access_rule SET lenses = lenses || 'pmo' WHERE code='commercials'`). The persona picker is a role lens, not authentication: in production, put SSO in front and derive the persona from IdP groups.

Pursuit content comes from the AI Native Pursuit Engineering method (`AI Native Sales Engineering Methodology.docx` and `Workflow.pptx` in the source folder), `00 Start here.docx`, `Stage templates/` and `Skills/`. Seeds are in `backend/app/pursuit_data.py` and `assets/seed/pursuit_kit.json`. The blank templates are in `assets/templates/`.

## Assurance workbench (assurance lens)

Modelled on an AI test-assurance workbench, rebuilt for FlyHigh. It sits after the implementation lifecycle and tests every step and wave. Working data lives in the `aw_*` tables; all engines are deterministic.

| Screen | Who | What it does |
|---|---|---|
| Overview | assurance, delivery, PMO | Counts (stories, cases, data sets, scripts, cycles, results, open defects, changed modules) and the four pillars with their components |
| Design | assurance | **Test case generator:** a two-step wizard, from user stories (the FlyHigh persona journeys and the FLY Jira backlog, by feature or picked one by one) or from documents (FSD/BRD lines, UI/UX screens, API endpoints); one case per acceptance criterion plus a negative case, typed functional, data, security, performance, UI or API; every run is a new suite version; CSV import. **Test data generator:** valid, boundary, invalid and masked rows from a data-model entity or pasted DDL / CSV header, with Snowflake INSERT SQL and DQ checks. **Test script generator:** keyword-driven pytest or BDD over the framework tree (applications, reusable components, standard suites, services) |
| Execution | assurance | Execution engines (local or cluster, with expiry), devices, releases; execution management (test planning, test execution with global engine and device, self-healing and failure analysis, CI/CD executions and schedules); test execution report (latest execution, results with root cause and resolution, every cycle). Runs use the built-in simulator, clearly labelled, until a real engine is connected |
| Analytics | assurance, delivery, PMO | Test report summarizer by release: feature-level status (story coverage, planned/actual/skipped/passed/failed, feature readiness, hotspots critical/flaky/stable), defect impact analysis (by status, severity and feature), defect list (status editable by assurance), impact-based test suggestion (impact × likelihood grid), test case performance (most failed with root cause and resolution) |
| Maintenance | assurance, delivery | Test case – code mappings (mapping table, code coverage per module, test case recommendations) and impact analysis: paste changed files (`git diff --name-only`), see the impacted cases ranked by risk, and create a regression test plan |

## Program office (PMO lens)

The PMO lens turns the **Snowflake AI Native Delivery Playbook** (data modernization variant) into a working program office. Content is seeded from `assets/seed/delivery_playbook.json`; working data lives in the `pmo_*` tables.

| Screen | Who | What it does | Playbook source |
|---|---|---|---|
| Delivery playbook | PMO, delivery | Primer (why delivery is changing, six mindset shifts, what stays human, the mental model, roles, what good looks like), the four archetypes (DMLC migration, DPLC data products, BMLC BI and semantic, AILC Cortex AI), the harness (delivery and Data Harness flows, toolkit, anatomy, agents by lane), ten practices, the FlyHigh worked example with the ten-month plan, artefacts and reference programs | Playbook HTML, Primer |
| Readiness scorecard | PMO | 17 questions scored 0–3 per track across five weighted dimensions (30/20/15/25/10). Bands: 75%+ ready, 50%+ ready with remediation. Lagging dimensions (< 67%) show their remediation. Tracks can be added. | Readiness Scorecard |
| Plan and execute | PMO, delivery | Six playbook stages with exit checklists (saved), the nine-phase onboarding plan and program metadata, 13 planning steps, 7 setup steps with harness readiness, execute activities per archetype (role, activity, agent or skill linked to the studio, tools, human involvement), autonomy tiers, minimum context and ways of working, optimize measures | Project Planning & Execution Template, Transformation Activities |
| Unit-effort estimator | PMO | ETL, warehouse and BI objects by complexity, frameworks and discovery; pilot share and wave speed-up; person-days, person-months, average FTE, activity split and framework complexity score. Scenarios are saved. | Estimation Template |
| AI use-case matrix | PMO | 37 activities across the four archetypes rated on value, repeatability, complexity, risk and automation (editable). The weighted score assigns a lane: pilot wave, next wave, assist only or human gate. Persona-level impact targets. | Use-Case Identification & Prioritization Matrix |
| KPI scorecard | PMO | Six measurement dimensions and 24 metrics in five categories with target, source, capture (auto, hybrid, manual) and cadence. Actuals, RAG status and notes are editable. | Measurement Framework & KPI Scorecard |
| Governance and RAID | PMO | RAID log (add, edit, close), three-tier operating model, cadence and decision areas, Responsible AI (lifecycle controls, eight pillars, agent-lifecycle risks mapped to NIST, ISO 42001, EU AI Act, OWASP), harness guardrails and the gate log | Responsible AI Governance Framework, Planning Template |
| Team and RACI | PMO, delivery | Pod topology, team composition per archetype, role evolution (traditional vs AI-native), four RACI matrices (planning, data products, migration, BI) | Team Formation & RACI |

All client, vendor and accelerator names in the playbook are rebranded for the sample: the client is ABC Retail, the initiative FlyHigh, the vendor Niche Consulting and its accelerators **Niche Accelerate**.

## Skills studio

**Skills studio** (every lens) runs every skill against the app's own data and keeps a history of runs.

**Pursuit skills (9).** These are the AI Native Pursuit Engineering skills, run as engines. Their SKILL.md files are in `skills/pursuit/`.

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

**Assurance skills (5).** Engines over the assurance workbench; SKILL.md files in `skills/assurance/`: `aw-test-case-generator`, `aw-test-data-generator`, `aw-test-script-generator`, `aw-test-report-summarizer`, `aw-impact-analyzer`. The assurance lens also gets the Snowflake testing skills (`/reconcile`, `/gen-unit-tests`, `/gen-etl-tests`, `/check-scd`, `/test-cdc`, `/replay-load`, `/compare-reports`, `/test-rls`, `/test-metrics`, `/golden-queries`, `/load-test`, `/tune-warehouse`, `/lint-sql`, `/parallel-run`).

**PMO skills (4).** Engines over the playbook data; SKILL.md files in `skills/pmo/`.

| Skill | What the engine does | Wired into |
|---|---|---|
| pmo-readiness-scorecard | Scores a track, sets the band and lists remediation for lagging dimensions; optionally raises them in the RAID log | Readiness scorecard |
| pmo-unit-effort-estimator | Runs the unit-effort model from object counts; optionally saves a scenario | Unit-effort estimator |
| pmo-usecase-prioritizer | Ranks activities by weighted score and lane | AI use-case matrix |
| pmo-steering-pack | Compiles readiness, KPI RAG, top RAID items, decisions needed, playbook progress and gate decisions into a steering pack | KPI scorecard, Governance |

The PMO lens also gets the planning and release delivery skills (`/plan-waves`, `/parallel-run`, `/gen-changelog`, `/release-notes`, `/gen-runbook`, `/gen-training`, `/kt-checklist`) and, for the hand-over stages, the pursuit orchestrator and job descriptions.

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

The packages are in `skills/packages/delivery/sf-*.skill`, `skills/packages/pursuit/*.skill` and `skills/packages/pmo/*.skill`, with a CLI: `cd skills/delivery && python -m snowskills list`.

**Modes:**

- **Engine:** deterministic. The same inputs always give the same output.
- **Copy prompt for your LLM:** puts the skill, the inputs and the draft on the clipboard.
- **Draft with LLM:** needs an LLM configured in `.env` (see [configuration](configuration.md)).

**Lens rules:**

- Pursuit skills follow their stages: the win scorecard and commercials model are pursuit-only; the other pursuit skills are shared with delivery.
- The orchestrator only opens stages the lens can see.
- Delivery skills are delivery-only, except the planning and release skills shared with the PMO.
- PMO skills are PMO-only; assurance skills are assurance-only. Only delivery personas can execute SQL on Snowflake.

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
- `GET /api/lens/list`: every lens with its personas (the sales lens is listed as coming soon)
- Assurance: `GET /api/assurance/overview|design|execution|analytics|maintenance`, `POST /api/assurance/design/cases/generate|import`, `POST /api/assurance/design/data/generate`, `POST /api/assurance/design/scripts/generate`, `POST|DELETE /api/assurance/execution/{engines|devices|releases|plans|cicd}`, `POST /api/assurance/execution/plans/{id}/run`, `PUT /api/assurance/analytics/defects/{id}`, `POST /api/assurance/maintenance/diff|remap|plan`
- PMO: `GET /api/pmo/playbook|readiness|roadmap|estimator|usecases|kpis|governance|team`, `PUT /api/pmo/readiness/{track}/{qid}`, `POST /api/pmo/readiness/tracks`, `PUT /api/pmo/roadmap/check`, `POST /api/pmo/estimator`, `PUT /api/pmo/usecases/{id}`, `PUT /api/pmo/kpis/{id}`, `POST|PUT|DELETE /api/pmo/raid[/{id}]`

## Notes

- Dashboard figures are illustrative, as in the reference content. fleet management system and labor management system content is flagged as discovery only.
- Each KPI's `source_fact` is a suggested mapping to confirm in discovery. Facts without detailed attributes in the reference content get a placeholder attribute so they can be curated.
- To re-seed from scratch, run `python -m app.seed`. This drops curated edits.
