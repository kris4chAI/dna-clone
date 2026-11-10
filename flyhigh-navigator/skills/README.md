# Skills

Everything FlyHigh Navigator knows how to *do* lives in this folder. The app loads these files at runtime; the
`.skill` packages are the same skills packaged for Claude (Settings → Skills → upload) or for running standalone.

| Folder | What it holds |
|---|---|
| `pursuit/<name>/SKILL.md` | The 9 AI Native Pursuit Engineering pursuit skills (source of truth) |
| `pmo/<name>/SKILL.md` | The 4 PMO skills from the AI Native Delivery Playbook (source of truth) |
| `assurance/<name>/SKILL.md` | The 5 assurance workbench skills (source of truth) |
| `delivery/snowskills/` | The Snowflake generator library behind the 46 delivery skills (pure Python, stdlib only) |
| `delivery/catalog/sf-*/` | Readable SKILL.md and example parameters per delivery skill |
| `packages/pursuit/*.skill`, `packages/pmo/*.skill`, `packages/assurance/*.skill`, `packages/delivery/*.skill` | Packaged skills (zip format) |

Rebuild packages and this catalog after editing a skill: `python tools/package_skills.py`.

Run a delivery skill without the app:

```bash
cd skills/delivery && python -m snowskills list
python -m snowskills run gen-grants --params catalog/sf-gen-grants/examples/params.json --out /tmp/out
```

## Pursuit skills (9)

| Skill | Purpose | Files |
|---|---|---|
| `niche-brand-guardian` | Audit proposal content against the firm's brand and honesty rules before anything leaves the team: titles, sentence case, stamps on unvalidated figures, competitor names and logo approvals. | [SKILL.md](pursuit/niche-brand-guardian/SKILL.md) · [package](packages/pursuit/niche-brand-guardian.skill) |
| `niche-exec-offering` | Turn a pursuit section into a slide spec (titles of three words or fewer, message in subtitles, stamps, evidence tags) for the firm's deck builder. | [SKILL.md](pursuit/niche-exec-offering/SKILL.md) · [package](packages/pursuit/niche-exec-offering.skill) |
| `proposal-to-job-descriptions` | Generate role-by-role job descriptions from a proposal, or from a user's role list mapped to standard data & analytics offering playbooks, with must-haves flagged for onshore, nearshore and offshore. | [SKILL.md](pursuit/proposal-to-job-descriptions/SKILL.md) · [package](packages/pursuit/proposal-to-job-descriptions.skill) |
| `rfp-commercials-model` | Turn a proposal's resource loading into commercials: rate card, scope options, managed services, fixed and flex term discounts, contract value, TCO and ROI, plus the matching pricing slides. | [SKILL.md](pursuit/rfp-commercials-model/SKILL.md) · [package](packages/pursuit/rfp-commercials-model.skill) |
| `rfp-response-orchestrator` | Run a Niche Consulting RFP pursuit end to end with the AI Native Pursuit Engineering method: nine gated stages from RFP signal to orals, with artefacts, skills, stamps and stage questions. | [SKILL.md](pursuit/rfp-response-orchestrator/SKILL.md) · [package](packages/pursuit/rfp-response-orchestrator.skill) |
| `rfp-section-builder` | Extract the section structure of a Niche Consulting RFP response, then generate or revise any one of its 14 sections independently from a section brief, ready for rubric scoring. | [SKILL.md](pursuit/rfp-section-builder/SKILL.md) · [package](packages/pursuit/rfp-section-builder.skill) |
| `rfp-section-loop` | Improve RFP response sections with a generate, score and revise loop until each reaches 90% of the rubric with all must-haves, or escalate the inputs needed. | [SKILL.md](pursuit/rfp-section-loop/SKILL.md) · [package](packages/pursuit/rfp-section-loop.skill) |
| `rfp-section-rubric` | Independently score one RFP response section against a 10-criterion weighted rubric and its must-haves, citing evidence, and return the highest-leverage fixes. | [SKILL.md](pursuit/rfp-section-rubric/SKILL.md) · [package](packages/pursuit/rfp-section-rubric.skill) |
| `rfp-win-scorecard` | Score a proposal against every buyer, evaluator and competitor archetype in a RAG-coloured Excel scorecard and list only the pending actions that lift the score. | [SKILL.md](pursuit/rfp-win-scorecard/SKILL.md) · [package](packages/pursuit/rfp-win-scorecard.skill) |

## PMO skills (4)

