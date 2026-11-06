"""Platform migration skills: procedures, ETL, unit tests, ingestion, BI repoint, initial load, reconciliation, parallel run."""
import re

from . import Field, header, ident, lit, skill, to_yaml


@skill(name="convert-procs", stage="migration", agent="Code Converter agent", title="Convert PL/SQL procedures",
       description="Translate an Oracle PL/SQL procedure into a Snowflake Scripting stored procedure skeleton: signature, declarations, common functions, exceptions, with TODOs for constructs that need judgement.",
       snowflake=["Snowflake Scripting (LANGUAGE SQL)", "EXECUTE IMMEDIATE", "RESULTSET / cursors", "SnowConvert AI for full estates"],
       fields=[Field("plsql", "PL/SQL source", "textarea",
                     "CREATE OR REPLACE PROCEDURE WMS_DW.P_LOAD_LABOR(p_site IN NUMBER, p_day IN DATE) IS\n  v_rows NUMBER := 0;\nBEGIN\n  DELETE FROM WMS_DW.FACT_LABOR_ACTIVITY WHERE site_key = p_site AND work_date = TRUNC(p_day);\n"
                     "  INSERT INTO WMS_DW.FACT_LABOR_ACTIVITY (site_key, work_date, direct_hours, load_ts)\n  SELECT site_key, TRUNC(task_start), SUM(NVL(duration_min,0))/60, SYSDATE\n  FROM WMS_DW.FACT_WAREHOUSE_TASK WHERE site_key = p_site AND TRUNC(task_start) = TRUNC(p_day)\n  GROUP BY site_key, TRUNC(task_start);\n"
                     "  v_rows := SQL%ROWCOUNT;\n  DBMS_OUTPUT.PUT_LINE('rows ' || v_rows);\n  COMMIT;\nEXCEPTION\n  WHEN OTHERS THEN\n    ROLLBACK;\n    RAISE;\nEND;"),
               Field("target_schema", "Target schema", "text", "FLYHIGH_DEV_SILVER.WAREHOUSE")],
       steps=["Prefer SnowConvert AI for bulk conversion; use this skill for single procedures and review.", "Resolve every TODO; set-based rewrites beat row loops.", "Prove parity with /gen-etl-tests and /reconcile."],
       gate="Code converter output peer-reviewed; parity proven by reconciliation, not by the converter")
def convert_procs(p, sk):
    src, todo = p.s("plsql"), []
    m = re.search(r"PROCEDURE\s+([\w.]+)\s*\((.*?)\)\s*(IS|AS)", src, re.I | re.S)
    name = (m.group(1).split(".")[-1] if m else "P_CONVERTED").upper()
    args = []
    if m:
        for a in m.group(2).split(","):
            parts = a.split()
            if len(parts) >= 3:
                t = {"NUMBER": "NUMBER", "DATE": "TIMESTAMP_NTZ", "VARCHAR2": "VARCHAR"}.get(parts[-1].upper().split("(")[0], "VARCHAR")
                args.append(f"{parts[0].upper()} {t}")
                if parts[1].upper() in ("OUT", "INOUT"):
                    todo.append(f"OUT parameter {parts[0]} → return it in the RETURNS value or a result table.")
    body = src[m.end():] if m else src
    decl_part, _, rest = re.split(r"\bBEGIN\b", body, maxsplit=1, flags=re.I)[0], None, re.split(r"\bBEGIN\b", body, maxsplit=1, flags=re.I)[-1]
    decls = []
    for d in [x.strip() for x in decl_part.split(";") if x.strip()]:
        dm = re.match(r"(\w+)\s+([\w()]+)(\s*:=\s*(.+))?", d)
        if dm:
            t = {"NUMBER": "NUMBER"}.get(dm.group(2).upper().split("(")[0], "VARCHAR")
            decls.append(f"  {dm.group(1)} {t}{' DEFAULT ' + dm.group(4) if dm.group(4) else ''};")
    rest = re.sub(r"END\s*;?\s*$", "", rest.strip(), flags=re.I)
    rules = [(r"\bSYSDATE\b", "CURRENT_TIMESTAMP()"), (r"\bTRUNC\(([^()]+)\)", r"DATE_TRUNC('DAY', \1)"),
             (r"SQL%ROWCOUNT", "SQLROWCOUNT"), (r"DBMS_OUTPUT\.PUT_LINE\((.*?)\);", r"-- log: \1  (use SYSTEM$LOG or a log table)"),
             (r"^\s*COMMIT\s*;", "  -- COMMIT: Snowflake Scripting autocommits each DML unless wrapped in BEGIN TRANSACTION"),
             (r"^\s*ROLLBACK\s*;", "    -- ROLLBACK only applies inside an explicit transaction")]
    for pat, rep in rules:
        rest = re.sub(pat, rep, rest, flags=re.I | re.M)
    rest = re.sub(r"\b(\w+)\.(\w+)\b", lambda mm: f"{p.s('target_schema')}.{mm.group(2)}" if mm.group(1).upper().endswith("_DW") else mm.group(0), rest)
    if re.search(r"\bWHEN\s+OTHERS\b", rest, re.I):
        rest = re.sub(r"RAISE\s*;", "RAISE;  -- re-raise keeps the error for the caller and task history", rest, flags=re.I)
    for kw, msg in [("BULK COLLECT", "BULK COLLECT/FORALL → rewrite set-based"), ("CURSOR", "Explicit cursor → FOR r IN c DO ... END FOR or set-based SQL"),
                    ("PRAGMA", "PRAGMA (autonomous transaction) has no direct equivalent"), ("UTL_", "UTL_* packages need a replacement (external functions, Python UDF)"),
                    ("DBMS_", "DBMS_* package call needs review")]:
        if kw in re.sub(r"DBMS_OUTPUT", "", src.upper()):
            todo.append(msg)
    vars_ = re.findall(r"^\s*(\w+)\s+\w+", decl_part, re.M)
    for v in vars_:
        rest = re.sub(rf"(?<![:\w]){v}(?=\s*:=)", v, rest)
    # bind variables inside SQL statements need a colon prefix in Snowflake Scripting
    for a in [x.split()[0] for x in args]:
        rest = re.sub(rf"(?<![:\w])({a})\b", r":\1", rest, flags=re.I)
    if re.search(r"\bEXCEPTION\b", rest, re.I):
        rest = re.sub(r"\bEXCEPTION\b", "  RETURN 'OK';\nEXCEPTION", rest, count=1, flags=re.I)
        ret = ""
    else:
        ret = "  RETURN 'OK';\n"
    proc = f"""{header(sk, f'procedure {name}')}CREATE OR REPLACE PROCEDURE {p.s('target_schema')}.{name}({', '.join(args)})
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
DECLARE
{chr(10).join(decls)}
BEGIN
{rest.rstrip()}
{ret}END;
$$;
"""
    todo.append("Arguments are referenced as :name inside SQL statements; check each substitution.")
    return {"files": {f"{name.lower()}.sql": proc, "todo.md": "# Manual review\n\n" + "\n".join(f"- [ ] {t}" for t in todo) + "\n"},
            "summary": f"{name} converted with {len(todo)} review items.", "notes": todo}


