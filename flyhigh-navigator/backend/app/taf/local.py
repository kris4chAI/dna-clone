"""TAF on Snowflake and on the built-in simulator.

Each assertion compiles to one Snowflake SQL query that counts violations, with the run's filter
mode applied to the case's date column (or a change-tracking CHANGES clause for date_source=CDF).
On the Snowflake engine the query runs in the DEV account configured in .env; on the simulator the
same SQL is recorded and the outcome is deterministic, so demos and tests are repeatable.

Results use TAF's check statuses (Pass, Fail, Warn, Error, Skipped, Manual, Info, Not_Run, Blocked)
and runs close with TAF's rules: findings make a run Partial, zero executed checks make it Error.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from . import logic as L

COLUMN_ASSERTIONS = ("not_null", "unique", "accepted_values", "range", "regex", "max_age_hours")
TEMPLATES = ("row_count_match", "sum_match", "referential_integrity", "freshness_sla")


def h01(*parts) -> float:
    return int(hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def _lit(v) -> str:
    return "'" + str(v).replace("'", "''") + "'"


def scope_clause(case: Dict[str, Any], req: L.ExecuteRequest) -> Tuple[str, str, Optional[str]]:
    """(where_sql, filter_applied, filter_skipped_reason) for one case."""
    col, tbl = case.get("date_column"), case.get("target_table")
    conds, applied, skipped = [], [], []
    mode = req.filter_mode
    if mode != "FULL" and req.date_source != "CDF":
        if not col:
            skipped.append(f"{mode} requested but {tbl} has no date column")
        elif mode == "LATEST_LOAD":
            conds.append(f"{col} = (SELECT MAX({col}) FROM {tbl})"); applied.append("LATEST_LOAD")
        elif mode == "SINGLE_DATE":
            conds.append(f"{col} = {_lit(req.filter_start_date)}::DATE"); applied.append(f"SINGLE_DATE {req.filter_start_date}")
        elif mode in ("DATE_RANGE", "CDF_RANGE"):
            conds.append(f"{col} BETWEEN {_lit(req.filter_start_date)}::DATE AND {_lit(req.filter_end_date)}::DATE")
            applied.append(f"{mode} {req.filter_start_date}..{req.filter_end_date}")
        elif mode == "INCREMENTAL":
            n = int(req.lookback_days or 1)
            conds.append(f"{col} >= DATEADD(day, -{n}, CURRENT_DATE())"); applied.append(f"INCREMENTAL {n}d")
    if req.filter_tenant_code:
        if case.get("tenant_column"):
            conds.append(f"{case['tenant_column']} = {_lit(req.filter_tenant_code)}"); applied.append(f"tenant {req.filter_tenant_code}")
        else:
            skipped.append(f"tenant filter requested but {tbl} has no tenant column")
    where = " AND ".join(conds)
    return where, (", ".join(applied) or "FULL"), ("; ".join(skipped) or None)


def source_of(case: Dict[str, Any], req: L.ExecuteRequest) -> str:
    """Table reference, or the change-tracking form when the date source is CDF (Snowflake CHANGES)."""
    tbl = case["target_table"]
    if req.date_source == "CDF" and req.filter_mode in ("DATE_RANGE", "CDF_RANGE", "SINGLE_DATE"):
        end = req.filter_end_date or req.filter_start_date
        return (f"{tbl} CHANGES(INFORMATION => DEFAULT) AT(TIMESTAMP => {_lit(req.filter_start_date)}::TIMESTAMP_LTZ) "
                f"END(TIMESTAMP => DATEADD(day, 1, {_lit(end)}::TIMESTAMP_LTZ))")
    return tbl


def compile_case(case: Dict[str, Any], req: L.ExecuteRequest) -> Tuple[Optional[str], str, Optional[str]]:
    """Snowflake SQL returning the violating rows (wrap in COUNT for the check)."""
    t = case["test_type"]
    if t == "MANUAL":
        return None, "n/a", None
    where, applied, skipped = scope_clause(case, req)
    w = f" AND ({where})" if where else ""
    src = source_of(case, req)
    if req.date_source == "CDF" and src != case.get("target_table"):
        applied = f"CHANGES {req.filter_start_date}..{req.filter_end_date or req.filter_start_date}"
        w = ""
    p = case.get("assertion_params") or {}
    col = case.get("target_column")
    if t == "COLUMN":
        a = case.get("assertion_name")
        if a == "not_null":
            sql = f"SELECT * FROM {src} WHERE {col} IS NULL{w}"
        elif a == "unique":
            sql = f"SELECT {col}, COUNT(*) AS n FROM {src} WHERE TRUE{w} GROUP BY {col} HAVING COUNT(*) > 1"
        elif a == "accepted_values":
            vals = ", ".join(_lit(v) for v in p.get("values", []))
            sql = f"SELECT * FROM {src} WHERE {col} NOT IN ({vals}){w}"
        elif a == "range":
            sql = f"SELECT * FROM {src} WHERE ({col} < {p.get('min', 0)} OR {col} > {p.get('max', 0)}){w}"
        elif a == "regex":
            sql = f"SELECT * FROM {src} WHERE NOT REGEXP_LIKE({col}, {_lit(p.get('pattern', '.*'))}){w}"
        elif a == "max_age_hours":
            sql = f"SELECT MAX({col}) AS latest FROM {src} HAVING MAX({col}) < DATEADD(hour, -{p.get('hours', 24)}, CURRENT_TIMESTAMP())"
        else:
            raise L.ValidationError(f"unknown column assertion {a!r}")
    elif t == "TEMPLATE":
        tp, tn = case.get("template_params") or {}, case.get("template_name")
        if tn == "row_count_match":
            sql = (f"SELECT s.n AS source_rows, t.n AS target_rows FROM (SELECT COUNT(*) AS n FROM {tp['source_table']}) s, "
                   f"(SELECT COUNT(*) AS n FROM {src} WHERE TRUE{w}) t WHERE ABS(s.n - t.n) > s.n * {tp.get('tolerance_pct', 0)} / 100")
        elif tn == "sum_match":
            m = tp["measure"]
            sql = (f"SELECT s.v AS source_sum, t.v AS target_sum FROM (SELECT SUM({m}) AS v FROM {tp['source_table']}) s, "
                   f"(SELECT SUM({m}) AS v FROM {src} WHERE TRUE{w}) t WHERE ABS(s.v - t.v) > ABS(s.v) * {tp.get('tolerance_pct', 0)} / 100")
        elif tn == "referential_integrity":
            sql = (f"SELECT c.* FROM {src} c LEFT JOIN {tp['parent_table']} p ON c.{col} = p.{tp['parent_column']} "
                   f"WHERE p.{tp['parent_column']} IS NULL{w}")
        elif tn == "freshness_sla":
            sql = (f"SELECT MAX({case.get('date_column') or col}) AS last_load FROM {case['target_table']} "
                   f"HAVING MAX({case.get('date_column') or col}) < DATEADD(minute, -{tp.get('sla_minutes', 60)}, CURRENT_TIMESTAMP())")
        else:
            raise L.ValidationError(f"unknown template {tn!r}")
    elif t == "SQL":
        expr = case.get("sql_expression") or ""
        if "{filter}" in expr:
            sql = expr.replace("{filter}", where or "TRUE")
        else:
            sql = expr
            if where:
                skipped = "; ".join(x for x in [skipped, "unscoped SQL case: add {filter} to scope it"] if x)
                applied = "FULL"
    else:
        raise L.ValidationError(f"unknown test_type {t!r}")
    return sql, applied, skipped


# ---------------------------------------------------------------------------
# Snowflake execution
# ---------------------------------------------------------------------------
def snowflake_ready() -> Tuple[bool, str]:
    if not os.getenv("SNOWFLAKE_ACCOUNT"):
        return False, "Snowflake is not configured (SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, key or password, ROLE, WAREHOUSE in .env)"
    if os.getenv("SNOWFLAKE_ALLOW_EXECUTE", "false").lower() != "true":
        return False, "Snowflake execution is off: set SNOWFLAKE_ALLOW_EXECUTE=true for a DEV account"
    return True, ""


def snowflake_connect():
    import snowflake.connector
    kw = {"account": os.getenv("SNOWFLAKE_ACCOUNT"), "user": os.getenv("SNOWFLAKE_USER"), "role": os.getenv("SNOWFLAKE_ROLE"),
          "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"), "database": os.getenv("SNOWFLAKE_DATABASE") or None}
    if os.getenv("SNOWFLAKE_PRIVATE_KEY_FILE"):
        kw.update(authenticator="SNOWFLAKE_JWT", private_key_file=os.getenv("SNOWFLAKE_PRIVATE_KEY_FILE"),
                  private_key_file_pwd=os.getenv("SNOWFLAKE_PRIVATE_KEY_FILE_PWD"))
    else:
        kw["password"] = os.getenv("SNOWFLAKE_PASSWORD")
    con = snowflake.connector.connect(**{k: v for k, v in kw.items() if v is not None})
    con.cursor().execute("ALTER SESSION SET QUERY_TAG = 'flyhigh-navigator-taf'")
    return con


# ---------------------------------------------------------------------------
# one check
# ---------------------------------------------------------------------------
def status_for(case: Dict[str, Any], violations: int) -> str:
    if violations == 0:
        return "Pass"
    return "Warn" if case.get("severity") == "Low" else "Fail"


def simulate(case: Dict[str, Any], seq: int) -> Tuple[str, int, Optional[str]]:
    u = h01(case["test_id"], seq, "taf")
    fragile = h01(case["test_id"], "fragile") < 0.18
    if u < 0.025:
        return "Error", 0, "SQL compilation error: object does not exist or not authorized"
    if (fragile and u < 0.55) or u < 0.06:
        v = int(1 + h01(case["test_id"], seq, "v") * 240)
        return status_for(case, v), v, None
    return "Pass", 0, None


def run_case(case: Dict[str, Any], req: L.ExecuteRequest, seq: int, con=None, sample_rows: int = 5) -> Dict[str, Any]:
    t0 = time.perf_counter()
    out = {"test_id": case["test_id"], "suite": case["suite"], "test_type": case["test_type"], "severity": case["severity"],
           "check_id": case.get("check_id") or case["test_id"], "expected_result": case.get("expected_result")}
    if not case.get("is_active", True):
        return {**out, "status": "Not_Run", "violation_count": None, "actual_result": "deactivated in the test suite",
                "executed_sql": None, "filter_applied": None, "filter_skipped_reason": None, "error_message": None, "sample_rows": [], "duration_ms": 0}
    if case["test_type"] == "MANUAL":
        return {**out, "status": "Manual", "violation_count": None, "actual_result": "manual check: record the outcome in UAT",
                "executed_sql": None, "filter_applied": "n/a", "filter_skipped_reason": None, "error_message": None, "sample_rows": [], "duration_ms": 0}
    try:
        sql, applied, skipped = compile_case(case, req)
    except Exception as e:
        return {**out, "status": "Error", "violation_count": None, "actual_result": None, "executed_sql": None, "filter_applied": None,
                "filter_skipped_reason": None, "error_message": f"compile: {e}", "sample_rows": [], "duration_ms": 0}
    count_sql = f"SELECT COUNT(*) AS violations FROM ({sql}) v"
    sample, err = [], None
    if con is not None:
        try:
            cur = con.cursor()
            cur.execute(count_sql)
            v = int(cur.fetchone()[0])
            if v and req.capture_records == "yes":
                cur.execute(f"SELECT * FROM ({sql}) v LIMIT {sample_rows}")
                cols = [d[0] for d in cur.description]
                sample = [dict(zip(cols, map(str, r))) for r in cur.fetchall()]
            st = status_for(case, v)
        except Exception as e:
            st, v, err = "Error", None, str(e)[:500]
    else:
        st, v, err = simulate({**case, "test_id": case["check_id"] if case["suite"] == "EXTERNAL" and case.get("check_id") else case["test_id"]}, seq)
        if v:
            sample = [{"row": i + 1, (case.get("target_column") or "value"): ("NULL" if case.get("assertion_name") == "not_null" else f"sample_{i + 1}")}
                      for i in range(min(3, v))]
    return {**out, "status": st, "violation_count": v, "actual_result": None if err else (f"{v} violating rows" if v else "0 violations"),
            "executed_sql": count_sql, "filter_applied": applied, "filter_skipped_reason": skipped, "error_message": err,
            "sample_rows": sample, "duration_ms": int((time.perf_counter() - t0) * 1000) + (0 if con else int(40 + h01(case["test_id"], seq) * 900))}


def in_scope(case: Dict[str, Any], req: L.ExecuteRequest) -> bool:
    if req.test_scope == L.SCOPE_EXTERNAL:
        return case["suite"] == "EXTERNAL"
    if case["suite"] == "EXTERNAL" and (req.run_external_suite != "yes" or req.test_scope not in (L.SCOPE_ALL, L.SCOPE_CLIENT)):
        return False
    if case["test_type"] not in L.SCOPE_TYPES[req.test_scope]:
        return False
    if req.run_scope not in ("", "ALL") and case.get("requirement_group") != req.run_scope:
        return False
    if req.sheet_filter not in ("", "ALL") and (case.get("sheet_name") or "") != req.sheet_filter:
        return False
    return True


def log_line(lines: List[str], msg: str):
    lines.append(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} {msg}")