| Skill | Purpose | Files |
|---|---|---|
| `pmo-readiness-scorecard` | Score a Snowflake modernization track on the 17-question AI-native readiness model across five weighted dimensions, set the qualification band and turn lagging dimensions into owned remediation actions. | [SKILL.md](pmo/pmo-readiness-scorecard/SKILL.md) · [package](packages/pmo/pmo-readiness-scorecard.skill) |
| `pmo-steering-pack` | Compile the FlyHigh steering pack: readiness per track, KPI scorecard by RAG, top risks and issues, decisions needed, playbook progress and recent gate decisions. | [SKILL.md](pmo/pmo-steering-pack/SKILL.md) · [package](packages/pmo/pmo-steering-pack.skill) |
| `pmo-unit-effort-estimator` | Estimate an AI-native Snowflake program with the unit-effort model: objects by complexity, AI frameworks and discovery, pilot share and wave speed-up, returning person-days, person-months and average FTE. | [SKILL.md](pmo/pmo-unit-effort-estimator/SKILL.md) · [package](packages/pmo/pmo-unit-effort-estimator.skill) |
| `pmo-usecase-prioritizer` | Rank data modernization activities for AI and agent enablement on value, repeatability, feasibility, trust and automation, and assign each a lane: pilot wave, next wave, assist only or human gate. | [SKILL.md](pmo/pmo-usecase-prioritizer/SKILL.md) · [package](packages/pmo/pmo-usecase-prioritizer.skill) |

## Assurance skills (5)

| Skill | Purpose | Files |
|---|---|---|
| `aw-impact-analyzer` | From a list of changed files, find the impacted test cases through test-to-code mappings and rank the regression suite by risk (mapping score × priority × failure history). | [SKILL.md](assurance/aw-impact-analyzer/SKILL.md) · [package](packages/assurance/aw-impact-analyzer.skill) |
| `aw-test-case-generator` | Generate a versioned suite of functional, negative, data, security, performance, UI and API test cases from user stories or from requirements, screen lists and API endpoints, for a Snowflake modernization program. | [SKILL.md](assurance/aw-test-case-generator/SKILL.md) · [package](packages/assurance/aw-test-case-generator.skill) |
| `aw-test-data-generator` | Generate synthetic Snowflake test data for valid, boundary, invalid and masked scenarios from a schema file (CREATE TABLE DDL, CSV header) or a data-model entity, with INSERT SQL and data-quality checks. | [SKILL.md](assurance/aw-test-data-generator/SKILL.md) · [package](packages/assurance/aw-test-data-generator.skill) |
| `aw-test-report-summarizer` | Summarize test results for a release: user-story coverage, results, feature readiness, hotspots (critical, flaky, stable), defects by severity, most-failed tests with root cause, and the impact × likelihood grid. | [SKILL.md](assurance/aw-test-report-summarizer/SKILL.md) · [package](packages/assurance/aw-test-report-summarizer.skill) |
| `aw-test-script-generator` | Generate keyword-driven pytest scripts or BDD features for a test case over reusable components (login, navigation, filters, KPI tiles, SQL, legacy comparison, row access, masking, latency, Cortex). | [SKILL.md](assurance/aw-test-script-generator/SKILL.md) · [package](packages/assurance/aw-test-script-generator.skill) |

## Snowflake delivery skills (46)

