"""Platform assurance skills: ETL, SCD, CDC, replay, report comparison, row access, metrics, golden queries, load and warehouse tuning."""
import json
import re

from . import Field, header, ident, lit, skill, to_yaml


@skill(name="gen-etl-tests", stage="assurance", agent="ETL Test Agent", title="Generate ETL tests",
       description="Check converted mappings against legacy output: row counts by business date, transformation rules recomputed from source, and lookup integrity.",
       snowflake=["Set-based assertions", "MINUS comparisons", "dbt singular tests"],
       fields=[Field("target", "Target table", "text", "FLYHIGH_DEV_SILVER.TRANSPORT.FACT_SHIPMENT_LEG"),
               Field("source", "Source table (landed legacy output)", "text", "FLYHIGH_DEV_BRONZE.TRANSPORT.ODI_FACT_SHIPMENT_LEG"),
               Field("key", "Key", "text", "SHIPMENT_LEG_ID"),
               Field("date_col", "Business date column", "text", "SHIP_DATE"),
               Field("rules", "Rules (column = expected expression over source alias s)", "lines",
                     "DELAY_HOURS = DATEDIFF(minute, s.PLANNED_ARRIVAL, s.ACTUAL_ARRIVAL) / 60\nLOADED_MILES = s.TOTAL_MILES - s.EMPTY_MILES"),
               Field("lookups", "Lookups (column | dimension.key)", "lines", "CARRIER_KEY | FLYHIGH_DEV_GOLD.TRANSPORT.DIM_CARRIER.CARRIER_KEY")],
       steps=["Land legacy output for the same window.", "Run etl_tests.sql; each block must return zero rows.", "Commit as dbt singular tests for CI."],
       gate="QA lead reviews each failure; evidence kept per wave")
def gen_etl_tests(p, sk):
    t, s, k, d = p.s("target"), p.s("source"), ident(p.s("key")), ident(p.s("date_col"))
    blocks = [header(sk, f"ETL tests for {t} · each block returns zero rows when it passes"),
              f"-- 1. Counts by business date\nSELECT COALESCE(a.d, b.d) AS business_date, a.n AS legacy_rows, b.n AS new_rows\nFROM (SELECT {d} AS d, COUNT(*) n FROM {s} GROUP BY 1) a\nFULL OUTER JOIN (SELECT {d} AS d, COUNT(*) n FROM {t} GROUP BY 1) b ON a.d = b.d\nWHERE NVL(a.n, -1) <> NVL(b.n, -1);",
              f"-- 2. Keys missing either side\nSELECT {k}, 'missing in new' AS issue FROM (SELECT {k} FROM {s} MINUS SELECT {k} FROM {t})\nUNION ALL\nSELECT {k}, 'not in legacy' FROM (SELECT {k} FROM {t} MINUS SELECT {k} FROM {s});"]
    for i, r in enumerate(p.lines("rules"), 3):
        col, _, expr = r.partition("=")
        blocks.append(f"-- {i}. Rule {col.strip()}\nSELECT t.{k}, t.{col.strip()} AS actual, {expr.strip()} AS expected\nFROM {t} t JOIN {s} s ON s.{k} = t.{k}\nWHERE NOT EQUAL_NULL(ROUND(t.{col.strip()}, 4), ROUND({expr.strip()}, 4));")
    for r in p.lines("lookups"):
        col, _, dim = r.partition("|")
        dt, dk = dim.strip().rsplit(".", 1)
        blocks.append(f"-- Lookup {col.strip()}\nSELECT t.{col.strip()}, COUNT(*) FROM {t} t LEFT JOIN {dt} d ON d.{dk} = t.{col.strip()}\nWHERE d.{dk} IS NULL GROUP BY 1;")
    return {"files": {"etl_tests.sql": "\n\n".join(blocks) + "\n"}, "summary": f"{len(blocks) - 1} test blocks for {t}."}