@skill(name="convert-etl", stage="migration", agent="Pipeline Converter", title="Convert ETL mappings",
       description="Turn an ODI-style mapping spec into a dbt incremental model with sources and tests, plus a Snowflake-native dynamic table alternative.",
       snowflake=["dbt-snowflake (incremental, merge)", "Dynamic tables (TARGET_LAG)", "Snowflake-native workflows"],
       fields=[Field("model", "Target model name", "text", "fact_shipment_leg"),
               Field("source", "Source (schema.table alias)", "text", "otm_bronze.shipment_stop s"),
               Field("joins", "Joins (one per line)", "lines", "LEFT JOIN otm_bronze.carrier c ON c.carrier_gid = s.servprov_gid"),
               Field("columns", "Columns (target = expression)", "lines",
                     "shipment_leg_id = s.shipment_gid || '-' || s.stop_num\ncarrier_key = c.carrier_key\nplanned_arrival = s.planned_arrival\nactual_arrival = s.actual_arrival\ndelay_hours = DATEDIFF(minute, s.planned_arrival, s.actual_arrival) / 60\nupdated_at = s.update_date"),
               Field("filter", "Filter", "text", "s.domain_name = 'FLYHIGH'"),
               Field("unique_key", "Unique key", "text", "shipment_leg_id"),
               Field("watermark", "Incremental watermark column", "text", "updated_at"),
               Field("target_lag", "Dynamic table target lag", "text", "30 minutes")],
       steps=["Describe the mapping (from the ODI repository or the converter).", "Commit the dbt model and run dbt build in DEV.", "Pick dbt or the dynamic table per pipeline; do not run both in production."],
       gate="Pipeline converter output reviewed; parity proven by /gen-etl-tests")
