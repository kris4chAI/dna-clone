-- =============================================================================
-- TAF view contract for the FlyHigh assurance workbench (Databricks engine)
--
-- The workbench reads ONLY these views when the Databricks engine is used. Paste this section into ddl/taf_ddl_all.sql
-- (views section, after the tables, before grants) so 00a_DDL_Bootstrap owns it.
-- The app itself never executes DDL.
--
-- Placeholders substituted by the bootstrap: ${catalog} and ${raw_schema}.
--
-- RULE: no semicolon may appear inside any string literal or comment in this
-- file. The bootstrap splits on the semicolon character naively.
-- RULE again, because it is the easiest way to cut a statement in half: none in
-- literals, none in comments.
--
-- Run ids carry different prefixes (R..., UI..., G..._TAF) so "latest" is always
-- decided by time, never by MAX(run_id).
-- =============================================================================

-- ---------------------------------------------------------------------------
-- vw_taf_report - catalog LEFT JOIN results. The MANUAL branch matters:
-- without it every unexecuted manual case reports as Not_Run.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW ${catalog}.${raw_schema}.vw_taf_report AS
WITH latest AS (
  SELECT run_id FROM ${catalog}.${raw_schema}.taf_results
  GROUP BY run_id ORDER BY MAX(executed_at) DESC LIMIT 1
)
SELECT
  c.run_id, c.test_id, c.test_type, c.severity, c.suite, c.requirement_group, c.requirement_id,
  c.requirement_title, c.source_schema, c.source_table, c.source_column, c.target_schema,
  c.target_table, c.target_column, c.sql_expression, c.assertion_name, c.assertion_params,
  c.template_name, c.template_params, c.filter_condition, c.expected_result, c.explanation,
  c.owner, c.is_enabled, c.source_format, c.source_ref,
  COALESCE(r.result_status, CASE WHEN c.test_type = 'MANUAL' THEN 'Manual' ELSE 'Not_Run' END) AS result_status,
  r.result_severity, r.violation_count, r.actual_result, r.executed_sql, r.sample_rows_preview,
  r.sample_rows_json, r.scalar_value, r.executed_at, r.duration_ms, r.triggered_by, r.error_message,
  r.upstream_pipeline_run, r.filter_applied, r.filter_skipped_reason,
  (c.run_id = (SELECT run_id FROM latest)) AS is_latest_run
FROM ${catalog}.${raw_schema}.taf_test_catalog c
LEFT JOIN ${catalog}.${raw_schema}.taf_results r
  ON r.run_id = c.run_id AND r.test_id = c.test_id;

CREATE OR REPLACE VIEW ${catalog}.${raw_schema}.vw_ui_taf_column_cases AS
SELECT * FROM ${catalog}.${raw_schema}.vw_taf_report WHERE test_type = 'COLUMN';

CREATE OR REPLACE VIEW ${catalog}.${raw_schema}.vw_ui_taf_sql_cases AS
SELECT * FROM ${catalog}.${raw_schema}.vw_taf_report WHERE test_type = 'SQL';

-- ---------------------------------------------------------------------------
-- runs
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW ${catalog}.${raw_schema}.vw_ui_taf_runs AS
SELECT run_id, started_at, finished_at, status, run_scope, triggered_by, upstream_pipeline_run,
       input_source, total_tests, pass_count, fail_count, warn_count, error_count, manual_count,
       not_run_count, notes
FROM ${catalog}.${raw_schema}.taf_run_manifest;

CREATE OR REPLACE VIEW ${catalog}.${raw_schema}.vw_ui_taf_running_manifests AS
SELECT * FROM ${catalog}.${raw_schema}.vw_ui_taf_runs WHERE status = 'Running';

CREATE OR REPLACE VIEW ${catalog}.${raw_schema}.vw_taf_run_trend AS
SELECT run_id, started_at, finished_at, status, triggered_by, total_tests, pass_count, fail_count,
       warn_count, error_count, manual_count, not_run_count
FROM ${catalog}.${raw_schema}.taf_run_manifest
WHERE status <> 'Running';

-- passed last run, fails this run - the highest-signal alert there is
CREATE OR REPLACE VIEW ${catalog}.${raw_schema}.vw_taf_regressions AS
WITH runs AS (
  SELECT run_id, MAX(executed_at) AS t FROM ${catalog}.${raw_schema}.taf_results GROUP BY run_id
), ordered AS (
  SELECT run_id, LAG(run_id) OVER (ORDER BY t) AS prev_run_id FROM runs
)
SELECT o.run_id, o.prev_run_id, cur.test_id, cur.test_type, cur.result_severity AS severity,
       prev.result_status AS prev_status, cur.result_status, cur.violation_count, cur.actual_result