@skill(name="check-scd", stage="assurance", agent="DW Validator", title="Check SCD history",
       description="Validate SCD type 2 dimensions: one current row per key, no overlapping or gapped intervals, valid dates, and facts joined to the version valid at event time.",
       snowflake=["Window functions (LAG / LEAD)", "QUALIFY", "Interval checks"],
       fields=[Field("dimension", "SCD2 dimension", "text", "FLYHIGH_DEV_GOLD.CUSTOMER.DIM_CUSTOMER"),
               Field("natural_key", "Natural key", "text", "CUSTOMER_ID"), Field("surrogate", "Surrogate key", "text", "CUSTOMER_KEY"),
               Field("from_col", "Effective from", "text", "EFFECTIVE_FROM"), Field("to_col", "Effective to", "text", "EFFECTIVE_TO"),
               Field("current_col", "Is-current flag", "text", "IS_CURRENT"),
               Field("fact", "Fact to check (table | fk | event date)", "text", "FLYHIGH_DEV_GOLD.WAREHOUSE.FACT_WAREHOUSE_TASK | CUSTOMER_KEY | TASK_START")],
       steps=["Run after each load into the dimension.", "Any rows returned are defects; fix the merge logic, not the data."],
       gate="DW validator results reviewed by the QA lead")
def check_scd(p, sk):
    d, nk, sk_, f, to, cur = p.s("dimension"), ident(p.s("natural_key")), ident(p.s("surrogate")), ident(p.s("from_col")), ident(p.s("to_col")), ident(p.s("current_col"))
    ft, fk, ev = [x.strip() for x in p.s("fact").split("|")]
    sql = f"""{header(sk, f'SCD2 checks on {d}')}-- 1. More than one current row per key
SELECT {nk}, COUNT(*) FROM {d} WHERE {cur} GROUP BY 1 HAVING COUNT(*) > 1;

-- 2. Keys with no current row
SELECT {nk} FROM {d} GROUP BY 1 HAVING COUNT_IF({cur}) = 0;

-- 3. Overlaps and gaps between consecutive versions
SELECT {nk}, {sk_}, {f}, {to}, LEAD({f}) OVER (PARTITION BY {nk} ORDER BY {f}) AS next_from
FROM {d}
QUALIFY next_from IS NOT NULL AND next_from <> {to};

-- 4. Invalid intervals
SELECT * FROM {d} WHERE {f} IS NULL OR ({to} IS NOT NULL AND {to} < {f}) OR ({cur} AND {to} < '9999-12-31');

-- 5. Facts pointing at a version not valid at event time
SELECT f.{fk}, f.{ev}, d.{f}, d.{to}
FROM {ft} f JOIN {d} d ON d.{sk_} = f.{fk}
WHERE NOT (f.{ev} >= d.{f} AND f.{ev} < COALESCE(d.{to}, '9999-12-31'))
LIMIT 100;
"""
    return {"files": {"scd_checks.sql": sql}, "summary": f"Five SCD2 checks on {d}."}


@skill(name="test-cdc", stage="assurance", agent="Pipeline Monitor", title="Test CDC and file loads",
       description="Check pipes, streams and tasks: pipe status, load errors, freshness against SLA, late-arriving rows, stale streams and failed task runs.",
       snowflake=["SYSTEM$PIPE_STATUS", "COPY_HISTORY", "SHOW STREAMS (stale)", "TASK_HISTORY"],
       fields=[Field("pipes", "Pipes (one per line)", "lines", "FLYHIGH_PRD_BRONZE.WAREHOUSE.PIPE_WMS_TASKS"),
               Field("tables", "Tables (table | timestamp column | SLA minutes)", "lines", "FLYHIGH_PRD_BRONZE.WAREHOUSE.WMS_TASKS_RAW | _LOADED_AT | 15\nFLYHIGH_PRD_SILVER.WAREHOUSE.WAREHOUSE_TASK | TASK_END | 30"),
               Field("schema", "Schema with streams and tasks", "text", "FLYHIGH_PRD_BRONZE.WAREHOUSE")],
       steps=["Run cdc_checks.sql during SIT and keep it as a monitoring query.", "Convert the freshness block into an alert with /gen-runbook."],
       gate="Pipeline monitor results reviewed before UAT")