def convert_etl(p, sk):
    cols = [l.split("=", 1) for l in p.lines("columns") if "=" in l]
    src_tbl, alias = (p.s("source").split() + ["s"])[:2]
    schema, table = src_tbl.split(".") if "." in src_tbl else ("raw", src_tbl)
    select = ",\n    ".join(f"{e.strip()} AS {c.strip()}" for c, e in cols)
    joins = "\n".join(p.lines("joins"))
    joins_dbt = re.sub(r"JOIN\s+(\w+)\.(\w+)", lambda m: f"JOIN {{{{ source('{m.group(1)}', '{m.group(2)}') }}}}", joins)
    wm = p.s("watermark")
    wm_expr = next((e.strip() for c, e in cols if c.strip() == wm), wm)
    model = f"""{{{{ config(materialized='incremental', unique_key='{p.s('unique_key')}', incremental_strategy='merge', on_schema_change='append_new_columns') }}}}

SELECT
    {select}
FROM {{{{ source('{schema}', '{table}') }}}} {alias}
{joins_dbt}
WHERE {p.s('filter') or '1=1'}
{{% if is_incremental() %}}
  AND {wm_expr} > (SELECT COALESCE(MAX({wm}), '1900-01-01') FROM {{{{ this }}}})
{{% endif %}}
"""
    schema_yml = {"version": 2, "models": [{"name": p.s("model"), "columns": [
        {"name": p.s("unique_key"), "tests": ["unique", "not_null"]}, *[{"name": c.strip()} for c, _ in cols if c.strip() != p.s("unique_key")]]}]}
    sources = {"version": 2, "sources": [{"name": schema, "tables": [{"name": table}] + [{"name": m} for m in re.findall(r"JOIN\s+\w+\.(\w+)", joins)]}]}
    dt = f"""{header(sk, 'dynamic table alternative')}CREATE OR REPLACE DYNAMIC TABLE FLYHIGH_DEV_SILVER.TRANSPORT.{ident(p.s('model'))}
  TARGET_LAG = '{p.s('target_lag')}'
  WAREHOUSE = WH_TRANSFORM
  REFRESH_MODE = AUTO
AS
SELECT
    {select}
FROM FLYHIGH_DEV_BRONZE.{ident(schema.replace('_bronze',''))}.{ident(table)} {alias}
{joins}
WHERE {p.s('filter') or '1=1'};
"""
    return {"files": {f"models/{p.s('model')}.sql": model, f"models/{p.s('model')}.yml": to_yaml(schema_yml) + "\n",
                      "models/sources.yml": to_yaml(sources) + "\n", "dynamic_table.sql": dt},
            "summary": f"dbt model {p.s('model')} with {len(cols)} columns and a dynamic-table alternative."}


@skill(name="gen-unit-tests", stage="migration", agent="Test Generator", title="Generate unit tests",
       description="Generate dbt schema tests, plain SQL assertions and Snowflake data metric functions (DMFs) for a table's keys, nulls, accepted values and relationships.",
       snowflake=["Data metric functions (SNOWFLAKE.CORE.NULL_COUNT, DUPLICATE_COUNT, FRESHNESS)", "DATA_METRIC_SCHEDULE", "dbt tests"],
       fields=[Field("table", "Table", "text", "FLYHIGH_DEV_GOLD.WAREHOUSE.FACT_WAREHOUSE_TASK"),
               Field("pk", "Primary key columns (comma)", "text", "TASK_ID"),
               Field("not_null", "Not-null columns (one per line)", "lines", "SITE_KEY\nITEM_KEY\nTASK_TYPE_KEY\nTASK_DATE_KEY"),
               Field("accepted", "Accepted values (column | v1,v2)", "lines", "EXCEPTION_FLAG | Y,N"),
               Field("relationships", "Relationships (column | parent table.column)", "lines", "SITE_KEY | FLYHIGH_DEV_GOLD.WAREHOUSE.DIM_SITE.SITE_KEY"),
               Field("freshness_col", "Freshness timestamp column", "text", "LOAD_TS"),
               Field("schedule", "DMF schedule", "text", "TRIGGER_ON_CHANGES")],
       steps=["Generate from the target model.", "Run assertions.sql in CI after each deploy (every query must return 0 rows).", "Apply dmfs.sql to keep monitoring in production."],
       gate="QA lead reviews coverage; failures block promotion")
def gen_unit_tests(p, sk):
    t, pk = p.s("table"), [ident(c) for c in p.s("pk").split(",") if c.strip()]
    nn = [ident(c) for c in p.lines("not_null")]
    a = [header(sk, f"assertions for {t} · each query must return zero rows")]
    a.append(f"-- unique key\nSELECT {', '.join(pk)}, COUNT(*) FROM {t} GROUP BY {', '.join(pk)} HAVING COUNT(*) > 1;")
    for c in pk + nn:
        a.append(f"SELECT '{c} is null' AS failure, COUNT(*) FROM {t} WHERE {c} IS NULL HAVING COUNT(*) > 0;")
    for l in p.lines("accepted"):
        c, _, vals = l.partition("|")
        a.append(f"SELECT {ident(c)}, COUNT(*) FROM {t} WHERE {ident(c)} NOT IN ({', '.join(lit(v.strip()) for v in vals.split(','))}) GROUP BY 1;")
    for l in p.lines("relationships"):
        c, _, parent = l.partition("|")
        ptab, pcol = parent.strip().rsplit(".", 1)
        a.append(f"SELECT f.{ident(c)}, COUNT(*) FROM {t} f LEFT JOIN {ptab} d ON d.{pcol} = f.{ident(c)} WHERE d.{pcol} IS NULL AND f.{ident(c)} IS NOT NULL GROUP BY 1;")
    d = [header(sk, f"data metric functions on {t}"), f"ALTER TABLE {t} SET DATA_METRIC_SCHEDULE = {lit(p.s('schedule'))};"]
    for c in pk + nn:
        d.append(f"ALTER TABLE {t} ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.NULL_COUNT ON ({c});")
    for c in pk:
        d.append(f"ALTER TABLE {t} ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.DUPLICATE_COUNT ON ({c});")
    if p.s("freshness_col"):
        d.append(f"ALTER TABLE {t} ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.FRESHNESS ON ({ident(p.s('freshness_col'))});")
    d.append("\n-- Results\nSELECT measurement_time, metric_name, argument_names, value\nFROM SNOWFLAKE.LOCAL.DATA_QUALITY_MONITORING_RESULTS\n"
             f"WHERE table_name = {lit(t.split('.')[-1])} ORDER BY measurement_time DESC;")
    name = t.split(".")[-1].lower()
    yml = {"version": 2, "models": [{"name": name, "columns":
           [{"name": c.lower(), "tests": ["not_null"] + (["unique"] if c in pk and len(pk) == 1 else [])} for c in pk + nn]}]}
    return {"files": {"assertions.sql": "\n\n".join(a) + "\n", "dmfs.sql": "\n".join(d) + "\n", f"tests/{name}.yml": to_yaml(yml) + "\n"},
            "summary": f"{len(a) - 1} assertions and {len(d) - 2} DMFs."}