FROM ordered o
JOIN ${catalog}.${raw_schema}.taf_results cur ON cur.run_id = o.run_id
JOIN ${catalog}.${raw_schema}.taf_results prev ON prev.run_id = o.prev_run_id AND prev.test_id = cur.test_id
WHERE prev.result_status = 'Pass' AND cur.result_status IN ('Fail', 'Error');

-- ---------------------------------------------------------------------------
-- unified TAF + EXTERNAL. One row per scenario. check_id identifies the
-- generated query - for the external suite one query covers many scenarios,
-- so check_id is a hash of its SQL. Adjust the external column mapping
-- (sheet_name, load_type) to your suite.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW ${catalog}.${raw_schema}.vw_validation_results AS
WITH ext_latest AS (
  SELECT e.run_id
  FROM (SELECT DISTINCT run_id FROM ${catalog}.${raw_schema}.taf_external_results) e
  LEFT JOIN ${catalog}.${raw_schema}.taf_run_manifest m ON m.run_id = e.run_id
  ORDER BY m.started_at DESC NULLS LAST, e.run_id DESC
  LIMIT 1
)
SELECT 'TAF' AS suite, t.run_id, t.test_id, t.test_id AS check_id, t.requirement_group AS sheet_name,
       t.requirement_group AS category, t.test_type, t.severity AS priority, t.severity,
       t.requirement_title AS test_scenario, CAST(NULL AS STRING) AS load_type,
       t.requirement_id AS feature_reference, t.result_status AS status, t.violation_count,
       t.duration_ms, t.executed_at, t.executed_sql AS sql_script,
       COALESCE(t.error_message, t.actual_result) AS comments, t.filter_applied, t.is_latest_run
FROM ${catalog}.${raw_schema}.vw_taf_report t
UNION ALL
SELECT 'EXTERNAL' AS suite, x.run_id, x.test_id, substr(sha2(COALESCE(x.sql_script, x.test_id), 256), 1, 16) AS check_id,
       x.file_type AS sheet_name, x.category, x.test_type, x.priority,
       CASE WHEN upper(x.priority) IN ('P1', 'HIGH', 'CRITICAL') THEN 'High'
            WHEN upper(x.priority) IN ('P3', 'LOW') THEN 'Low' ELSE 'Medium' END AS severity,
       x.test_scenario, x.source_type AS load_type, CAST(NULL AS STRING) AS feature_reference,
       CASE upper(x.status) WHEN 'PASS' THEN 'Pass' WHEN 'PASSED' THEN 'Pass' WHEN 'FAIL' THEN 'Fail'
            WHEN 'FAILED' THEN 'Fail' WHEN 'WARN' THEN 'Warn' WHEN 'ERROR' THEN 'Error'
            WHEN 'SKIPPED' THEN 'Skipped' ELSE COALESCE(x.status, 'Not_Run') END AS status,
       x.violation_count, x.duration_ms, CAST(NULL AS TIMESTAMP) AS executed_at, x.sql_script,
       x.comments, CAST(NULL AS STRING) AS filter_applied,
       (x.run_id = (SELECT run_id FROM ext_latest)) AS is_latest_run
FROM ${catalog}.${raw_schema}.taf_external_results x;

CREATE OR REPLACE VIEW ${catalog}.${raw_schema}.vw_validation_scenarios AS
SELECT * FROM ${catalog}.${raw_schema}.vw_validation_results;

CREATE OR REPLACE VIEW ${catalog}.${raw_schema}.vw_validation_dashboard AS
SELECT suite, run_id, MAX(executed_at) AS executed_at, COUNT(*) AS total,
       SUM(CASE WHEN status = 'Pass' THEN 1 ELSE 0 END) AS pass_count,
       SUM(CASE WHEN status = 'Fail' THEN 1 ELSE 0 END) AS fail_count,
       SUM(CASE WHEN status = 'Warn' THEN 1 ELSE 0 END) AS warn_count,
       SUM(CASE WHEN status = 'Error' THEN 1 ELSE 0 END) AS error_count,
       SUM(CASE WHEN status NOT IN ('Pass', 'Fail', 'Warn', 'Error') THEN 1 ELSE 0 END) AS other_count
FROM ${catalog}.${raw_schema}.vw_validation_results
WHERE is_latest_run = true
GROUP BY suite, run_id;

CREATE OR REPLACE VIEW ${catalog}.${raw_schema}.vw_validation_by_category AS
SELECT suite, run_id, category, COUNT(*) AS total,
       SUM(CASE WHEN status = 'Pass' THEN 1 ELSE 0 END) AS pass_count,
       SUM(CASE WHEN status = 'Fail' THEN 1 ELSE 0 END) AS fail_count,
       SUM(CASE WHEN status = 'Error' THEN 1 ELSE 0 END) AS error_count,
       COUNT(DISTINCT check_id) AS distinct_checks
FROM ${catalog}.${raw_schema}.vw_validation_results
WHERE is_latest_run = true
GROUP BY suite, run_id, category;