def test_cdc(p, sk):
    out = [header(sk, "CDC and load checks")]
    for pipe in p.lines("pipes"):
        out.append(f"SELECT PARSE_JSON(SYSTEM$PIPE_STATUS({lit(pipe)})) AS status;")
    for l in p.lines("tables"):
        t, c, sla = [x.strip() for x in l.split("|")]
        out.append(f"-- {t}\nSELECT {lit(t)} AS table_name, MAX({c}) AS latest, DATEDIFF(minute, MAX({c}), CURRENT_TIMESTAMP()) AS minutes_behind,\n"
                   f"       IFF(DATEDIFF(minute, MAX({c}), CURRENT_TIMESTAMP()) > {sla}, 'BREACH', 'OK') AS freshness\nFROM {t};")
        out.append(f"SELECT file_name, status, row_count, error_count, first_error_message, last_load_time\n"
                   f"FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(TABLE_NAME => {lit(t)}, START_TIME => DATEADD(day, -1, CURRENT_TIMESTAMP())))\nWHERE error_count > 0;")
    sch = p.s("schema")
    out.append(f"SHOW STREAMS IN SCHEMA {sch};\nSELECT \"name\", \"stale\", \"stale_after\" FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) WHERE \"stale\" = 'true' OR \"stale_after\" < DATEADD(day, 2, CURRENT_TIMESTAMP());")
    out.append(f"SELECT name, state, error_message, scheduled_time\nFROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(SCHEDULED_TIME_RANGE_START => DATEADD(day, -1, CURRENT_TIMESTAMP())))\n"
               f"WHERE database_name = {lit(sch.split('.')[0])} AND state = 'FAILED';")
    return {"files": {"cdc_checks.sql": "\n\n".join(out) + "\n"}, "summary": "Pipe, freshness, error, stream and task checks."}


@skill(name="replay-load", stage="assurance", agent="Pipeline Monitor", title="Replay a load",
       description="Replay files or a time window idempotently: refresh the pipe, force-reload specific files and deduplicate on the key so reruns never double count.",
       snowflake=["ALTER PIPE ... REFRESH", "COPY INTO ... FORCE / FILES", "MERGE with QUALIFY dedupe"],
       fields=[Field("pipe", "Pipe", "text", "FLYHIGH_PRD_BRONZE.WAREHOUSE.PIPE_WMS_TASKS"),
               Field("stage", "Stage", "text", "@FLYHIGH_PRD_BRONZE.WAREHOUSE.STG_WMS_TASKS"),
               Field("table", "Bronze table", "text", "FLYHIGH_PRD_BRONZE.WAREHOUSE.WMS_TASKS_RAW"),
               Field("files", "Files to force-reload (one per line)", "lines", "2026/11/04/tasks_0900.csv"),
               Field("since", "Replay files modified after (timestamp)", "text", "2026-11-04 08:00:00"),
               Field("key", "Dedupe key", "text", "TASK_ID")],
       steps=["Pick refresh (missed notifications) or force (bad data fixed upstream).", "Run, then run the dedupe block.", "Re-run /test-cdc and /reconcile for the window."],
       gate="Pipeline owner approves replays in production")
def replay_load(p, sk):
    files = ", ".join(lit(f) for f in p.lines("files"))
    k, t = ident(p.s("key")), p.s("table")
    sql = f"""{header(sk, 'idempotent replay')}-- A. Missed event notifications: reload files the pipe has not seen (last 7 days only)
ALTER PIPE {p.s('pipe')} REFRESH MODIFIED_AFTER = {lit(p.s('since'))};

-- B. Upstream re-sent corrected files: force-reload named files
COPY INTO {t} FROM {p.s('stage')} FILES = ({files}) FORCE = TRUE ON_ERROR = 'ABORT_STATEMENT';

-- C. Keep one row per key (latest load wins) so replays never double count
CREATE TABLE {t}_BAK_REPLAY CLONE {t};   -- audit snapshot before dedupe (drop after sign-off)
DELETE FROM {t} USING (
  SELECT {k}, _LOADED_AT FROM {t}
  QUALIFY ROW_NUMBER() OVER (PARTITION BY {k} ORDER BY _LOADED_AT DESC) > 1
) d WHERE {t}.{k} = d.{k} AND {t}._LOADED_AT = d._LOADED_AT;
"""
    return {"files": {"replay.sql": sql}, "summary": "Refresh, force-reload and dedupe steps."}