@skill(name="repoint-ingest", stage="migration", agent="Ingest Repoint agent", title="Repoint ingestion",
       description="Repoint Boomi/CDC and file feeds to Snowflake: storage integration, stage, file format, auto-ingest Snowpipe, stream and merge task into Silver, or a Kafka connector config.",
       snowflake=["Storage integration + external stage", "Snowpipe AUTO_INGEST", "Streams + tasks (MERGE)", "Snowflake Kafka connector / Snowpipe Streaming"],
       fields=[Field("feed", "Feed name", "text", "wms_tasks"),
               Field("pattern", "Pattern", "choice", "file", options=["file", "kafka"]),
               Field("s3_url", "S3 location", "text", "s3://flyhigh-landing/wms/tasks/"),
               Field("role_arn", "AWS IAM role ARN", "text", "arn:aws:iam::123456789012:role/flyhigh-snowflake-s3"),
               Field("bronze_table", "Bronze table", "text", "FLYHIGH_PRD_BRONZE.WAREHOUSE.WMS_TASKS_RAW"),
               Field("silver_table", "Silver table", "text", "FLYHIGH_PRD_SILVER.WAREHOUSE.WAREHOUSE_TASK"),
               Field("key", "Merge key", "text", "TASK_ID"),
               Field("columns", "Columns (name type)", "lines", "TASK_ID NUMBER\nSITE_ID VARCHAR\nTASK_TYPE VARCHAR\nTASK_START TIMESTAMP_NTZ\nTASK_END TIMESTAMP_NTZ\nUNITS NUMBER\nOP_TYPE VARCHAR"),
               Field("topic", "Kafka topic", "text", "wms.tasks.v1")],
       steps=["Create the storage integration once per bucket and share the IAM trust values with the cloud team.", "Apply ingest.sql in DEV; drop a sample file and watch COPY_HISTORY.", "Resume the task after review; monitor with /test-cdc."],
       gate="Platform engineer reviews; data owner confirms the feed contract")