-- one row per distinct generated query
CREATE OR REPLACE VIEW ${catalog}.${raw_schema}.vw_validation_check_summary AS
SELECT suite, run_id, check_id, is_latest_run, MIN(category) AS category,
       CASE WHEN MAX(CASE WHEN status = 'Error' THEN 1 ELSE 0 END) = 1 THEN 'Error'
            WHEN MAX(CASE WHEN status = 'Fail' THEN 1 ELSE 0 END) = 1 THEN 'Fail'
            WHEN MAX(CASE WHEN status = 'Warn' THEN 1 ELSE 0 END) = 1 THEN 'Warn'
            WHEN MAX(CASE WHEN status = 'Pass' THEN 1 ELSE 0 END) = 1 THEN 'Pass'
            ELSE MIN(status) END AS status,
       COUNT(*) AS scenario_count,
       SUM(CASE WHEN status IN ('Fail', 'Error') THEN 1 ELSE 0 END) AS failed_scenarios,
       SUM(violation_count) AS violation_count, MAX(duration_ms) AS duration_ms
FROM ${catalog}.${raw_schema}.vw_validation_results
GROUP BY suite, run_id, check_id, is_latest_run;

CREATE OR REPLACE VIEW ${catalog}.${raw_schema}.vw_validation_check_dashboard AS
SELECT suite, run_id, COUNT(*) AS distinct_checks,
       SUM(CASE WHEN status IN ('Fail', 'Error') THEN 1 ELSE 0 END) AS failed_checks,
       SUM(scenario_count) AS scenarios
FROM ${catalog}.${raw_schema}.vw_validation_check_summary
WHERE is_latest_run = true
GROUP BY suite, run_id;

-- ---------------------------------------------------------------------------
-- failures + resolution. failure_id is the composite test_id::run_id.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW ${catalog}.${raw_schema}.vw_validation_failures AS
WITH f AS (
  SELECT 'TAF' AS suite, run_id, test_id, severity, result_status AS status, requirement_title,
         violation_count, actual_result, error_message, sample_rows_preview, is_latest_run
  FROM ${catalog}.${raw_schema}.vw_taf_report
  WHERE result_status IN ('Fail', 'Error')
  UNION ALL
  SELECT suite, run_id, test_id, severity, status, test_scenario AS requirement_title,
         violation_count, CAST(NULL AS STRING) AS actual_result, comments AS error_message,
         CAST(NULL AS STRING) AS sample_rows_preview, is_latest_run
  FROM ${catalog}.${raw_schema}.vw_validation_results
  WHERE suite = 'EXTERNAL' AND status IN ('Fail', 'Error')
)
SELECT concat(f.test_id, '::', f.run_id) AS failure_id, f.*,
       fr.recommended_fix, COALESCE(fr.resolved, false) AS resolved, fr.resolved_by, fr.resolved_at
FROM f
LEFT JOIN ${catalog}.${raw_schema}.taf_failure_resolution fr
  ON fr.failure_id = concat(f.test_id, '::', f.run_id);

-- ---------------------------------------------------------------------------
-- control plane + scenario history
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW ${catalog}.${raw_schema}.vw_validation_test_suite AS
SELECT test_id, suite, sheet_name, functional_category, test_category, priority_label, load_type,
       feature_reference, test_scenario, is_active, deactivated_by, deactivated_at, updated_at
FROM ${catalog}.${raw_schema}.taf_test_suite;

CREATE OR REPLACE VIEW ${catalog}.${raw_schema}.vw_ui_taf_scenario_runs AS
SELECT run_id, scenario_id, scenario, description, status, violation_count, duration_ms,
       evidence_json, sql_used, error_message, executed_at
FROM ${catalog}.${raw_schema}.taf_scenario_runs;

-- grants for the app service principal (reads views, writes 4 base tables)
GRANT USE CATALOG ON CATALOG ${catalog} TO `${app_sp}`;
GRANT USE SCHEMA ON SCHEMA ${catalog}.${raw_schema} TO `${app_sp}`;
GRANT SELECT ON SCHEMA ${catalog}.${raw_schema} TO `${app_sp}`;
GRANT MODIFY ON TABLE ${catalog}.${raw_schema}.taf_failure_resolution TO `${app_sp}`;
GRANT MODIFY ON TABLE ${catalog}.${raw_schema}.taf_test_suite TO `${app_sp}`;
GRANT MODIFY ON TABLE ${catalog}.${raw_schema}.taf_run_manifest TO `${app_sp}`;
GRANT MODIFY ON TABLE ${catalog}.${raw_schema}.taf_scenario_runs TO `${app_sp}`;
GRANT READ VOLUME, WRITE VOLUME ON VOLUME ${catalog}.${raw_schema}.taf_uploads TO `${app_sp}`;