@skill(name="compare-reports", stage="assurance", agent="BI Comparator", title="Compare reports",
       description="Compare legacy report numbers (OAC, Power BI) with the new Snowflake/Tableau numbers per filter combination, within tolerance, and produce signed evidence.",
       snowflake=["Comparison table + query", "Snowflake values from semantic views or gold tables"],
       fields=[Field("report", "Report", "text", "Site Daily Operations"),
               Field("checks", "Checks (metric | filter | new-value SQL)", "lines",
                     "On-time ship % | site=DAL1, week=2026-W44 | SELECT ROUND(100 * AVG(IFF(SHIPPED_AT <= CUTOFF_AT, 1, 0)), 2) FROM FLYHIGH_PRD_GOLD.WAREHOUSE.FACT_OUTBOUND_ORDER_LINE WHERE SITE_KEY = 101 AND FISCAL_WEEK = '2026-W44'\n"
                     "Pick accuracy | site=DAL1, week=2026-W44 | SELECT 1 - SUM(SHORT_ERROR_QTY)/SUM(LINES_HANDLED) FROM FLYHIGH_PRD_GOLD.WAREHOUSE.FACT_WAREHOUSE_TASK WHERE SITE_KEY = 101"),
               Field("tolerance_pct", "Tolerance %", "number", "0.5")],
       steps=["Fill legacy_values.csv from the legacy report export.", "Load it to REPORT_COMPARE_LEGACY, run compare.sql.", "Attach the result to the BI validation evidence."],
       gate="Business owner signs each report as matching or explained")
def compare_reports(p, sk):
    rows = [[x.strip() for x in l.split("|", 2)] for l in p.lines("checks")]
    csv = "report,metric,filter,legacy_value\n" + "".join(f"{p.s('report')},{r[0]},\"{r[1]}\",[legacy value]\n" for r in rows)
    sql = [header(sk, f"report comparison · {p.s('report')}"),
           "CREATE TABLE IF NOT EXISTS FLYHIGH_PRD_GOLD.QA.REPORT_COMPARE_LEGACY (REPORT VARCHAR, METRIC VARCHAR, FILTER VARCHAR, LEGACY_VALUE NUMBER(38,6));",
           "CREATE TABLE IF NOT EXISTS FLYHIGH_PRD_GOLD.QA.REPORT_COMPARE_NEW LIKE FLYHIGH_PRD_GOLD.QA.REPORT_COMPARE_LEGACY;"]
    for r in rows:
        sql.append(f"-- {r[0]} · {r[1]} (the SQL must return a single value)\n"
                   f"INSERT INTO FLYHIGH_PRD_GOLD.QA.REPORT_COMPARE_NEW SELECT {lit(p.s('report'))}, {lit(r[0])}, {lit(r[1])}, ({r[2].rstrip(';')});")
    tol = p.n("tolerance_pct", 0.5)
    sql.append(f"""
SELECT l.metric, l.filter, l.legacy_value, n.legacy_value AS new_value,
       ROUND(100 * (n.legacy_value - l.legacy_value) / NULLIF(l.legacy_value, 0), 3) AS diff_pct,
       IFF(ABS(100 * (n.legacy_value - l.legacy_value) / NULLIF(l.legacy_value, 0)) <= {tol}, 'MATCH', 'CHECK') AS status
FROM FLYHIGH_PRD_GOLD.QA.REPORT_COMPARE_LEGACY l
LEFT JOIN FLYHIGH_PRD_GOLD.QA.REPORT_COMPARE_NEW n USING (report, metric, filter)
WHERE l.report = {lit(p.s('report'))};""")
    return {"files": {"legacy_values.csv": csv, "compare.sql": "\n".join(sql) + "\n"}, "summary": f"{len(rows)} checks for {p.s('report')}."}


@skill(name="test-rls", stage="assurance", agent="BI Comparator", title="Test row-level security",
       description="Prove each persona sees exactly its rows: simulate roles with POLICY_CONTEXT, compare visible counts with expectations and check masked columns.",
       snowflake=["EXECUTE USING POLICY_CONTEXT", "Row access and masking policies"],
       fields=[Field("table", "Protected table", "text", "FLYHIGH_PRD_GOLD.CUSTOMER.FACT_ORDER_RELEASE"),
               Field("column", "Entitlement column", "text", "CUSTOMER_ID"),
               Field("cases", "Cases (role | expected visible values comma, or *)", "lines", "FR_PORTAL_ACME | C-1001\nFR_PORTAL_GLOBEX | C-2002\nFR_EXEC | *"),
               Field("masked", "Masked column to check (optional)", "text", "FLYHIGH_PRD_GOLD.CUSTOMER.DIM_CUSTOMER.CONTACT_EMAIL")],
       steps=["Run as a role allowed to use POLICY_CONTEXT (policy admin).", "Every 'FAIL' row is a defect; re-run after each policy change."],
       gate="Data owner signs the persona visibility matrix")