def repoint_ingest(p, sk):
    f, b, s, key = ident(p.s("feed")), p.s("bronze_table"), p.s("silver_table"), ident(p.s("key"))
    cols = [c.split()[0].upper() for c in p.lines("columns")]
    db_sch = ".".join(b.split(".")[:2])
    if p.s("pattern") == "kafka":
        cfg = {"name": f"snowflake-sink-{p.s('feed')}", "config": {
            "connector.class": "com.snowflake.kafka.connector.SnowflakeSinkConnector", "topics": p.s("topic"),
            "snowflake.topic2table.map": f"{p.s('topic')}:{b.split('.')[-1]}", "snowflake.url.name": "[account].snowflakecomputing.com:443",
            "snowflake.user.name": "SVC_INGEST", "snowflake.private.key": "${file:/secrets/snowflake.properties:private_key}",
            "snowflake.database.name": b.split(".")[0], "snowflake.schema.name": b.split(".")[1], "snowflake.role.name": "FR_INGEST",
            "snowflake.ingestion.method": "SNOWPIPE_STREAMING", "buffer.flush.time": "10",
            "key.converter": "org.apache.kafka.connect.storage.StringConverter", "value.converter": "org.apache.kafka.connect.json.JsonConverter",
            "value.converter.schemas.enable": "false"}}
        import json
        land = json.dumps(cfg, indent=2) + "\n"
        land_name = "kafka_connector.json"
        bronze_ddl = f"-- Kafka connector creates {b} with RECORD_METADATA and RECORD_CONTENT (VARIANT) columns\n"
        sel = ", ".join(f"RECORD_CONTENT:{c.lower()}::{t.split()[1]} AS {c}" for c, t in zip(cols, p.lines("columns")))
    else:
        land_name = "ingest.sql"
        land = None
        bronze_ddl = f"CREATE TABLE IF NOT EXISTS {b} ({', '.join(p.lines('columns'))}, _FILE VARCHAR, _LOADED_AT TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP());\n"
        sel = ", ".join(cols)
    sql = f"""{header(sk, f'ingestion for {f}')}USE ROLE SYSADMIN;
"""
    if p.s("pattern") == "file":
        sql += f"""CREATE STORAGE INTEGRATION IF NOT EXISTS SI_{f}
  TYPE = EXTERNAL_STAGE STORAGE_PROVIDER = 'S3' ENABLED = TRUE
  STORAGE_AWS_ROLE_ARN = {lit(p.s('role_arn'))} STORAGE_ALLOWED_LOCATIONS = ({lit(p.s('s3_url'))});
DESC INTEGRATION SI_{f};   -- give STORAGE_AWS_IAM_USER_ARN and STORAGE_AWS_EXTERNAL_ID to the cloud team

CREATE FILE FORMAT IF NOT EXISTS {db_sch}.FF_{f}_CSV TYPE = CSV SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '"' NULL_IF = ('', 'NULL') ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE;
CREATE STAGE IF NOT EXISTS {db_sch}.STG_{f} URL = {lit(p.s('s3_url'))} STORAGE_INTEGRATION = SI_{f} FILE_FORMAT = {db_sch}.FF_{f}_CSV;

{bronze_ddl}
CREATE PIPE IF NOT EXISTS {db_sch}.PIPE_{f} AUTO_INGEST = TRUE AS
  COPY INTO {b} ({', '.join(cols)}, _FILE)
  FROM (SELECT {', '.join(f'${i+1}' for i in range(len(cols)))}, METADATA$FILENAME FROM @{db_sch}.STG_{f})
  ON_ERROR = 'CONTINUE';
SHOW PIPES LIKE 'PIPE_{f}' IN SCHEMA {db_sch};   -- notification_channel → S3 event notification (SQS)
"""
    else:
        sql += f"-- Bronze table is created by the Kafka connector (see kafka_connector.json)\n"
    upd = ", ".join(f"t.{c} = s.{c}" for c in cols if c != key)
    sql += f"""
CREATE STREAM IF NOT EXISTS {db_sch}.STR_{f} ON TABLE {b} APPEND_ONLY = TRUE;

CREATE TASK IF NOT EXISTS {db_sch}.TSK_MERGE_{f}
  WAREHOUSE = WH_INGEST SCHEDULE = '5 MINUTE'
  WHEN SYSTEM$STREAM_HAS_DATA('{db_sch}.STR_{f}')
AS
MERGE INTO {s} t
USING (
  SELECT {sel} FROM {db_sch}.STR_{f}
  QUALIFY ROW_NUMBER() OVER (PARTITION BY {key} ORDER BY {'_LOADED_AT' if p.s('pattern') == 'file' else 'RECORD_METADATA:offset'} DESC) = 1
) s ON t.{key} = s.{key}
WHEN MATCHED {"AND s.OP_TYPE = 'D' THEN DELETE WHEN MATCHED " if 'OP_TYPE' in cols else ''}THEN UPDATE SET {upd}
WHEN NOT MATCHED THEN INSERT ({', '.join(cols)}) VALUES ({', '.join('s.' + c for c in cols)});
-- ALTER TASK {db_sch}.TSK_MERGE_{f} RESUME;   -- after review
"""
    files = {"ingest.sql": sql}
    if land:
        files[land_name] = land
    return {"files": files, "summary": f"{p.s('pattern')} ingestion for {p.s('feed')} into {s}."}


@skill(name="repoint-bi", stage="migration", agent="BI Repoint agent", title="Repoint BI to semantic views",
       description="Publish certified KPIs as a Snowflake semantic view (tables, relationships, facts, dimensions, metrics) for Tableau live connections and Cortex Analyst.",
       snowflake=["CREATE SEMANTIC VIEW", "SEMANTIC_VIEW() queries", "Cortex Analyst", "Tableau live connection"],
       fields=[Field("name", "Semantic view", "text", "FLYHIGH_PRD_GOLD.WAREHOUSE.SV_SITE_OPS"),
               Field("tables", "Tables (alias | fq name | primary key)", "lines",
                     "task | FLYHIGH_PRD_GOLD.WAREHOUSE.FACT_WAREHOUSE_TASK | TASK_ID\nsite | FLYHIGH_PRD_GOLD.WAREHOUSE.DIM_SITE | SITE_KEY\ndt | FLYHIGH_PRD_GOLD.WAREHOUSE.DIM_DATE | DATE_KEY"),
               Field("relationships", "Relationships (from_alias(col) -> to_alias)", "lines", "task(SITE_KEY) -> site\ntask(TASK_DATE_KEY) -> dt"),
               Field("facts", "Facts (alias.name = expression)", "lines", "task.units = UNITS_HANDLED\ntask.direct_hours = DURATION_MIN / 60\ntask.error_qty = SHORT_ERROR_QTY\ntask.pick_lines = LINES_HANDLED"),
               Field("dimensions", "Dimensions (alias.name = expression)", "lines", "site.site_name = SITE_NAME\nsite.region = REGION\ndt.fiscal_week = FISCAL_WEEK\ndt.calendar_date = CALENDAR_DATE"),
               Field("metrics", "Metrics (alias.name = expression · use KPI library formulas)", "lines",
                     "task.uph = SUM(task.units) / NULLIF(SUM(task.direct_hours), 0)\ntask.pick_accuracy = 1 - SUM(task.error_qty) / NULLIF(SUM(task.pick_lines), 0)")],
       steps=["Take metric definitions from the certified KPI library.", "Apply the semantic view; query it with SEMANTIC_VIEW() to check numbers.", "Point Tableau workbooks at it with a live connection; validate with /compare-reports."],
       gate="BI lead and data owner certify each metric before publishing")
