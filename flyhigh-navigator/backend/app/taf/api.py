"""TAF data checks inside the assurance workbench: control plane, runs on three engines, results,
run logs, health scenarios, and the failure triage that feeds defects.

Routes live under /api/assurance/taf and /api/assurance/triage. Access follows the assurance screens:
reading results, scenarios and triage needs the screen that shows them; changing anything (toggle,
run, upload, scenarios, resolve, raise defect) is for the assurance lens.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile

from ..access import screen
from ..db import one, q
from . import databricks as DBX
from . import local as LOC
from . import logic as L
from . import scenarios as SC
from .catalog import taf_rows

log = logging.getLogger("taf.api")
router = APIRouter(prefix="/api/assurance")
LIMIT_RUNS, LIMIT_DETAIL, LIMIT_RESULTS = 100, 5000, 10000
MAX_UPLOAD_BYTES, MAX_EVIDENCE_CHARS = 50 * 1024 * 1024, 16000
STATUS_ORDER = ["Pass", "Fail", "Warn", "Error", "Skipped", "Manual", "Info", "Not_Run", "Blocked"]
EDIT = screen("aw_design")       # assurance lens only
EXEC = screen("aw_execution")     # assurance lens only
READ_DASH = screen("aw_overview")
READ_AN = screen("aw_analytics")


def _now():
    return datetime.now(timezone.utc)


def engines() -> List[Dict[str, Any]]:
    sf_ok, sf_why = LOC.snowflake_ready()
    cfg = DBX.config()
    return [{"name": "Simulator", "ready": True, "note": "Built-in: compiles the real Snowflake SQL, deterministic outcomes"},
            {"name": "Snowflake", "ready": sf_ok, "note": "Runs each check's SQL in the DEV account from .env" if sf_ok else sf_why},
            {"name": "Databricks", "ready": cfg.configured,
             "note": (f"Submits TAF's notebook chain in {cfg.catalog}.{cfg.schema} ({cfg.environment})" if cfg.configured
                      else "Set DATABRICKS_HOST, DATABRICKS_TOKEN (or client id and secret) and APP_TAF_* in .env")}]


# ---------------------------------------------------------------------------
# seed
# ---------------------------------------------------------------------------
def seed_taf(x):
    """x: assurance_api.X executor (inside the seeding transaction)."""
    cols = ["test_id", "suite", "check_id", "test_type", "severity", "requirement_group", "requirement_id", "requirement_title", "sheet_name",
            "functional_category", "load_type", "target_table", "target_column", "date_column", "tenant_column", "assertion_name",
            "assertion_params", "template_name", "template_params", "sql_expression", "expected_result", "explanation", "owner",
            "source_ref", "lakehouse_type"]
    for r in taf_rows():
        vals = [json.dumps(r[c]) if c in ("assertion_params", "template_params") and r[c] is not None else r[c] for c in cols]
        x.one(f"INSERT INTO taf_case({','.join(cols)}) VALUES ({','.join(['%s'] * len(cols))}) RETURNING 1", tuple(vals))
    x.one("UPDATE taf_case SET is_active=FALSE, deactivated_by='seed', deactivated_at=now() - interval '3 days' WHERE test_id='TAF-CORE-008' RETURNING 1")
    plan = [("R20261028_0200", "Simulator", L.SCOPE_ALL, "FULL", 12, "scheduled"),
            ("G20261102_0200_TAF", "Simulator", L.SCOPE_ALL, "INCREMENTAL", 7, "pipeline"),
            ("UI20261106_101500_a1b2c3", "Simulator", L.SCOPE_ALL, "LATEST_LOAD", 3, L.TRIGGERED_BY)]
    for i, (rid, eng, scope, mode, days_ago, trig) in enumerate(plan):
        req = L.ExecuteRequest.from_dict({"engine": eng, "test_scope": scope, "filter_mode": mode})
        run_local(x, rid, req, "seed", seq=i + 1, started=_now() - timedelta(days=days_ago), triggered_by=trig)


# ---------------------------------------------------------------------------
# local engines (Simulator, Snowflake)
# ---------------------------------------------------------------------------
class _Q:
    """Runtime executor with the same interface as the seed executor."""
    def q(self, sql, p=()):
        return q(sql, p)

    def one(self, sql, p=()):
        return one(sql, p)


def run_local(x, run_id: str, req: L.ExecuteRequest, user: str, seq: Optional[int] = None, started=None, triggered_by=L.TRIGGERED_BY):
    started = started or _now()
    lines: List[str] = []
    LOC.log_line(lines, f"TAF run {run_id} on {req.engine}: scope '{req.test_scope}', filter {req.filter_mode}/{req.date_source}")
    x.one("""INSERT INTO taf_run(run_id,engine,test_scope,started_at,status,run_scope,triggered_by,upstream_pipeline_run,input_source,
             filter_mode,date_source,params,created_by) VALUES (%s,%s,%s,%s,'Running',%s,%s,%s,%s,%s,%s,%s,%s)
             ON CONFLICT (run_id) DO NOTHING RETURNING 1""",
          (run_id, req.engine, req.test_scope, started, req.run_scope or "ALL", triggered_by, None,
           req.source_file_path or "workbench suite", req.filter_mode, req.date_source, json.dumps({k: v for k, v in req.__dict__.items() if k != "warnings"}), user))
    seq = seq or (x.one("SELECT COUNT(*) AS n FROM taf_run")["n"] + 3)
    cases = [c for c in x.q("SELECT * FROM taf_case ORDER BY suite, test_id") if LOC.in_scope(c, req)]
    LOC.log_line(lines, f"{len(cases)} case(s) in scope ({sum(1 for c in cases if not c['is_active'])} deactivated load as Not_Run)")
    con, result_state = None, "SUCCESS"
    if req.engine == "Snowflake":
        try:
            con = LOC.snowflake_connect()
            LOC.log_line(lines, "connected to Snowflake")
        except Exception as e:
            LOC.log_line(lines, f"ERROR cannot connect to Snowflake: {e}")
            result_state = "FAILED"
            cases = []
    t = started
    try:
        for c in cases:
            r = LOC.run_case(c, req, seq, con=con, sample_rows=5)
            t = t + timedelta(milliseconds=r["duration_ms"] or 1)
            x.one("""INSERT INTO taf_result(run_id,test_id,suite,check_id,test_type,severity,status,violation_count,expected_result,actual_result,
                     executed_sql,sample_rows,duration_ms,executed_at,filter_applied,filter_skipped_reason,error_message)
                     VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING 1""",
                  (run_id, r["test_id"], r["suite"], r["check_id"], r["test_type"], r["severity"], r["status"], r["violation_count"],
                   r["expected_result"], r["actual_result"], r["executed_sql"], json.dumps(r["sample_rows"][:5]), r["duration_ms"], t,
                   r["filter_applied"], r["filter_skipped_reason"], r["error_message"]))
            LOC.log_line(lines, f"{r['suite']}/{r['test_id']} {r['status']}" + (f" ({r['violation_count']} violations)" if r["violation_count"] else "")
                         + (f" ERROR {r['error_message']}" if r["error_message"] else ""))
    except Exception as e:
        result_state = "FAILED"
        LOC.log_line(lines, f"ERROR run aborted: {e}")
    finally:
        if con is not None:
            con.close()
    counts = L.tally(x.q("SELECT status, COUNT(*) AS n FROM taf_result WHERE run_id=%s GROUP BY status", (run_id,)))
    status, note = L.final_manifest_status(result_state, counts)
    LOC.log_line(lines, f"closed: {status} · {note}")
    x.one("""UPDATE taf_run SET status=%s, finished_at=%s, total_tests=%s, pass_count=%s, fail_count=%s, warn_count=%s, error_count=%s,
             manual_count=%s, not_run_count=%s, notes=%s, log=%s WHERE run_id=%s RETURNING 1""",
          (status, t + timedelta(seconds=2), counts["total_tests"], counts["pass_count"], counts["fail_count"], counts["warn_count"],
           counts["error_count"], counts["manual_count"], counts["not_run_count"], note, "\n".join(lines), run_id))
    return status


# ---------------------------------------------------------------------------
# Databricks mirror and reconcile
# ---------------------------------------------------------------------------
def _mirror_and_close(run: Dict[str, Any], state: Dict[str, Any], note_extra: str = "") -> None:
    rows = []
    try:
        rows = DBX.results(run["run_id"])
    except Exception as e:
        note_extra = f"{note_extra} results not readable: {e}".strip()
    for r in rows:
        one("""INSERT INTO taf_result(run_id,test_id,suite,check_id,test_type,severity,status,violation_count,expected_result,actual_result,
               executed_sql,sample_rows,duration_ms,executed_at,filter_applied,filter_skipped_reason,error_message)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING 1""",
            (run["run_id"], r["test_id"], r["suite"], r.get("check_id"), r.get("test_type"), r.get("severity"),
             r.get("status") if r.get("status") in STATUS_ORDER else "Info", r.get("violation_count"), r.get("expected_result"), r.get("actual_result"),
             r.get("executed_sql"), json.dumps([{"preview": r.get("sample_rows_preview")}] if r.get("sample_rows_preview") else []),
             r.get("duration_ms"), r.get("executed_at"), r.get("filter_applied"), r.get("filter_skipped_reason"), r.get("error_message")))
    counts = L.tally(q("SELECT status, COUNT(*) AS n FROM taf_result WHERE run_id=%s GROUP BY status", (run["run_id"],)))
    status, note = L.final_manifest_status(state.get("result_state"), counts)
    note = f"{note}. {note_extra}".strip(". ") if note_extra else note
    one("""UPDATE taf_run SET status=%s, finished_at=now(), total_tests=%s, pass_count=%s, fail_count=%s, warn_count=%s, error_count=%s,
           manual_count=%s, not_run_count=%s, notes=%s WHERE run_id=%s AND status='Running' RETURNING 1""",
        (status, counts["total_tests"], counts["pass_count"], counts["fail_count"], counts["warn_count"], counts["error_count"],
         counts["manual_count"], counts["not_run_count"], note, run["run_id"]))
    DBX.close_manifest(run["run_id"], state.get("result_state"), counts, note)


_last_reconcile, _rec_lock = 0.0, threading.Lock()


def reconcile_running(force: bool = False) -> int:
    """Self-heal runs stranded at Running (job died, tab closed). Throttled to once per 30 s."""
    global _last_reconcile
    with _rec_lock:
        if not force and time.time() - _last_reconcile < 30:
            return 0
        _last_reconcile = time.time()
    closed = 0
    for r in q("SELECT * FROM taf_run WHERE status='Running'"):
        try:
            if r["engine"] == "Databricks" and (r["upstream_pipeline_run"] or "").isdigit() and DBX.config().configured:
                st = DBX.status(r["upstream_pipeline_run"])
                if st["terminal"]:
                    _mirror_and_close(r, st, "closed by reconcile")
                    closed += 1
            elif r["started_at"] and (_now() - r["started_at"]).total_seconds() > DBX.config().stranded_hours * 3600:
                one("UPDATE taf_run SET status='Error', finished_at=now(), notes=%s WHERE run_id=%s RETURNING 1",
                    (f"stranded: Running > {DBX.config().stranded_hours:g} h", r["run_id"]))
                closed += 1
        except Exception:
            log.exception("reconcile failed for %s", r["run_id"])
    return closed


# ---------------------------------------------------------------------------
# config, dashboard, control plane
# ---------------------------------------------------------------------------
@router.get("/taf/config")
def taf_config(p: dict = Depends(READ_DASH)):
    return {"engines": engines(), "databricks": DBX.config().public(), "scopes": list(L.TEST_SCOPE_CHAINS), "filter_modes": list(L.FILTER_MODES),
            "date_sources": list(L.DATE_SOURCES), "chains": {k: list(v) for k, v in L.TEST_SCOPE_CHAINS.items()},
            "scope_types": {k: list(v) for k, v in L.SCOPE_TYPES.items()}, "statuses": STATUS_ORDER,
            "sheets": [r["sheet_name"] for r in q("SELECT DISTINCT sheet_name FROM taf_case ORDER BY 1")],
            "groups": [r["requirement_group"] for r in q("SELECT DISTINCT requirement_group FROM taf_case ORDER BY 1")],
            "limits": {"runs": LIMIT_RUNS, "detail": LIMIT_DETAIL, "results": LIMIT_RESULTS}}


def _latest_run(suite: Optional[str] = None, x=None) -> Optional[str]:
    r = (x or _Q()).one(f"""SELECT r.run_id FROM taf_run r WHERE r.status <> 'Running'
                {"AND EXISTS (SELECT 1 FROM taf_result x WHERE x.run_id=r.run_id AND x.suite=%s)" if suite else ""}
                ORDER BY r.started_at DESC LIMIT 1""", (suite,) if suite else ())
    return r["run_id"] if r else None


@router.get("/taf/dashboard")
def taf_dashboard(p: dict = Depends(READ_DASH)):
    """Latest run per suite. Scenario and distinct-check counts are deliberately separate:
    one failing generated query fails every scenario attached to it."""
    suites = []
    for s in ("TAF", "EXTERNAL"):
        rid = _latest_run(s)
        if not rid:
            continue
        rows = q("SELECT status, check_id FROM taf_result WHERE run_id=%s AND suite=%s", (rid, s))
        checks = {}
        for r in rows:
            checks.setdefault(r["check_id"], set()).add(r["status"])
        run = one("SELECT run_id, engine, started_at, status FROM taf_run WHERE run_id=%s", (rid,))
        suites.append({"suite": s, **run, "total": len(rows), **{f"{k.lower()}_count": sum(1 for r in rows if r["status"] == k) for k in STATUS_ORDER},
                       "distinct_checks": len(checks), "failed_checks": sum(1 for v in checks.values() if v & {"Fail", "Error"})})
    runs = q("SELECT * FROM taf_run ORDER BY started_at DESC LIMIT 20")
    return {"suites": suites, "runs": runs, "running": sum(1 for r in runs if r["status"] == "Running")}


@router.get("/taf/suite")
def taf_suite(search: Optional[str] = None, category: Optional[str] = None, suite: Optional[str] = None, active_only: bool = False,
              p: dict = Depends(screen("aw_design"))):
    """The control plane: which cases are active. Not a results page, so no pass/fail strip."""
    where, args = ["TRUE"], []
    if search:
        where.append("(c.test_id ILIKE %s OR c.requirement_title ILIKE %s OR c.target_table ILIKE %s)"); args += [f"%{search}%"] * 3
    if category:
        where.append("c.functional_category = %s"); args.append(category)
    if suite in ("TAF", "EXTERNAL"):
        where.append("c.suite = %s"); args.append(suite)
    if active_only:
        where.append("c.is_active")
    rows = q(f"""SELECT c.*, t.name AS lakehouse_name, (SELECT r.status FROM taf_result r JOIN taf_run u ON u.run_id=r.run_id
                 WHERE r.test_id=c.test_id AND r.suite=c.suite ORDER BY u.started_at DESC LIMIT 1) AS last_status
                 FROM taf_case c LEFT JOIN aw_test_type t ON t.code=c.lakehouse_type WHERE {' AND '.join(where)}
                 ORDER BY c.suite, c.test_id LIMIT {LIMIT_RESULTS}""", tuple(args))
    return {"rows": rows}


@router.post("/taf/suite/{suite}/{test_id}/set-active")
def set_active(suite: str, test_id: str, payload: Dict[str, Any] = Body(...), p: dict = Depends(EDIT)):
    if "is_active" not in payload:
        raise HTTPException(400, "is_active is required")
    want = bool(payload["is_active"])
    c = one("SELECT * FROM taf_case WHERE test_id=%s AND suite=%s", (test_id, suite))
    if not c:
        raise HTTPException(404, "unknown test case")
    if c["origin"] == "databricks":
        try:
            DBX.set_active(test_id, suite, want, p["code"])
        except Exception as e:
            raise HTTPException(502, f"Databricks write-through failed, nothing changed: {e}")
    one("""UPDATE taf_case SET is_active=%s, deactivated_by=CASE WHEN %s THEN NULL ELSE %s END,
           deactivated_at=CASE WHEN %s THEN NULL ELSE now() END, updated_at=now() WHERE test_id=%s AND suite=%s RETURNING 1""",
        (want, want, p["code"], want, test_id, suite))
    got = one("SELECT is_active FROM taf_case WHERE test_id=%s AND suite=%s", (test_id, suite))
    if not got or got["is_active"] != want:  # a write that does not stick is an error, not a 200
        raise HTTPException(500, "the change did not persist (re-query disagrees)")
    return {"ok": True, "verified": True, "test_id": test_id, "suite": suite, "is_active": want}


@router.post("/taf/suite/sync")
def sync_suite(payload: Dict[str, Any] = Body(default={}), p: dict = Depends(EDIT)):
    """Add cases seen in runs (and, with Databricks, TAF's own suite) that the control plane does not know yet.
    Never re-enables something that was turned off."""
    before = one("SELECT COUNT(*) AS n FROM taf_case")["n"]
    if payload.get("engine") == "Databricks":
        try:
            for r in DBX.suite_rows():
                one("""INSERT INTO taf_case(test_id,suite,check_id,test_type,severity,requirement_group,requirement_title,sheet_name,functional_category,
                       load_type,is_active,origin) VALUES (%s,%s,%s,'SQL',%s,%s,%s,%s,%s,%s,%s,'databricks') ON CONFLICT DO NOTHING RETURNING 1""",
                    (r["test_id"], r["suite"], r["test_id"], r.get("priority_label") or "Medium", r.get("test_category"), r.get("test_scenario"),
                     r.get("sheet_name"), r.get("functional_category"), r.get("load_type"), bool(r.get("is_active", True))))
        except DBX.NotConfigured as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            raise HTTPException(502, f"reading TAF's suite on Databricks failed: {e}")
    one("""INSERT INTO taf_case(test_id,suite,check_id,test_type,severity,requirement_title,origin)
           SELECT DISTINCT ON (r.test_id, r.suite) r.test_id, r.suite, r.check_id, COALESCE(r.test_type,'SQL'), r.severity, r.test_id, 'run'
           FROM taf_result r WHERE NOT EXISTS (SELECT 1 FROM taf_case c WHERE c.test_id=r.test_id AND c.suite=r.suite)
           ON CONFLICT DO NOTHING RETURNING 1""")
    after = one("SELECT COUNT(*) AS n FROM taf_case")["n"]
    return {"ok": True, "before": before, "after": after, "inserted": after - before}


# ---------------------------------------------------------------------------
# upload, execute, status, runs, logs
# ---------------------------------------------------------------------------
def _import_external(name: str, data: bytes) -> List[Dict[str, Any]]:
    low = name.lower()
    if low.endswith((".yaml", ".yml", ".json")):
        import yaml
        doc = yaml.safe_load(data.decode("utf-8")) if not low.endswith(".json") else json.loads(data.decode("utf-8"))
        rows = doc.get("cases", doc) if isinstance(doc, dict) else doc
    elif low.endswith(".csv"):
        rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
    else:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        rows = []
        for ws in wb.worksheets:
            it = ws.iter_rows(values_only=True)
            head = [str(h or "").strip().lower() for h in next(it, [])]
            rows += [{**dict(zip(head, r)), "sheet_name": ws.title} for r in it if any(r)]
    if not isinstance(rows, list) or not rows:
        raise L.ValidationError("no cases found: expected a list of cases (test_id, test_scenario, category, priority, sql_script)")
    return rows


@router.post("/taf/upload")
async def upload(file: UploadFile = File(...), engine: str = Form("Simulator"), p: dict = Depends(EXEC)):
    data = await file.read()
    if not data:
        raise HTTPException(400, "empty file")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "file larger than 50 MB")
    name = (file.filename or "upload").replace("\\", "/").split("/")[-1]
    if engine == "Databricks":
        try:
            path = DBX.upload(name, data)
        except (L.ValidationError, DBX.NotConfigured) as e:
            raise HTTPException(400, str(e))
        except Exception as e:  # fail loudly: never fall back to local disk
            raise HTTPException(502, f"upload to the TAF volume failed, file NOT saved: {e}")
        one("INSERT INTO taf_upload(filename,path,bytes,imported,engine,created_by) VALUES (%s,%s,%s,0,'Databricks',%s) RETURNING 1",
            (name, path, len(data), p["code"]))
        return {"ok": True, "path": path, "bytes": len(data), "imported": 0}
    if not name.lower().endswith((".xlsx", ".xlsm", ".yaml", ".yml", ".json", ".csv")):
        raise HTTPException(400, "only .xlsx, .xlsm, .yaml, .yml, .json or .csv uploads are accepted")
    try:
        rows = _import_external(name, data)
    except Exception as e:
        raise HTTPException(400, f"could not read {name}: {e}")
    n = 0
    for i, r in enumerate(rows, 1):
        g = {str(k).strip().lower(): v for k, v in r.items()}
        tid = str(g.get("test_id") or f"EXT-U{i:03d}")
        pri = str(g.get("priority") or "P2").upper()
        one("""INSERT INTO taf_case(test_id,suite,check_id,test_type,severity,requirement_group,requirement_title,sheet_name,functional_category,
               load_type,target_table,sql_expression,expected_result,explanation,owner,source_ref,lakehouse_type,origin)
               VALUES (%s,'EXTERNAL',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'upload')
               ON CONFLICT (test_id, suite) DO UPDATE SET requirement_title=EXCLUDED.requirement_title, sql_expression=EXCLUDED.sql_expression,
               check_id=EXCLUDED.check_id, updated_at=now() RETURNING 1""",
            (tid, str(g.get("check_id") or tid), str(g.get("test_type") or "SQL").upper() if str(g.get("test_type") or "SQL").upper() in ("COLUMN", "TEMPLATE", "SQL", "MANUAL") else "SQL",
             "High" if pri in ("P1", "HIGH", "CRITICAL") else "Low" if pri in ("P3", "LOW") else "Medium",
             g.get("category"), g.get("test_scenario") or g.get("title") or tid, g.get("sheet_name") or g.get("file_type") or "Upload",
             g.get("category"), g.get("load_type") or g.get("source_type"), g.get("target_table"), g.get("sql_script") or g.get("sql"),
             g.get("expected") or "0 failures", g.get("test_scenario"), g.get("owner") or "Client QA", f"{name}#{tid}", g.get("lakehouse_type")))
        n += 1
    up = one("INSERT INTO taf_upload(filename,path,bytes,imported,engine,created_by) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
             (name, f"upload:{name}", len(data), n, engine, p["code"]))
    return {"ok": True, "path": f"upload:{up['id']}:{name}", "bytes": len(data), "imported": n}


@router.post("/taf/execute")
def execute(payload: Dict[str, Any] = Body(...), p: dict = Depends(EXEC)):
    try:
        req = L.ExecuteRequest.from_dict(payload)
    except L.ValidationError as e:
        raise HTTPException(400, str(e))
    run_id = L.new_ui_run_id()
    if req.engine == "Databricks":
        try:
            sub = DBX.submit(req, run_id, p["code"])
        except DBX.NotConfigured as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            raise HTTPException(502, f"job submit failed, nothing started: {e}")
        one("""INSERT INTO taf_run(run_id,engine,test_scope,status,run_scope,triggered_by,upstream_pipeline_run,input_source,filter_mode,date_source,
               params,notes,created_by) VALUES (%s,'Databricks',%s,'Running',%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING 1""",
            (run_id, req.test_scope, req.run_scope or "ALL", L.TRIGGERED_BY, sub["job_run_id"], req.source_file_path or "deployed workbook + cases/",
             req.filter_mode, req.date_source, json.dumps({k: v for k, v in req.__dict__.items() if k != "warnings"}),
             json.dumps({"log_file": sub["log_file"], "chain": sub["chain"]}), p["code"]))
        return {"ok": True, "run_id": run_id, "engine": "Databricks", "job_run_id": sub["job_run_id"], "chain": sub["chain"],
                "log_file": sub["log_file"], "warnings": req.warnings + sub["warnings"]}
    if req.engine == "Snowflake":
        ok, why = LOC.snowflake_ready()
        if not ok:
            raise HTTPException(400, why)
    # Simulator and Snowflake run in the background; the UI polls /taf/run-status every 5 s.
    one("""INSERT INTO taf_run(run_id,engine,test_scope,status,run_scope,triggered_by,input_source,filter_mode,date_source,params,created_by)
           VALUES (%s,%s,%s,'Running',%s,%s,%s,%s,%s,%s,%s) RETURNING 1""",
        (run_id, req.engine, req.test_scope, req.run_scope or "ALL", L.TRIGGERED_BY, req.source_file_path or "workbench suite",
         req.filter_mode, req.date_source, json.dumps({k: v for k, v in req.__dict__.items() if k != "warnings"}), p["code"]))

    def work():
        try:
            time.sleep(1.5 if req.engine == "Simulator" else 0)
            run_local(_Q(), run_id, req, p["code"])
        except Exception as e:
            log.exception("local run failed")
            one("UPDATE taf_run SET status='Error', finished_at=now(), notes=%s WHERE run_id=%s RETURNING 1", (f"run crashed: {e}", run_id))
    threading.Thread(target=work, daemon=True).start()
    chain = [f"{req.engine.lower()}:{t.lower()}" for t in L.SCOPE_TYPES[req.test_scope]]
    return {"ok": True, "run_id": run_id, "engine": req.engine, "job_run_id": None, "chain": chain, "warnings": req.warnings}


@router.get("/taf/run-status/{run_id}")
def run_status(run_id: str, p: dict = Depends(EXEC)):
    r = one("SELECT * FROM taf_run WHERE run_id=%s", (run_id,))
    if not r:
        raise HTTPException(404, "unknown run")
    out = {"run_id": run_id, "engine": r["engine"], "terminal": r["status"] != "Running", "manifest": r, "tasks": []}
    if r["engine"] == "Databricks" and r["status"] == "Running" and (r["upstream_pipeline_run"] or "").isdigit():
        try:
            st = DBX.status(r["upstream_pipeline_run"])
        except Exception as e:
            raise HTTPException(502, f"cannot read the Databricks job run: {e}")
        out.update(st)
        if st["terminal"]:
            _mirror_and_close(r, st)
            out["manifest"] = one("SELECT * FROM taf_run WHERE run_id=%s", (run_id,))
    else:
        done = one("SELECT COUNT(*) AS n FROM taf_result WHERE run_id=%s", (run_id,))["n"]
        out["life_cycle_state"] = "RUNNING" if r["status"] == "Running" else "TERMINATED"
        out["progress"] = done
    return out


@router.get("/taf/runs")
def runs(p: dict = Depends(EXEC)):
    healed = reconcile_running()
    return {"rows": q(f"SELECT run_id, engine, test_scope, started_at, finished_at, status, run_scope, triggered_by, upstream_pipeline_run, filter_mode, "
                      f"date_source, total_tests, pass_count, fail_count, warn_count, error_count, manual_count, not_run_count, notes, created_by "
                      f"FROM taf_run ORDER BY started_at DESC LIMIT {LIMIT_RUNS}"), "reconciled": healed}


@router.get("/taf/run-log/{run_id}")
def run_log(run_id: str, tail_kb: int = Query(512, ge=1, le=20480), p: dict = Depends(EXEC)):
    r = one("SELECT * FROM taf_run WHERE run_id=%s", (run_id,))
    if not r:
        raise HTTPException(404, "unknown run")
    if r["engine"] == "Databricks":
        try:
            return {"run_id": run_id, **DBX.read_log(run_id, r["upstream_pipeline_run"], tail_kb)}
        except Exception as e:
            return {"run_id": run_id, "source": "unavailable", "truncated": False, "content": f"(Databricks log unavailable: {e})"}
    text = r["log"] or "(no log yet)"
    limit = tail_kb * 1024
    return {"run_id": run_id, "source": "workbench", "log_file": f"taf_run_{run_id}.log", "truncated": len(text) > limit, "content": text[-limit:]}


# ---------------------------------------------------------------------------
# results and assertions
# ---------------------------------------------------------------------------
@router.get("/taf/results")
def results(run_id: Optional[str] = None, suite: Optional[str] = Query(None, pattern="^(TAF|EXTERNAL)$"),
            test_type: Optional[str] = Query(None, pattern="^(COLUMN|TEMPLATE|SQL|MANUAL)$"), p: dict = Depends(EXEC)):
    rid = run_id or _latest_run(suite)
    if not rid:
        return {"run_id": None, "rows": []}
    where, args = ["r.run_id=%s"], [rid]
    if suite:
        where.append("r.suite=%s"); args.append(suite)
    if test_type:
        where.append("r.test_type=%s"); args.append(test_type)
    rows = q(f"""SELECT r.*, c.requirement_group, c.requirement_id, c.requirement_title, c.sheet_name, c.functional_category, c.target_table,
                 c.target_column, c.assertion_name, c.template_name, c.source_ref, c.lakehouse_type
                 FROM taf_result r LEFT JOIN taf_case c ON c.test_id=r.test_id AND c.suite=r.suite WHERE {' AND '.join(where)}
                 ORDER BY r.suite, r.test_id LIMIT {LIMIT_RESULTS}""", tuple(args))
    return {"run_id": rid, "run": one("SELECT * FROM taf_run WHERE run_id=%s", (rid,)), "rows": rows,
            "distinct_checks": len({r["check_id"] for r in rows})}


# ---------------------------------------------------------------------------
# health scenarios
# ---------------------------------------------------------------------------
@router.get("/taf/scenarios")
def list_scenarios(p: dict = Depends(READ_AN)):
    reg = [s.public() for s in SC.load_scenarios()]
    last = {r["scenario_id"]: r for r in q("""SELECT DISTINCT ON (scenario_id) * FROM taf_scenario_run ORDER BY scenario_id, executed_at DESC""")}
    for s in reg:
        s["last_run"] = last.get(s["scenario_id"])
    return {"rows": reg, "databricks": DBX.config().configured}


@router.post("/taf/scenarios/execute")
def execute_scenarios(payload: Dict[str, Any] = Body(default={}), p: dict = Depends(EDIT)):
    cfg = DBX.config()
    on_dbx = payload.get("engine") == "Databricks"
    if on_dbx and not cfg.configured:
        raise HTTPException(400, "Databricks is not configured; run the scenarios on the workbench store instead")
    reg = {s.scenario_id: s for s in SC.load_scenarios()}
    wanted = payload.get("scenario_ids") or list(reg)
    unknown = [x for x in wanted if x not in reg]
    if unknown:
        raise HTTPException(400, f"unknown scenario ids: {unknown}")
    run_id = f"SC{_now().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(3)}"
    out = []
    for sid in wanted:
        s = reg[sid]
        sql = s.render(cfg.mass_fail_pct, cfg.stranded_hours, databricks=on_dbx, catalog=cfg.catalog, schema=cfg.schema)
        t0 = time.perf_counter()
        rows, err = None, None
        try:
            rows = DBX.query(sql) if on_dbx else q(sql)
        except Exception as e:  # any exception is ERROR, never a pass
            err = e
        dur = int((time.perf_counter() - t0) * 1000)
        status = SC.evaluate(s.kind, rows, err)
        ev = json.loads(json.dumps((rows or [])[:SC.EVIDENCE_ROWS], default=str))
        one("""INSERT INTO taf_scenario_run(run_id,scenario_id,scenario,status,violation_count,duration_ms,evidence,sql_used,error_message,engine)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING 1""",
            (run_id, sid, s.scenario, status, len(rows) if (rows is not None and s.kind == "find") else None, dur,
             json.dumps(ev)[:MAX_EVIDENCE_CHARS], sql, str(err)[:4000] if err else None, "Databricks" if on_dbx else "Workbench"))
        out.append({"scenario_id": sid, "scenario": s.scenario, "status": status, "kind": s.kind, "caveat": s.caveat, "duration_ms": dur,
                    "violation_count": len(rows) if (rows is not None and s.kind == "find") else None, "evidence": ev, "sql_used": sql,
                    "error_message": str(err)[:4000] if err else None})
    return {"run_id": run_id, "rows": out}


# ---------------------------------------------------------------------------
# failure triage: every failure, then a linked defect when it needs a fix
# ---------------------------------------------------------------------------
def triage_rows(include_resolved: bool = False, scope: str = "latest", x=None) -> List[Dict[str, Any]]:
    x = x or _Q()
    latest_taf = {s: _latest_run(s, x) for s in ("TAF", "EXTERNAL")}
    taf = x.q("""SELECT r.test_id || '::' || r.run_id AS failure_id, 'Data check' AS source, r.suite, r.run_id, r.test_id AS ref,
               r.severity, r.status, c.requirement_title AS title, r.violation_count, r.actual_result, r.error_message,
               r.sample_rows, r.executed_sql, u.started_at AS run_at, u.engine
               FROM taf_result r JOIN taf_run u ON u.run_id=r.run_id LEFT JOIN taf_case c ON c.test_id=r.test_id AND c.suite=r.suite
               WHERE r.status IN ('Fail','Error')""")
    if scope == "latest":
        taf = [r for r in taf if r["run_id"] == latest_taf.get(r["suite"])]
    cases = x.q("""SELECT c.key || '::C' || cy.id AS failure_id, 'Test case' AS source, 'CASE' AS suite, 'C' || cy.id AS run_id, c.key AS ref,
                 CASE c.priority WHEN 'High' THEN 'High' WHEN 'Low' THEN 'Low' ELSE 'Medium' END AS severity, 'failed' AS status,
                 c.title, NULL::int AS violation_count, r.detail AS actual_result, r.root_cause AS error_message, NULL::jsonb AS sample_rows,
                 NULL AS executed_sql, cy.started AS run_at, cy.engine, r.resolution AS suggested_fix, cy.id AS cycle_id, c.id AS case_id
                 FROM aw_result r JOIN aw_case c ON c.id=r.case_id JOIN aw_cycle cy ON cy.id=r.cycle_id WHERE r.status='failed'""")
    if scope == "latest":
        last_per_plan = {r["plan_id"]: r["id"] for r in x.q("SELECT DISTINCT ON (plan_id) plan_id, id FROM aw_cycle ORDER BY plan_id, id DESC")}
        cases = [r for r in cases if r["cycle_id"] in last_per_plan.values()]
    tri = {r["failure_id"]: r for r in x.q("SELECT t.*, d.key AS defect_key, d.status AS defect_status FROM aw_triage t LEFT JOIN aw_defect d ON d.id=t.defect_id")}
    out = []
    for r in taf + cases:
        t = tri.get(r["failure_id"], {})
        row = {**r, "recommended_fix": t.get("recommended_fix"), "suggested_fix": r.get("suggested_fix"), "resolved": bool(t.get("resolved")), "resolved_by": t.get("resolved_by"),
               "resolved_at": t.get("resolved_at"), "defect_id": t.get("defect_id"), "defect_key": t.get("defect_key"), "defect_status": t.get("defect_status")}
        if include_resolved or not row["resolved"]:
            out.append(row)
    sev = {"High": 0, "Medium": 1, "Low": 2}
    return sorted(out, key=lambda r: (r["resolved"], sev.get(r["severity"], 1), str(r["run_at"]), r["ref"]))


@router.get("/triage")
def triage(include_resolved: bool = False, scope: str = Query("latest", pattern="^(latest|all)$"), p: dict = Depends(READ_AN)):
    rows = triage_rows(include_resolved, scope)
    return {"rows": rows, "counts": {"open": sum(1 for r in rows if not r["resolved"]), "high": sum(1 for r in rows if r["severity"] == "High" and not r["resolved"]),
                                     "with_defect": sum(1 for r in rows if r["defect_id"]), "resolved": sum(1 for r in rows if r["resolved"])}}


def _check_failure(failure_id: str) -> Dict[str, Any]:
    if failure_id.count("::") != 1:
        raise HTTPException(400, "failure_id must be '<test>::<run>'")
    r = next((x for x in triage_rows(True, "all") if x["failure_id"] == failure_id), None)
    if not r:
        raise HTTPException(404, "no such failure")
    return r


@router.post("/triage/{failure_id}/resolve")
def resolve(failure_id: str, payload: Dict[str, Any] = Body(...), p: dict = Depends(EDIT)):
    r = _check_failure(failure_id)
    fix = (payload.get("recommended_fix") or "").strip() or None
    res = bool(payload.get("resolved"))
    if res and not fix:
        raise HTTPException(400, "record a recommended fix before resolving")
    one("""INSERT INTO aw_triage(failure_id,source,recommended_fix,resolved,resolved_by,resolved_at,updated_at)
           VALUES (%s,%s,%s,%s,%s,%s,now()) ON CONFLICT (failure_id) DO UPDATE SET recommended_fix=EXCLUDED.recommended_fix,
           resolved=EXCLUDED.resolved, resolved_by=EXCLUDED.resolved_by, resolved_at=EXCLUDED.resolved_at, updated_at=now() RETURNING 1""",
        (failure_id, r["source"], fix, res, p["code"] if res else None, _now() if res else None))
    got = one("SELECT * FROM aw_triage WHERE failure_id=%s", (failure_id,))
    if not got or got["resolved"] != res or (got["recommended_fix"] or None) != fix:
        raise HTTPException(500, "the change did not persist (re-query disagrees)")
    return {"ok": True, "verified": True, **got}


def raise_defect(x, r: Dict[str, Any], who: str, status: str = "Open") -> Dict[str, Any]:
    n = x.one("SELECT COUNT(*)+1 AS n FROM aw_defect")["n"]
    sev = {"High": "Critical", "Medium": "Major"}.get(r["severity"], "Minor")
    feature = r.get("suite") if r["source"] == "Data check" else (x.one("SELECT feature FROM aw_case WHERE id=%s", (r["case_id"],)) or {}).get("feature")
    comp = None
    if r["source"] == "Data check":
        c = x.one("SELECT target_table FROM taf_case WHERE test_id=%s AND suite=%s", (r["ref"], r["suite"]))
        comp = c["target_table"] if c else None
        feature = "Data checks · " + r["suite"]
    else:
        m = x.one("""SELECT m.module FROM aw_mapping mp JOIN aw_module m ON m.id=mp.module_id WHERE mp.case_id=%s ORDER BY mp.score DESC LIMIT 1""", (r["case_id"],))
        comp = m["module"] if m else None
    d = x.one("""INSERT INTO aw_defect(key,title,severity,status,case_id,feature,component,cycle_id,cause,failure_id)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
              (f"DEF-{n:03d}", f"{r['ref']}: {(r.get('title') or '')[:150]}", sev, status, r.get("case_id"), feature, comp, r.get("cycle_id"),
               r.get("error_message") or r.get("actual_result"), r["failure_id"]))
    x.one("""INSERT INTO aw_triage(failure_id,source,recommended_fix,defect_id,updated_at) VALUES (%s,%s,%s,%s,now())
             ON CONFLICT (failure_id) DO UPDATE SET defect_id=EXCLUDED.defect_id, recommended_fix=COALESCE(aw_triage.recommended_fix, EXCLUDED.recommended_fix),
             updated_at=now() RETURNING 1""", (r["failure_id"], r["source"], r.get("recommended_fix"), d["id"]))
    return d


@router.post("/triage/{failure_id}/defect")
def defect(failure_id: str, p: dict = Depends(EDIT)):
    r = _check_failure(failure_id)
    if r["defect_id"]:
        raise HTTPException(400, f"already linked to {r['defect_key']}")
    return raise_defect(_Q(), r, p["code"])