def test_rls(p, sk):
    t, c = p.s("table"), ident(p.s("column"))
    out = [header(sk, f"row access tests on {t}")]
    for l in p.lines("cases"):
        role, _, exp = [x.strip() for x in l.partition("|")]
        if exp == "*":
            out.append(f"-- {role}: sees all rows\nEXECUTE USING POLICY_CONTEXT(CURRENT_ROLE => {lit(ident(role))}) AS\n"
                       f"SELECT {lit(ident(role))} AS role, IFF(COUNT(*) = (SELECT COUNT(*) FROM {t}), 'PASS', 'FAIL') AS result FROM {t};")
        else:
            vals = ", ".join(lit(v.strip()) for v in exp.split(","))
            out.append(f"-- {role}: sees only {exp}\nEXECUTE USING POLICY_CONTEXT(CURRENT_ROLE => {lit(ident(role))}) AS\n"
                       f"SELECT {lit(ident(role))} AS role, IFF(COUNT_IF({c} NOT IN ({vals})) = 0 AND COUNT(*) > 0, 'PASS', 'FAIL') AS result FROM {t};")
    if p.s("masked"):
        tbl, col = p.s("masked").rsplit(".", 1)
        for l in p.lines("cases")[:2]:
            role = ident(l.split("|")[0])
            out.append(f"EXECUTE USING POLICY_CONTEXT(CURRENT_ROLE => {lit(role)}) AS SELECT {lit(role)} AS role, {col} FROM {tbl} LIMIT 5;")
    return {"files": {"rls_tests.sql": "\n\n".join(out) + "\n"}, "summary": f"{len(p.lines('cases'))} persona cases."}


@skill(name="test-metrics", stage="assurance", agent="Semantic Tester", title="Test semantic metrics",
       description="Check each certified KPI in the semantic view against an independent base-table query, so the semantic layer returns the legacy numbers.",
       snowflake=["SEMANTIC_VIEW() query clause", "Cortex Analyst consumes the same view"],
       fields=[Field("view", "Semantic view", "text", "FLYHIGH_PRD_GOLD.WAREHOUSE.SV_SITE_OPS"),
               Field("cases", "Cases (metric | dimension | base SQL returning dimension, value)", "lines",
                     "task.uph | site.site_name | SELECT s.SITE_NAME, SUM(f.UNITS_HANDLED)/NULLIF(SUM(f.DURATION_MIN)/60,0) FROM FLYHIGH_PRD_GOLD.WAREHOUSE.FACT_WAREHOUSE_TASK f JOIN FLYHIGH_PRD_GOLD.WAREHOUSE.DIM_SITE s ON s.SITE_KEY = f.SITE_KEY GROUP BY 1")],
       steps=["Pull formulas from the KPI library.", "Run metric_tests.sql; mismatches block publishing the semantic view."],
       gate="Semantic tester evidence signed by the BI lead")
def test_metrics(p, sk):
    out = [header(sk, f"metric tests on {p.s('view')}")]
    for i, l in enumerate(p.lines("cases"), 1):
        m, d, base = [x.strip() for x in l.split("|", 2)]
        out.append(f"""-- Case {i}: {m} by {d}
WITH sv AS (
  SELECT * FROM SEMANTIC_VIEW({p.s('view')} DIMENSIONS {d} METRICS {m})
), base AS ({base.rstrip(';')})
SELECT COALESCE(sv.$1, base.$1) AS dim, sv.$2 AS semantic_value, base.$2 AS base_value,
       IFF(EQUAL_NULL(ROUND(sv.$2, 4), ROUND(base.$2, 4)), 'PASS', 'FAIL') AS result
FROM sv FULL OUTER JOIN base ON sv.$1 = base.$1
WHERE result = 'FAIL';""")
    return {"files": {"metric_tests.sql": "\n\n".join(out) + "\n"}, "summary": f"{len(p.lines('cases'))} metric cases."}