def repoint_bi(p, sk):
    def kv(l):
        a, _, b = l.partition("=")
        return a.strip(), b.strip()
    tables = [[x.strip() for x in l.split("|")] for l in p.lines("tables")]
    rels = []
    for i, l in enumerate(p.lines("relationships")):
        m = re.match(r"(\w+)\((\w+)\)\s*->\s*(\w+)", l)
        if m:
            rels.append(f"    {m.group(1)}_to_{m.group(3)} AS {m.group(1)} ({m.group(2)}) REFERENCES {m.group(3)}")
    facts = [f"    {a} AS {b}" for a, b in map(kv, p.lines("facts"))]
    dims = [f"    {a} AS {b}" for a, b in map(kv, p.lines("dimensions"))]
    mets = [f"    {a} AS {b}" for a, b in map(kv, p.lines("metrics"))]
    sql = f"""{header(sk, 'semantic view')}CREATE OR REPLACE SEMANTIC VIEW {p.s('name')}
  TABLES (
{(','+chr(10)).join(f'    {t[0]} AS {t[1]} PRIMARY KEY ({t[2]})' for t in tables)}
  )
  RELATIONSHIPS (
{(','+chr(10)).join(rels)}
  )
  FACTS (
{(','+chr(10)).join(facts)}
  )
  DIMENSIONS (
{(','+chr(10)).join(dims)}
  )
  METRICS (
{(','+chr(10)).join(mets)}
  )
  COMMENT = 'Certified metrics · generated by /repoint-bi';

-- Smoke test
SELECT * FROM SEMANTIC_VIEW(
  {p.s('name')}
  DIMENSIONS {', '.join(kv(l)[0] for l in p.lines('dimensions')[:2])}
  METRICS {', '.join(kv(l)[0] for l in p.lines('metrics'))}
) LIMIT 50;
"""
    md = ["# Tableau repoint", "", f"- Connection: Snowflake, live, OAuth, warehouse WH_BI, role per persona", f"- Data source: `{p.s('name')}` (semantic view)",
          "- Keep layouts like-for-like for the first wave; uplift after validation", "- Publish with the Tableau REST API (sites, folders, permissions)"]
    return {"files": {"semantic_view.sql": sql, "tableau_repoint.md": "\n".join(md) + "\n"},
            "summary": f"Semantic view with {len(mets)} metrics over {len(tables)} tables."}


@skill(name="load-initial", stage="migration", agent="Migration Runner", title="Initial history load",
       description="Load historical extracts (landed in S3 by DMS or export) with COPY INTO, validate first, and record row counts in a load audit table.",
       snowflake=["COPY INTO with VALIDATION_MODE", "Parquet / CSV file formats", "LOAD_HISTORY / COPY_HISTORY", "Zero-copy clone for non-prod"],
       fields=[Field("stage", "Stage", "text", "@FLYHIGH_PRD_BRONZE.ADMIN.STG_HISTORY"),
               Field("tables", "Tables (target | stage path)", "lines", "FLYHIGH_PRD_BRONZE.WAREHOUSE.FACT_WAREHOUSE_TASK | wms/fact_warehouse_task/\nFLYHIGH_PRD_BRONZE.TRANSPORT.FACT_SHIPMENT_LEG | otm/fact_shipment_leg/"),
               Field("format", "File format", "choice", "parquet", options=["parquet", "csv"]),
               Field("clone_to", "Clone to non-prod database (optional)", "text", "FLYHIGH_STG_BRONZE")],
       steps=["Run the VALIDATION_MODE block first and fix errors.", "Run the loads, then the audit insert.", "Clone to STG for testing instead of reloading."],
       gate="Migration lead confirms counts against the source before reconciliation")