| Stage | Skill | What · agent | Snowflake features | Files |
|---|---|---|---|---|
| 1 Discover | `/discover` | Estate discovery · Estate Analyzer agent | ACCOUNT_USAGE.TABLES, ACCOUNT_USAGE.ACCESS_HISTORY (lineage), ACCOUNT_USAGE.QUERY_HISTORY | [SKILL.md](delivery/catalog/sf-discover/SKILL.md) · [package](packages/delivery/sf-discover.skill) |
| 1 Discover | `/pi-commit-and-raise-pull-request` | Commit and raise pull request · PRD Agent | Artefacts versioned next to Snowflake code | [SKILL.md](delivery/catalog/sf-pi-commit-and-raise-pull-request/SKILL.md) · [package](packages/delivery/sf-pi-commit-and-raise-pull-request.skill) |
| 1 Discover | `/pi-define-requirements` | Define requirements (PRD) · PRD Agent | SNOWFLAKE.ACCOUNT_USAGE.TABLES / COLUMNS (catalog probe), Horizon catalog search | [SKILL.md](delivery/catalog/sf-pi-define-requirements/SKILL.md) · [package](packages/delivery/sf-pi-define-requirements.skill) |
| 1 Discover | `/plan-waves` | Plan migration waves · Estate Analyzer agent | Wave plan drives Snowflake AIM and schemachange folders | [SKILL.md](delivery/catalog/sf-plan-waves/SKILL.md) · [package](packages/delivery/sf-plan-waves.skill) |
| 2 Design | `/pi-design-solution` | Design the solution · Solution Design Agent | Database per layer and environment, Warehouses per workload, Database roles | [SKILL.md](delivery/catalog/sf-pi-design-solution/SKILL.md) · [package](packages/delivery/sf-pi-design-solution.skill) |
| 4 Foundation build | `/convert-ddl` | Convert legacy DDL · DDL Converter | Snowflake data types, Informational constraints, Sequences / IDENTITY | [SKILL.md](delivery/catalog/sf-convert-ddl/SKILL.md) · [package](packages/delivery/sf-convert-ddl.skill) |
| 4 Foundation build | `/design-auth` | Design authentication and encryption · Auth Designer | SAML2 security integration, Network rules + network policies, Authentication / password / session policies | [SKILL.md](delivery/catalog/sf-design-auth/SKILL.md) · [package](packages/delivery/sf-design-auth.skill) |
| 4 Foundation build | `/design-rbac` | Design role-based access · RBAC Designer | Database roles, Functional account roles, Future grants | [SKILL.md](delivery/catalog/sf-design-rbac/SKILL.md) · [package](packages/delivery/sf-design-rbac.skill) |
| 4 Foundation build | `/gen-grants` | Generate grants · RBAC Designer | CREATE DATABASE ROLE, GRANT ... ON FUTURE TABLES / VIEWS, GRANT DATABASE ROLE TO ROLE | [SKILL.md](delivery/catalog/sf-gen-grants/SKILL.md) · [package](packages/delivery/sf-gen-grants.skill) |
| 4 Foundation build | `/gen-keypair` | Generate key-pair auth · Auth Designer | RSA_PUBLIC_KEY / RSA_PUBLIC_KEY_2 rotation, RSA_PUBLIC_KEY_FP verification | [SKILL.md](delivery/catalog/sf-gen-keypair/SKILL.md) · [package](packages/delivery/sf-gen-keypair.skill) |
| 4 Foundation build | `/gen-masking` | Generate masking policies · Policy Author | Object tagging, Tag-based masking policies, IS_ROLE_IN_SESSION | [SKILL.md](delivery/catalog/sf-gen-masking/SKILL.md) · [package](packages/delivery/sf-gen-masking.skill) |
| 4 Foundation build | `/gen-migration` | Generate schemachange migration · DDL Converter | schemachange (versioned V__ / repeatable R__ scripts), Time Travel for rollback | [SKILL.md](delivery/catalog/sf-gen-migration/SKILL.md) · [package](packages/delivery/sf-gen-migration.skill) |
| 4 Foundation build | `/gen-rls` | Generate row access policies · Policy Author | Row access policies, Entitlement mapping table, IS_ROLE_IN_SESSION / CURRENT_ROLE | [SKILL.md](delivery/catalog/sf-gen-rls/SKILL.md) · [package](packages/delivery/sf-gen-rls.skill) |
| 4 Foundation build | `/gen-scim` | Generate SCIM provisioning · Identity Mapper | CREATE SECURITY INTEGRATION TYPE = SCIM, SYSTEM$GENERATE_SCIM_ACCESS_TOKEN | [SKILL.md](delivery/catalog/sf-gen-scim/SKILL.md) · [package](packages/delivery/sf-gen-scim.skill) |
| 4 Foundation build | `/gen-zone-ddl` | Generate zone DDL · Zone Mapper | CREATE DATABASE / SCHEMA ... WITH MANAGED ACCESS, Object tags, Tasks | [SKILL.md](delivery/catalog/sf-gen-zone-ddl/SKILL.md) · [package](packages/delivery/sf-gen-zone-ddl.skill) |
| 4 Foundation build | `/map-groups` | Map IdP groups to roles · Identity Mapper | SCIM-provisioned roles, DEFAULT_ROLE / DEFAULT_WAREHOUSE, GRANT ROLE | [SKILL.md](delivery/catalog/sf-map-groups/SKILL.md) · [package](packages/delivery/sf-map-groups.skill) |
| 4 Foundation build | `/map-zones` | Map data layers and zones · Zone Mapper | Databases and managed-access schemas, DATA_RETENTION_TIME_IN_DAYS, Transient tables | [SKILL.md](delivery/catalog/sf-map-zones/SKILL.md) · [package](packages/delivery/sf-map-zones.skill) |
| 6 Platform migration | `/convert-etl` | Convert ETL mappings · Pipeline Converter | dbt-snowflake (incremental, merge), Dynamic tables (TARGET_LAG), Snowflake-native workflows | [SKILL.md](delivery/catalog/sf-convert-etl/SKILL.md) · [package](packages/delivery/sf-convert-etl.skill) |
| 6 Platform migration | `/convert-procs` | Convert PL/SQL procedures · Code Converter agent | Snowflake Scripting (LANGUAGE SQL), EXECUTE IMMEDIATE, RESULTSET / cursors | [SKILL.md](delivery/catalog/sf-convert-procs/SKILL.md) · [package](packages/delivery/sf-convert-procs.skill) |
| 6 Platform migration | `/gen-unit-tests` | Generate unit tests · Test Generator | Data metric functions (SNOWFLAKE.CORE.NULL_COUNT, DUPLICATE_COUNT, FRESHNESS), DATA_METRIC_SCHEDULE, dbt tests | [SKILL.md](delivery/catalog/sf-gen-unit-tests/SKILL.md) · [package](packages/delivery/sf-gen-unit-tests.skill) |
| 6 Platform migration | `/load-initial` | Initial history load · Migration Runner | COPY INTO with VALIDATION_MODE, Parquet / CSV file formats, LOAD_HISTORY / COPY_HISTORY | [SKILL.md](delivery/catalog/sf-load-initial/SKILL.md) · [package](packages/delivery/sf-load-initial.skill) |
| 6 Platform migration | `/parallel-run` | Parallel run · Cutover Validator | Tasks with CRON schedules, Alerts + SYSTEM$SEND_EMAIL, Notification integrations | [SKILL.md](delivery/catalog/sf-parallel-run/SKILL.md) · [package](packages/delivery/sf-parallel-run.skill) |
| 6 Platform migration | `/reconcile` | Reconcile source and target · Migration Runner | HASH_AGG, MINUS set comparison, Results table for evidence | [SKILL.md](delivery/catalog/sf-reconcile/SKILL.md) · [package](packages/delivery/sf-reconcile.skill) |
| 6 Platform migration | `/repoint-bi` | Repoint BI to semantic views · BI Repoint agent | CREATE SEMANTIC VIEW, SEMANTIC_VIEW() queries, Cortex Analyst | [SKILL.md](delivery/catalog/sf-repoint-bi/SKILL.md) · [package](packages/delivery/sf-repoint-bi.skill) |
| 6 Platform migration | `/repoint-ingest` | Repoint ingestion · Ingest Repoint agent | Storage integration + external stage, Snowpipe AUTO_INGEST, Streams + tasks (MERGE) | [SKILL.md](delivery/catalog/sf-repoint-ingest/SKILL.md) · [package](packages/delivery/sf-repoint-ingest.skill) |
| 8 Platform assurance | `/check-scd` | Check SCD history · DW Validator | Window functions (LAG / LEAD), QUALIFY, Interval checks | [SKILL.md](delivery/catalog/sf-check-scd/SKILL.md) · [package](packages/delivery/sf-check-scd.skill) |
| 8 Platform assurance | `/compare-reports` | Compare reports · BI Comparator | Comparison table + query, Snowflake values from semantic views or gold tables | [SKILL.md](delivery/catalog/sf-compare-reports/SKILL.md) · [package](packages/delivery/sf-compare-reports.skill) |
| 8 Platform assurance | `/gen-etl-tests` | Generate ETL tests · ETL Test Agent | Set-based assertions, MINUS comparisons, dbt singular tests | [SKILL.md](delivery/catalog/sf-gen-etl-tests/SKILL.md) · [package](packages/delivery/sf-gen-etl-tests.skill) |
| 8 Platform assurance | `/golden-queries` | Golden queries · Semantic Tester | HASH_AGG fingerprints, Snowflake Scripting procedure, RESULT_SCAN | [SKILL.md](delivery/catalog/sf-golden-queries/SKILL.md) · [package](packages/delivery/sf-golden-queries.skill) |
| 8 Platform assurance | `/load-test` | Load test · Performance Agent | QUERY_TAG, INFORMATION_SCHEMA.QUERY_HISTORY_BY_WAREHOUSE, Multi-cluster warehouses | [SKILL.md](delivery/catalog/sf-load-test/SKILL.md) · [package](packages/delivery/sf-load-test.skill) |
| 8 Platform assurance | `/replay-load` | Replay a load · Pipeline Monitor | ALTER PIPE ... REFRESH, COPY INTO ... FORCE / FILES, MERGE with QUALIFY dedupe | [SKILL.md](delivery/catalog/sf-replay-load/SKILL.md) · [package](packages/delivery/sf-replay-load.skill) |
| 8 Platform assurance | `/test-cdc` | Test CDC and file loads · Pipeline Monitor | SYSTEM$PIPE_STATUS, COPY_HISTORY, SHOW STREAMS (stale) | [SKILL.md](delivery/catalog/sf-test-cdc/SKILL.md) · [package](packages/delivery/sf-test-cdc.skill) |
| 8 Platform assurance | `/test-metrics` | Test semantic metrics · Semantic Tester | SEMANTIC_VIEW() query clause, Cortex Analyst consumes the same view | [SKILL.md](delivery/catalog/sf-test-metrics/SKILL.md) · [package](packages/delivery/sf-test-metrics.skill) |
| 8 Platform assurance | `/test-rls` | Test row-level security · BI Comparator | EXECUTE USING POLICY_CONTEXT, Row access and masking policies | [SKILL.md](delivery/catalog/sf-test-rls/SKILL.md) · [package](packages/delivery/sf-test-rls.skill) |
| 8 Platform assurance | `/tune-warehouse` | Tune warehouse · Performance Agent | WAREHOUSE_LOAD_HISTORY / WAREHOUSE_METERING_HISTORY, Multi-cluster + scaling policy, Query Acceleration Service | [SKILL.md](delivery/catalog/sf-tune-warehouse/SKILL.md) · [package](packages/delivery/sf-tune-warehouse.skill) |
| 9 Build & release | `/build-artifacts` | Build Snowflake artefacts · Build Agent | schemachange, Snowflake CLI (snow), Zero-copy clone for PR validation | [SKILL.md](delivery/catalog/sf-build-artifacts/SKILL.md) · [package](packages/delivery/sf-build-artifacts.skill) |
| 9 Build & release | `/gen-changelog` | Generate changelog · Release Agent | Release metadata for schemachange versions | [SKILL.md](delivery/catalog/sf-gen-changelog/SKILL.md) · [package](packages/delivery/sf-gen-changelog.skill) |
| 9 Build & release | `/lint-sql` | Lint SQL · Quality Gate | SQLFluff snowflake dialect, Anti-pattern checks (SELECT *, ORDER BY without LIMIT, CREATE OR REPLACE on tables) | [SKILL.md](delivery/catalog/sf-lint-sql/SKILL.md) · [package](packages/delivery/sf-lint-sql.skill) |
| 9 Build & release | `/pr-template` | Pull request template · Quality Gate | Evidence links to Snowflake query IDs and recon tables | [SKILL.md](delivery/catalog/sf-pr-template/SKILL.md) · [package](packages/delivery/sf-pr-template.skill) |
| 9 Build & release | `/promote` | Promote dev → stage → prod · Promotion Agent | schemachange per environment, Snowflake CLI, Golden queries after deploy | [SKILL.md](delivery/catalog/sf-promote/SKILL.md) · [package](packages/delivery/sf-promote.skill) |
| 9 Build & release | `/release-notes` | Release notes · Release Agent | Objects changed, Evidence: GOLDEN_RUN, RECON_RESULT query IDs | [SKILL.md](delivery/catalog/sf-release-notes/SKILL.md) · [package](packages/delivery/sf-release-notes.skill) |
| 9 Build & release | `/rollback` | Roll back a release · Promotion Agent | Time Travel AT (TIMESTAMP), UNDROP, Zero-copy clone | [SKILL.md](delivery/catalog/sf-rollback/SKILL.md) · [package](packages/delivery/sf-rollback.skill) |
| 10 Operate & monitor | `/gen-adr` | Architecture decision record · Docs Agent | Decision records next to Snowflake code | [SKILL.md](delivery/catalog/sf-gen-adr/SKILL.md) · [package](packages/delivery/sf-gen-adr.skill) |
| 10 Operate & monitor | `/gen-runbook` | Runbook with alerts · Docs Agent | CREATE ALERT, SYSTEM$SEND_EMAIL, TASK_HISTORY / COPY_HISTORY / QUERY_HISTORY | [SKILL.md](delivery/catalog/sf-gen-runbook/SKILL.md) · [package](packages/delivery/sf-gen-runbook.skill) |
| 10 Operate & monitor | `/gen-training` | Role-based training plan · Enablement Agent | Snowsight, Cortex Analyst, Semantic views | [SKILL.md](delivery/catalog/sf-gen-training/SKILL.md) · [package](packages/delivery/sf-gen-training.skill) |
| 10 Operate & monitor | `/kt-checklist` | Knowledge transfer and handover · Enablement Agent | GRANT OWNERSHIP ... COPY CURRENT GRANTS, Service user and key handover, Resource monitor ownership | [SKILL.md](delivery/catalog/sf-kt-checklist/SKILL.md) · [package](packages/delivery/sf-kt-checklist.skill) |