@skill(name="golden-queries", stage="assurance", agent="Semantic Tester", title="Golden queries",
       description="Register golden queries with expected result fingerprints and a procedure that re-runs them and flags drift after every release.",
       snowflake=["HASH_AGG fingerprints", "Snowflake Scripting procedure", "RESULT_SCAN"],
       fields=[Field("queries", "Golden queries (id | SQL)", "lines",
                     "GQ-OTIF-W44 | SELECT ROUND(AVG(IFF(ON_TIME AND IN_FULL,1,0)),4) FROM FLYHIGH_PRD_GOLD.TRANSPORT.FACT_ORDER_RELEASE WHERE FISCAL_WEEK = '2026-W44'\n"
                     "GQ-UPH-DAL1 | SELECT ROUND(SUM(UNITS_HANDLED)/NULLIF(SUM(DURATION_MIN)/60,0),2) FROM FLYHIGH_PRD_GOLD.WAREHOUSE.FACT_WAREHOUSE_TASK WHERE SITE_KEY = 101")],
       steps=["Capture expected fingerprints once from a signed-off baseline.", "Call the procedure after each promotion; drift fails the release."],
       gate="Semantic tester owns the golden set; changes need BI lead approval")
def golden_queries(p, sk):
    rows = [[x.strip() for x in l.split("|", 1)] for l in p.lines("queries")]
    sql = f"""{header(sk, 'golden query registry')}CREATE SCHEMA IF NOT EXISTS FLYHIGH_PRD_GOLD.QA;
CREATE TABLE IF NOT EXISTS FLYHIGH_PRD_GOLD.QA.GOLDEN_QUERY (ID VARCHAR PRIMARY KEY, SQL_TEXT VARCHAR, EXPECTED_HASH NUMBER, CAPTURED_AT TIMESTAMP_LTZ);
CREATE TABLE IF NOT EXISTS FLYHIGH_PRD_GOLD.QA.GOLDEN_RUN (ID VARCHAR, ACTUAL_HASH NUMBER, STATUS VARCHAR, RUN_AT TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP());

MERGE INTO FLYHIGH_PRD_GOLD.QA.GOLDEN_QUERY g USING (
  SELECT column1 AS id, column2 AS sql_text FROM VALUES
  {(','+chr(10)+'  ').join(f"({lit(r[0])}, {lit(r[1].rstrip(';'))})" for r in rows)}
) s ON g.id = s.id
WHEN MATCHED THEN UPDATE SET sql_text = s.sql_text
WHEN NOT MATCHED THEN INSERT (id, sql_text) VALUES (s.id, s.sql_text);

CREATE OR REPLACE PROCEDURE FLYHIGH_PRD_GOLD.QA.SP_RUN_GOLDEN(CAPTURE BOOLEAN)
RETURNS VARCHAR LANGUAGE SQL EXECUTE AS CALLER AS
$$
DECLARE
  c CURSOR FOR SELECT id, sql_text, expected_hash FROM FLYHIGH_PRD_GOLD.QA.GOLDEN_QUERY;
  h NUMBER;
  fails INTEGER DEFAULT 0;
BEGIN
  FOR r IN c DO
    EXECUTE IMMEDIATE r.sql_text;
    SELECT HASH_AGG(*) INTO :h FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
    IF (capture) THEN
      UPDATE FLYHIGH_PRD_GOLD.QA.GOLDEN_QUERY SET expected_hash = :h, captured_at = CURRENT_TIMESTAMP() WHERE id = r.id;
    ELSE
      INSERT INTO FLYHIGH_PRD_GOLD.QA.GOLDEN_RUN (id, actual_hash, status)
        VALUES (r.id, :h, IFF(:h = r.expected_hash, 'PASS', 'DRIFT'));
      IF (h <> r.expected_hash) THEN fails := fails + 1; END IF;
    END IF;
  END FOR;
  RETURN IFF(capture, 'captured', fails || ' golden queries drifted');
END;
$$;

-- CALL FLYHIGH_PRD_GOLD.QA.SP_RUN_GOLDEN(TRUE);   -- once, on the signed-off baseline
-- CALL FLYHIGH_PRD_GOLD.QA.SP_RUN_GOLDEN(FALSE);  -- after every release
"""
    return {"files": {"golden_queries.sql": sql}, "summary": f"{len(rows)} golden queries registered."}