def load_initial(p, sk):
    fmt = p.s("format")
    ff = "TYPE = PARQUET" if fmt == "parquet" else "TYPE = CSV SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '\"'"
    sql = [header(sk, "initial history load"), "CREATE SCHEMA IF NOT EXISTS FLYHIGH_PRD_BRONZE.ADMIN;",
           "CREATE TABLE IF NOT EXISTS FLYHIGH_PRD_BRONZE.ADMIN.LOAD_AUDIT (TABLE_NAME VARCHAR, ROWS_LOADED NUMBER, ERRORS NUMBER, LOADED_AT TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP());"]
    for l in p.lines("tables"):
        t, _, path = [x.strip() for x in l.partition("|")]
        opts = "MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE" if fmt == "parquet" else ""
        sql.append(f"""
-- {t}
COPY INTO {t} FROM {p.s('stage')}/{path} FILE_FORMAT = ({ff}) {opts} VALIDATION_MODE = RETURN_ERRORS;   -- 1. validate
COPY INTO {t} FROM {p.s('stage')}/{path} FILE_FORMAT = ({ff}) {opts} ON_ERROR = ABORT_STATEMENT;      -- 2. load
INSERT INTO FLYHIGH_PRD_BRONZE.ADMIN.LOAD_AUDIT (TABLE_NAME, ROWS_LOADED, ERRORS)
  SELECT {lit(t)}, SUM(row_count), SUM(error_count)
  FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(TABLE_NAME => {lit(t)}, START_TIME => DATEADD(hour, -12, CURRENT_TIMESTAMP())));""")
    if p.s("clone_to"):
        sql.append(f"\n-- Non-prod copy without duplicating storage\nCREATE OR REPLACE DATABASE {ident(p.s('clone_to'))} CLONE FLYHIGH_PRD_BRONZE;")
    return {"files": {"load_initial.sql": "\n".join(sql) + "\n"}, "summary": f"{len(p.lines('tables'))} tables to load."}


@skill(name="reconcile", stage="migration", agent="Migration Runner", title="Reconcile source and target",
       description="Prove parity between Oracle and Snowflake: counts, measure sums and per-key hashes, with paired queries for both sides and a Snowflake results table.",
       snowflake=["HASH_AGG", "MINUS set comparison", "Results table for evidence"],
       fields=[Field("pairs", "Pairs (source oracle table | target snowflake table | key | measures comma)", "lines",
                     "WMS_DW.FACT_WAREHOUSE_TASK | FLYHIGH_PRD_SILVER.WAREHOUSE.FACT_WAREHOUSE_TASK | TASK_ID | UNITS,DURATION_MIN\nOTM_DW.FACT_SHIPMENT_LEG | FLYHIGH_PRD_SILVER.TRANSPORT.FACT_SHIPMENT_LEG | SHIPMENT_LEG_ID | FREIGHT_COST,LOADED_MILES"),
               Field("wave", "Wave", "text", "1"),
               Field("tolerance", "Measure tolerance (absolute)", "number", "0.01")],
       steps=["Run oracle_side.sql on the legacy database and load its output into RECON_SOURCE (CSV via stage).", "Run snowflake_side.sql, then compare.sql.", "Attach the RECON_RESULT rows as evidence for the wave sign-off."],
       gate="QA lead signs every variance as fixed or explained before cut-over")
def reconcile(p, sk):
    ora, sf, cmp = ["-- Oracle side: export to CSV and load into FLYHIGH_PRD_BRONZE.ADMIN.RECON_SOURCE"], [header(sk, f"reconciliation · wave {p.s('wave')}")], []
    sf.append("CREATE TABLE IF NOT EXISTS FLYHIGH_PRD_BRONZE.ADMIN.RECON_SOURCE (WAVE VARCHAR, OBJECT_NAME VARCHAR, METRIC VARCHAR, VALUE NUMBER(38,4));")
    sf.append("CREATE TABLE IF NOT EXISTS FLYHIGH_PRD_BRONZE.ADMIN.RECON_TARGET LIKE FLYHIGH_PRD_BRONZE.ADMIN.RECON_SOURCE;")
    sf.append("CREATE TABLE IF NOT EXISTS FLYHIGH_PRD_BRONZE.ADMIN.RECON_RESULT (WAVE VARCHAR, OBJECT_NAME VARCHAR, METRIC VARCHAR, SOURCE_VALUE NUMBER(38,4), TARGET_VALUE NUMBER(38,4), DIFF NUMBER(38,4), STATUS VARCHAR, RUN_AT TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP());")
    for l in p.lines("pairs"):
        s, t, key, meas = [x.strip() for x in l.split("|")]
        ms = [m.strip() for m in meas.split(",") if m.strip()]
        name = t.split(".")[-1]
        sums_o = ", ".join(f"'{m}' AS m{i}, SUM({m})" for i, m in enumerate(ms))
        ora.append(f"SELECT '{p.s('wave')}', '{name}', 'ROW_COUNT', COUNT(*) FROM {s}\n" +
                   "".join(f"UNION ALL SELECT '{p.s('wave')}', '{name}', 'SUM_{m}', SUM({m}) FROM {s}\n" for m in ms) + ";")
        sf.append(f"INSERT INTO FLYHIGH_PRD_BRONZE.ADMIN.RECON_TARGET\nSELECT '{p.s('wave')}', '{name}', 'ROW_COUNT', COUNT(*) FROM {t}\n" +
                  "".join(f"UNION ALL SELECT '{p.s('wave')}', '{name}', 'SUM_{m}', SUM({m}) FROM {t}\n" for m in ms) + ";")
        sf.append(f"-- Row-level fingerprint for drill-down (compare with a key sample exported from Oracle)\nSELECT HASH_AGG({key}, {', '.join(ms)}) AS fingerprint FROM {t};")
    cmp.append(f"""{header(sk, 'compare and record')}INSERT INTO FLYHIGH_PRD_BRONZE.ADMIN.RECON_RESULT (WAVE, OBJECT_NAME, METRIC, SOURCE_VALUE, TARGET_VALUE, DIFF, STATUS)
SELECT COALESCE(s.wave, t.wave), COALESCE(s.object_name, t.object_name), COALESCE(s.metric, t.metric), s.value, t.value,
       t.value - s.value,
       CASE WHEN s.value IS NULL OR t.value IS NULL THEN 'MISSING'
            WHEN ABS(t.value - s.value) <= {p.n('tolerance', 0.01)} THEN 'MATCH' ELSE 'VARIANCE' END
FROM FLYHIGH_PRD_BRONZE.ADMIN.RECON_SOURCE s
FULL OUTER JOIN FLYHIGH_PRD_BRONZE.ADMIN.RECON_TARGET t
  ON s.wave = t.wave AND s.object_name = t.object_name AND s.metric = t.metric
WHERE COALESCE(s.wave, t.wave) = '{p.s('wave')}';

SELECT object_name, metric, source_value, target_value, diff, status
FROM FLYHIGH_PRD_BRONZE.ADMIN.RECON_RESULT WHERE wave = '{p.s('wave')}' AND status <> 'MATCH' ORDER BY object_name, metric;
""")
    return {"files": {"oracle_side.sql": "\n\n".join(ora) + "\n", "snowflake_side.sql": "\n\n".join(sf) + "\n", "compare.sql": "\n".join(cmp)},
            "summary": f"Reconciliation for {len(p.lines('pairs'))} tables in wave {p.s('wave')}."}


