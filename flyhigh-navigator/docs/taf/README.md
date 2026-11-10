# TAF data checks in the assurance workbench

TAF (the test automation framework) is the data-test framework of the assurance lens. It was merged in from the standalone TAF operator app; the screens now live inside the workbench and the Databricks App packaging is gone.

## What runs where

| Test kind | Statuses | Engines |
|---|---|---|
| TAF data checks: column, template and SQL assertions, plus the external suite | Pass, Fail, Warn, Error, Skipped, Manual, Info, Not_Run, Blocked | Simulator, Snowflake, Databricks |
| UI, API and performance test cases (test plans) | passed, failed, skipped | Simulator, Snowflake engines, devices |

- **Simulator** compiles the real Snowflake SQL for every check and returns deterministic outcomes. No setup.
- **Snowflake** runs the compiled SQL on the DEV account in `.env` (`SNOWFLAKE_ALLOW_EXECUTE=true`). The CDF date source uses `CHANGES(INFORMATION => DEFAULT)`.
- **Databricks** submits the TAF notebook chain as a one-time job (`jobs.submit`), writes a Running manifest row first, and reads results from `vw_taf_report` and `vw_validation_results` through the SQL Statement Execution API. Set `DATABRICKS_HOST`, a token or client id and secret, and the `APP_TAF_*` values.

Every run is mirrored into the workbench store (`taf_run`, `taf_result`), so the dashboards, triage and health scenarios work the same for all three engines.

## Screens

| Where | What |
|---|---|
| Overview | Latest run per suite: scenarios vs distinct checks, failed checks, runs in progress |
| Design > Data checks (TAF) | Test suite control plane: activate or deactivate (verified by re-query), sync from the latest run (never re-enables) |
| Execution > Data checks run | Engine, scope, run scope, sheet filter, filter mode and date source, tenant, period, segment, upload, evidence and notification options |
| Execution > Data check results | Per run: all, column, template and SQL assertions; executed SQL and sample rows |
| Execution > Run logs | One consolidated log per run |
| Analytics > Failure triage | Every failed data check and test case; record a recommended fix and resolve, or raise a linked defect in one action |
| Analytics > Health scenarios | Read-only checks on the runs themselves, each with what it cannot prove |

## Rules kept from TAF

- `LATEST_LOAD` cannot be combined with the `CDF` date source. Date modes need their dates; start must not be after end.
- Manual runs never fail for findings: findings make a run **Partial**. Zero executed checks is **Error**, never green.
- Tables without the requested filter column run unscoped and record the skip reason on every result row. SQL cases are scoped only when they contain `{filter}`.
- `failure_id` is `test_id::run_id`. Run ids look like `UI20261106_101500_a1b2c3`; "latest" is decided by time, never by `MAX(run_id)`.
- Running manifests older than `APP_TAF_STRANDED_HOURS` are closed as Error on the next read.

## Files

- `taf_app_views.sql`: the Unity Catalog view contract the Databricks engine reads.
- `loader-integration.md`: the loader change that makes a deactivated case load as `Not_Run` on the next Databricks run.
- Code: `backend/app/taf/` (logic, local compiler and simulator, Databricks engine, scenarios, seed catalog, API); `frontend/src/views/Taf.jsx`; `frontend/src/components/DataTable.jsx`.
- Tests: `backend/tests/` (`pytest backend/tests`).