@skill(name="load-test", stage="assurance", agent="Performance Agent", title="Load test",
       description="Run dashboard queries concurrently against a warehouse with a query tag, then report p50/p95 latency, queueing and spill from QUERY_HISTORY against the 5-second target.",
       snowflake=["QUERY_TAG", "INFORMATION_SCHEMA.QUERY_HISTORY_BY_WAREHOUSE", "Multi-cluster warehouses", "snowflake-connector-python"],
       fields=[Field("warehouse", "Warehouse", "text", "WH_BI"), Field("users", "Concurrent users", "number", "25"),
               Field("iterations", "Iterations per user", "number", "10"), Field("target_ms", "Target p95 (ms)", "number", "5000"),
               Field("queries", "Dashboard queries (one per line)", "lines",
                     "SELECT * FROM SEMANTIC_VIEW(FLYHIGH_PRD_GOLD.WAREHOUSE.SV_SITE_OPS DIMENSIONS site.site_name METRICS task.uph)\nSELECT SITE_KEY, COUNT(*) FROM FLYHIGH_PRD_GOLD.WAREHOUSE.FACT_WAREHOUSE_TASK WHERE TASK_DATE_KEY >= 20261001 GROUP BY 1")],
       steps=["Run load_test.py from a machine near the account region with a service user.", "Run analyze.sql with the printed tag.", "Hand results to /tune-warehouse."],
       gate="Performance agent results reviewed with the platform owner")
def load_test(p, sk):
    qs = json.dumps(p.lines("queries"), indent=2)
    py = f'''"""Concurrent load test · generated by {sk.package}. pip install snowflake-connector-python"""
import os, random, statistics, threading, time, uuid
import snowflake.connector

QUERIES = {qs}
USERS, ITERATIONS, WAREHOUSE = {int(p.n('users', 25))}, {int(p.n('iterations', 10))}, "{ident(p.s('warehouse'))}"
TAG = "loadtest-" + uuid.uuid4().hex[:8]
lat = []

def worker():
    con = snowflake.connector.connect(connection_name=os.getenv("SNOWFLAKE_CONNECTION", "default"))
    cur = con.cursor()
    cur.execute(f"USE WAREHOUSE {{WAREHOUSE}}"); cur.execute(f"ALTER SESSION SET QUERY_TAG = '{{TAG}}'")
    cur.execute("ALTER SESSION SET USE_CACHED_RESULT = FALSE")
    for _ in range(ITERATIONS):
        q = random.choice(QUERIES); t = time.perf_counter(); cur.execute(q).fetchall(); lat.append((time.perf_counter() - t) * 1000)
    con.close()

threads = [threading.Thread(target=worker) for _ in range(USERS)]
[t.start() for t in threads]; [t.join() for t in threads]
lat.sort()
p95 = lat[int(len(lat) * 0.95) - 1]
print(f"tag={{TAG}} runs={{len(lat)}} p50={{statistics.median(lat):.0f}}ms p95={{p95:.0f}}ms target={int(p.n('target_ms', 5000))}ms",
      "PASS" if p95 <= {int(p.n('target_ms', 5000))} else "FAIL")
'''
    sql = f"""{header(sk, 'analyze a load-test run')}SET tag = 'loadtest-xxxxxxxx';   -- printed by load_test.py
SELECT COUNT(*) AS queries,
       APPROX_PERCENTILE(total_elapsed_time, 0.5) AS p50_ms, APPROX_PERCENTILE(total_elapsed_time, 0.95) AS p95_ms,
       AVG(queued_overload_time) AS avg_queued_ms, SUM(bytes_spilled_to_local_storage) AS spill_local, SUM(bytes_spilled_to_remote_storage) AS spill_remote
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY_BY_WAREHOUSE(WAREHOUSE_NAME => {lit(ident(p.s('warehouse')))}, RESULT_LIMIT => 10000))
WHERE query_tag = $tag;
"""
    return {"files": {"load_test.py": py, "analyze.sql": sql}, "summary": f"{int(p.n('users',25))} users × {int(p.n('iterations',10))} iterations on {p.s('warehouse')}."}


@skill(name="tune-warehouse", stage="assurance", agent="Performance Agent", title="Tune warehouse",
       description="Diagnose a warehouse from ACCOUNT_USAGE (queueing, spill, credits) and emit sizing, multi-cluster, auto-suspend, query acceleration and resource-monitor settings.",
       snowflake=["WAREHOUSE_LOAD_HISTORY / WAREHOUSE_METERING_HISTORY", "Multi-cluster + scaling policy", "Query Acceleration Service", "Resource monitors", "Search optimization"],
       fields=[Field("warehouse", "Warehouse", "text", "WH_BI"), Field("size", "Current size", "choice", "MEDIUM", options=["XSMALL", "SMALL", "MEDIUM", "LARGE", "XLARGE"]),
               Field("avg_queued", "Avg queued load (from diagnosis, 0 if unknown)", "number", "0.4"),
               Field("spill_gb", "Remote spill GB / day", "number", "0"),
               Field("monthly_credits", "Monthly credit quota", "number", "800"),
               Field("users_peak", "Peak concurrent users", "number", "60")],
       steps=["Run diagnose.sql and enter the figures.", "Apply tuning.sql in a change window; re-run /load-test.", "Keep the resource monitor on every warehouse."],
       gate="Platform owner approves sizing and credit quotas")