@skill(name="parallel-run", stage="migration", agent="Cutover Validator", title="Parallel run",
       description="Schedule daily parity checks during the parallel run with a task, an alert on variances and exit criteria for cut-over.",
       snowflake=["Tasks with CRON schedules", "Alerts + SYSTEM$SEND_EMAIL", "Notification integrations"],
       fields=[Field("days", "Parallel-run length (days)", "number", "90"),
               Field("cron", "Daily check time (CRON, UTC)", "text", "0 7 * * *"),
               Field("email", "Alert recipient", "text", "cutover-team@abcretail.example"),
               Field("integration", "Email notification integration", "text", "NI_EMAIL"),
               Field("exit", "Exit criteria (one per line)", "lines", "Zero unexplained variances for 10 consecutive business days\nAll critical reports signed off by business owners\nRunbook rehearsed twice")],
       steps=["Load the Oracle-side numbers daily (from /reconcile).", "Resume the task and alert after review.", "Track exit criteria in the cut-over checklist."],
       gate="Steering committee confirms exit criteria before cut-over")
def parallel_run(p, sk):
    ni = ident(p.s("integration"))
    sql = f"""{header(sk, 'parallel run checks')}CREATE NOTIFICATION INTEGRATION IF NOT EXISTS {ni} TYPE = EMAIL ENABLED = TRUE ALLOWED_RECIPIENTS = ({lit(p.s('email'))});

CREATE OR REPLACE TASK FLYHIGH_PRD_BRONZE.ADMIN.TSK_PARALLEL_RUN
  WAREHOUSE = WH_ADMIN SCHEDULE = 'USING CRON {p.s('cron')} UTC'
AS
  EXECUTE IMMEDIATE FROM @FLYHIGH_PRD_BRONZE.ADMIN.STG_SCRIPTS/compare.sql;   -- compare.sql from /reconcile

CREATE OR REPLACE ALERT FLYHIGH_PRD_BRONZE.ADMIN.ALR_PARALLEL_RUN_VARIANCE
  WAREHOUSE = WH_ADMIN SCHEDULE = '60 MINUTE'
  IF (EXISTS (SELECT 1 FROM FLYHIGH_PRD_BRONZE.ADMIN.RECON_RESULT
              WHERE status <> 'MATCH' AND run_at > DATEADD(hour, -1, CURRENT_TIMESTAMP())))
  THEN CALL SYSTEM$SEND_EMAIL({lit(ni)}, {lit(p.s('email'))}, 'FlyHigh parallel run: variance detected',
       'New variances in RECON_RESULT. Review before the daily stand-up.');
-- ALTER TASK FLYHIGH_PRD_BRONZE.ADMIN.TSK_PARALLEL_RUN RESUME;
-- ALTER ALERT FLYHIGH_PRD_BRONZE.ADMIN.ALR_PARALLEL_RUN_VARIANCE RESUME;

-- Daily trend for the exit criteria
SELECT DATE(run_at) AS day, COUNT_IF(status = 'MATCH') AS matched, COUNT_IF(status <> 'MATCH') AS open_variances
FROM FLYHIGH_PRD_BRONZE.ADMIN.RECON_RESULT GROUP BY 1 ORDER BY 1 DESC LIMIT {int(p.n('days', 90))};
"""
    md = ["# Parallel run exit criteria", "", *[f"- [ ] {x}" for x in p.lines("exit")]]
    return {"files": {"parallel_run.sql": sql, "exit_criteria.md": "\n".join(md) + "\n"}, "summary": f"{int(p.n('days',90))}-day parallel run with daily checks."}