def tune_warehouse(p, sk):
    wh = ident(p.s("warehouse"))
    sizes = ["XSMALL", "SMALL", "MEDIUM", "LARGE", "XLARGE"]
    size = p.s("size")
    rec, notes = [], []
    if p.n("spill_gb") > 1:
        size = sizes[min(sizes.index(size) + 1, len(sizes) - 1)]
        notes.append("Remote spill: size up one step (memory-bound queries).")
    maxc = 1
    if p.n("avg_queued") > 0.1 or p.n("users_peak") > 30:
        maxc = min(6, max(2, int(p.n("users_peak") // 20)))
        notes.append(f"Queueing/concurrency: multi-cluster 1–{maxc} with STANDARD scaling instead of a bigger size.")
    diag = f"""{header(sk, f'diagnose {wh}')}SELECT DATE_TRUNC('hour', start_time) AS hour, AVG(avg_running) AS running, AVG(avg_queued_load) AS queued
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_LOAD_HISTORY WHERE warehouse_name = {lit(wh)} AND start_time > DATEADD(day, -14, CURRENT_TIMESTAMP())
GROUP BY 1 ORDER BY queued DESC LIMIT 48;

SELECT DATE(start_time) AS day, SUM(credits_used) AS credits FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE warehouse_name = {lit(wh)} AND start_time > DATEADD(day, -30, CURRENT_TIMESTAMP()) GROUP BY 1 ORDER BY 1;

SELECT query_id, total_elapsed_time/1000 AS sec, bytes_spilled_to_remote_storage/POWER(1024,3) AS remote_spill_gb, partitions_scanned, partitions_total
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY WHERE warehouse_name = {lit(wh)} AND start_time > DATEADD(day, -7, CURRENT_TIMESTAMP())
ORDER BY total_elapsed_time DESC LIMIT 25;

SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_ACCELERATION_ELIGIBLE WHERE warehouse_name = {lit(wh)} ORDER BY eligible_query_acceleration_time DESC LIMIT 20;
"""
    tune = f"""{header(sk, f'tune {wh}')}ALTER WAREHOUSE {wh} SET
  WAREHOUSE_SIZE = '{size}'
  MIN_CLUSTER_COUNT = 1 MAX_CLUSTER_COUNT = {maxc} SCALING_POLICY = 'STANDARD'
  AUTO_SUSPEND = 60 AUTO_RESUME = TRUE
  ENABLE_QUERY_ACCELERATION = TRUE QUERY_ACCELERATION_MAX_SCALE_FACTOR = 4
  STATEMENT_TIMEOUT_IN_SECONDS = 600 STATEMENT_QUEUED_TIMEOUT_IN_SECONDS = 120;

CREATE OR REPLACE RESOURCE MONITOR RM_{wh} WITH CREDIT_QUOTA = {int(p.n('monthly_credits', 800))} FREQUENCY = MONTHLY START_TIMESTAMP = IMMEDIATELY
  TRIGGERS ON 75 PERCENT DO NOTIFY ON 90 PERCENT DO NOTIFY ON 100 PERCENT DO SUSPEND;
ALTER WAREHOUSE {wh} SET RESOURCE_MONITOR = RM_{wh};

-- Point lookups on large tables: consider search optimization
-- ALTER TABLE FLYHIGH_PRD_GOLD.TRANSPORT.FACT_TRACKING_EVENT ADD SEARCH OPTIMIZATION ON EQUALITY(SHIPMENT_ID);
"""
    if maxc == 1:
        tune = tune.replace("MIN_CLUSTER_COUNT = 1 MAX_CLUSTER_COUNT = 1 SCALING_POLICY = 'STANDARD'\n  ", "")
    return {"files": {"diagnose.sql": diag, "tuning.sql": tune}, "summary": f"{wh}: {size}, clusters 1–{maxc}, auto-suspend 60 s.", "notes": notes}
