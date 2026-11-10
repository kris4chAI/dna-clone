"""Databricks execution engine for TAF (merged from the TAF operator app).

When DATABRICKS_HOST and credentials are set, the assurance workbench can launch TAF's notebook
chain on Databricks (jobs.submit, no blocking), poll it, close its manifest with the TAF status
rules, read the consolidated run log and mirror the results into the workbench so analytics,
triage and the lakehouse test map see every engine the same way.

Differences from the original app, on purpose:
* SQL goes through the Databricks SQL Statement Execution API in databricks-sdk instead of
  databricks-sql-connector (which pulls pandas and pyarrow into the image). Named parameters,
  never string-built values, as before.
* Configuration keeps the original variable names (APP_TAF_*), read from FlyHigh's .env.
* Unsubstituted placeholders degrade to DEV-shaped defaults and never crash the app.
"""
from __future__ import annotations

import io
import json
import logging
import os
import re
import threading
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from typing import Any, Dict, List, Optional

from . import logic as L

log = logging.getLogger("taf.databricks")

ENVIRONMENTS = ("dev", "tst", "stg", "prd")
_ENV_RE = re.compile(r"(?<![a-z])(dev|tst|stg|prd)(?![a-z])", re.IGNORECASE)
_PLACEHOLDER_RE = re.compile(r"^(_{1,2}[A-Z0-9_]+_{1,2}|\$\{[^}]*\}|<[^>]*>)$")
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class NotConfigured(RuntimeError):
    pass


def is_placeholder(value: Optional[str]) -> bool:
    if value is None:
        return True
    v = value.strip()
    return v == "" or bool(_PLACEHOLDER_RE.match(v)) or "PLACEHOLDER" in v.upper()


def env_value(name: str, default: Optional[str] = None) -> Optional[str]:
    raw = os.environ.get(name)
    return default if is_placeholder(raw) else raw.strip()


def detect_environment() -> str:
    explicit = env_value("APP_TAF_ENVIRONMENT")
    if explicit and explicit.lower() in ENVIRONMENTS:
        return explicit.lower()
    for var in ("APP_UC_CREDENTIAL_NAME", "APP_DOWNSTREAM_DB_ENDPOINT", "DATABRICKS_HOST"):
        val = env_value(var)
        if val:
            m = _ENV_RE.search(val)
            if m:
                return m.group(1).lower()
    return "dev"


def safe_identifier(value: str, what: str) -> str:
    if not _IDENT_RE.match(value or ""):
        raise ValueError(f"{what} {value!r} is not a valid Unity Catalog identifier")
    return value


@dataclass(frozen=True)
class Config:
    configured: bool
    host: Optional[str]
    environment: str
    catalog: str
    schema: str
    http_path: Optional[str]
    notebook_dir: str
    log_dir: str
    upload_dir: str
    run_as_sp: Optional[str]
    mass_fail_pct: float
    stranded_hours: float
    defaults_applied: tuple

    def public(self) -> Dict[str, Any]:
        d = asdict(self)
        d["defaults_applied"] = list(self.defaults_applied)
        d["warehouse_source"] = "configured" if self.http_path else "auto-discover"
        d.pop("http_path", None)
        return d


@lru_cache(maxsize=1)
def config() -> Config:
    defaults = []
    env = detect_environment()
    catalog = env_value("APP_TAF_CATALOG")
    if catalog is None:
        catalog = f"{env_value('APP_TAF_CATALOG_PREFIX', 'taf')}_{env}"
        defaults.append("catalog")
    schema = env_value("APP_TAF_SCHEMA")
    if schema is None:
        schema = "raw"
        defaults.append("schema")
    safe_identifier(catalog, "catalog")
    safe_identifier(schema, "schema")
    nb = env_value("APP_TAF_NOTEBOOK_DIR")
    if nb is None:
        nb = "/Workspace/Shared/taf/files/notebooks/taf/notebooks"
        defaults.append("notebook_dir")
    volume = f"/Volumes/{catalog}/{schema}/taf_uploads"
    http_path = env_value("APP_TAF_HTTP_PATH")
    if http_path is None:
        defaults.append("http_path")
    host = env_value("DATABRICKS_HOST")
    creds = env_value("DATABRICKS_TOKEN") or (env_value("DATABRICKS_CLIENT_ID") and env_value("DATABRICKS_CLIENT_SECRET"))
    return Config(configured=bool(host and creds), host=host, environment=env, catalog=catalog, schema=schema,
                  http_path=http_path, notebook_dir=nb.rstrip("/"), log_dir=(env_value("APP_TAF_LOG_DIR") or f"{volume}/logs").rstrip("/"),
                  upload_dir=volume, run_as_sp=env_value("APP_TAF_RUN_AS_SP"),
                  mass_fail_pct=float(env_value("APP_TAF_MASS_FAIL_PCT", "25") or 25),
                  stranded_hours=float(env_value("APP_TAF_STRANDED_HOURS", "12") or 12), defaults_applied=tuple(defaults))


def fqn(name: str) -> str:
    cfg = config()
    safe_identifier(name, "object")
    return f"`{cfg.catalog}`.`{cfg.schema}`.`{name}`"


# ---------------------------------------------------------------------------
# workspace client + SQL through the Statement Execution API
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_client = None
_wh_cache: Optional[str] = None


def client():
    global _client
    if not config().configured:
        raise NotConfigured("Databricks is not configured: set DATABRICKS_HOST and DATABRICKS_TOKEN "
                            "(or DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET) and APP_TAF_* in .env")
    with _lock:
        if _client is None:
            try:
                from databricks.sdk import WorkspaceClient
            except ImportError as e:
                raise NotConfigured("databricks-sdk is missing from the image; rebuild with docker compose build") from e
            _client = WorkspaceClient()
        return _client


def set_client(c) -> None:
    """Test hook."""
    global _client
    _client = c


def warehouse_id() -> str:
    global _wh_cache
    hp = config().http_path
    if hp:
        return hp.rstrip("/").split("/")[-1]
    if _wh_cache:
        return _wh_cache
    for wh in client().warehouses.list():
        state = getattr(getattr(wh, "state", None), "value", str(getattr(wh, "state", "")))
        if str(state).upper() == "RUNNING":
            _wh_cache = wh.id
            return wh.id
    raise NotConfigured("No SQL warehouse configured (APP_TAF_HTTP_PATH) and none is RUNNING to auto-discover")


def _jsonable(v: Any) -> Any:
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


def query(sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    from databricks.sdk.service.sql import StatementParameterListItem, StatementState
    w = client()
    plist = [StatementParameterListItem(name=k, value=None if v is None else str(v)) for k, v in (params or {}).items()]
    r = w.statement_execution.execute_statement(statement=sql, warehouse_id=warehouse_id(), parameters=plist or None,
                                                wait_timeout="50s")
    deadline = time.time() + 300
    while r.status and r.status.state in (StatementState.PENDING, StatementState.RUNNING) and time.time() < deadline:
        time.sleep(1.5)
        r = w.statement_execution.get_statement(r.statement_id)
    if not r.status or r.status.state != StatementState.SUCCEEDED:
        err = getattr(getattr(r.status, "error", None), "message", None) or str(getattr(r.status, "state", "unknown"))
        raise RuntimeError(f"Databricks SQL failed: {err}")
    if not r.manifest or not r.manifest.schema or not r.manifest.schema.columns:
        return []
    cols = [c.name for c in r.manifest.schema.columns]
    rows = list((r.result.data_array if r.result else None) or [])
    chunk = r.result.next_chunk_index if r.result else None
    while chunk is not None:
        part = w.statement_execution.get_statement_result_chunk_n(r.statement_id, chunk)
        rows += list(part.data_array or [])
        chunk = part.next_chunk_index
    return [{c: _jsonable(v) for c, v in zip(cols, row)} for row in rows]


def execute(sql: str, params: Optional[Dict[str, Any]] = None) -> None:
    query(sql, params)


# ---------------------------------------------------------------------------
# run lifecycle on Databricks
# ---------------------------------------------------------------------------
def job_state(job_run) -> Dict[str, Any]:
    st = getattr(job_run, "state", None)
    lcs = getattr(getattr(st, "life_cycle_state", None), "value", None) or str(getattr(st, "life_cycle_state", "") or "")
    rs = getattr(getattr(st, "result_state", None), "value", None) or (str(st.result_state) if st and st.result_state else None)
    return {"life_cycle_state": lcs, "result_state": rs, "state_message": getattr(st, "state_message", "") or "",
            "terminal": lcs in L.TERMINAL_LIFECYCLE}


def submit(req: L.ExecuteRequest, run_id: str, submitted_by: str) -> Dict[str, Any]:
    from databricks.sdk.service.jobs import JobRunAs, NotebookTask, SubmitTask, TaskDependency
    cfg = config()
    log_file = L.log_file_for(cfg.log_dir, run_id)
    params = L.build_base_parameters(req, run_id=run_id, catalog=cfg.catalog, schema=cfg.schema, log_file=log_file,
                                     environment=cfg.environment)
    chain = L.build_chain(req.test_scope, cfg.notebook_dir)
    tasks = [SubmitTask(task_key=t["task_key"], notebook_task=NotebookTask(notebook_path=t["notebook_path"], base_parameters=params),
                        depends_on=[TaskDependency(task_key=d) for d in t["depends_on"]] or None, timeout_seconds=t["timeout_seconds"])
             for t in chain]
    extra = {"run_as": JobRunAs(service_principal_name=cfg.run_as_sp)} if cfg.run_as_sp else {}
    waiter = client().jobs.submit(run_name=f"TAF UI {req.test_scope} {run_id}", tasks=tasks, timeout_seconds=36000, **extra)
    job_run_id = getattr(getattr(waiter, "response", None), "run_id", None) or waiter.run_id
    notes = json.dumps({"test_scope": req.test_scope, "log_file": log_file, "filter_mode": req.filter_mode,
                        "date_source": req.date_source, "submitted_by": submitted_by})
    warnings = []
    try:  # the Running manifest row in UC keeps the run recoverable from TAF's own views
        execute(f"""INSERT INTO {fqn('taf_run_manifest')}
            (run_id, started_at, status, run_scope, triggered_by, upstream_pipeline_run, input_source,
             total_tests, pass_count, fail_count, warn_count, error_count, manual_count, not_run_count, notes)
            VALUES (:run_id, current_timestamp(), 'Running', :run_scope, :triggered_by, :job_run_id, :input_source, 0,0,0,0,0,0,0, :notes)""",
                {"run_id": run_id, "run_scope": req.run_scope or "ALL", "triggered_by": L.TRIGGERED_BY, "job_run_id": str(job_run_id),
                 "input_source": req.source_file_path or "deployed workbook + cases/", "notes": notes})
    except Exception:
        log.exception("manifest insert failed for %s", run_id)
        warnings.append("manifest row NOT written in Unity Catalog: TAF's own views will not show this run")
    return {"job_run_id": str(job_run_id), "log_file": log_file, "chain": [t["task_key"] for t in chain], "warnings": warnings}


def status(job_run_id: str) -> Dict[str, Any]:
    jr = client().jobs.get_run(int(job_run_id))
    st = job_state(jr)
    st["tasks"] = [{"task_key": t.task_key, "run_id": getattr(t, "run_id", None), **job_state(t)} for t in (getattr(jr, "tasks", None) or [])]
    st["run_page_url"] = getattr(jr, "run_page_url", None)
    return st


def results(run_id: str) -> List[Dict[str, Any]]:
    """Results of one run from TAF's view contract, in the workbench's result shape."""
    rows = query(f"""SELECT test_id, test_type, severity, result_status AS status, violation_count, expected_result, actual_result,
                     executed_sql, sample_rows_preview, duration_ms, executed_at, filter_applied, filter_skipped_reason, error_message,
                     requirement_group, requirement_id, requirement_title, target_table, target_column, 'TAF' AS suite, test_id AS check_id
                     FROM {fqn('vw_taf_report')} WHERE run_id = :r""", {"r": run_id})
    rows += query(f"""SELECT test_id, test_type, severity, status, violation_count, CAST(NULL AS STRING) AS expected_result,
                      comments AS actual_result, sql_script AS executed_sql, CAST(NULL AS STRING) AS sample_rows_preview, duration_ms,
                      executed_at, filter_applied, CAST(NULL AS STRING) AS filter_skipped_reason, CAST(NULL AS STRING) AS error_message,
                      category AS requirement_group, feature_reference AS requirement_id, test_scenario AS requirement_title,
                      CAST(NULL AS STRING) AS target_table, CAST(NULL AS STRING) AS target_column, 'EXTERNAL' AS suite, check_id
                      FROM {fqn('vw_validation_results')} WHERE suite = 'EXTERNAL' AND run_id = :r""", {"r": run_id})
    return rows


def close_manifest(run_id: str, result_state: Optional[str], counts: Dict[str, int], note: str) -> None:
    status_, _ = L.final_manifest_status(result_state, counts)
    try:
        execute(f"""UPDATE {fqn('taf_run_manifest')} SET status = :status, finished_at = current_timestamp(),
            total_tests = :total_tests, pass_count = :pass_count, fail_count = :fail_count, warn_count = :warn_count,
            error_count = :error_count, manual_count = :manual_count, not_run_count = :not_run_count,
            notes = concat_ws(' | ', notes, :note) WHERE run_id = :run_id AND status = 'Running'""",
                {"status": status_, "note": note, "run_id": run_id, **counts})
    except Exception:
        log.exception("closing UC manifest failed for %s", run_id)


def read_log(run_id: str, job_run_id: Optional[str], tail_kb: int = 512) -> Dict[str, Any]:
    cfg = config()
    w = client()
    log_file = L.log_file_for(cfg.log_dir, run_id)
    try:
        raw = w.files.download(log_file).contents.read()
        limit = tail_kb * 1024
        return {"source": "volume", "log_file": log_file, "truncated": len(raw) > limit, "content": raw[-limit:].decode("utf-8", errors="replace")}
    except Exception as exc:
        log.info("log file not readable (%s), falling back to job output", exc)
    if not (job_run_id or "").isdigit():
        return {"source": "none", "log_file": log_file, "truncated": False, "content": f"(no log at {log_file})"}
    parts = []
    for t in (getattr(w.jobs.get_run(int(job_run_id)), "tasks", None) or []):
        try:
            o = w.jobs.get_run_output(t.run_id)
            nb = getattr(getattr(o, "notebook_output", None), "result", None)
            parts.append(f"===== task {t.task_key} =====\n" + (f"exit: {nb}\n" if nb else "")
                         + (f"error: {o.error}\n" if getattr(o, "error", None) else "") + (f"{o.error_trace}\n" if getattr(o, "error_trace", None) else ""))
        except Exception as exc:
            parts.append(f"===== task {t.task_key} =====\n(output unavailable: {exc})\n")
    return {"source": "job_output", "log_file": log_file, "truncated": False, "content": "\n".join(parts) or "(no output yet)"}


def upload(filename: str, data: bytes) -> str:
    """Upload a workbook or YAML to the UC volume. Fails loudly: never a local fallback,
    because job compute cannot see the app's disk."""
    path = L.upload_path(config().upload_dir, filename)
    client().files.upload(path, io.BytesIO(data), overwrite=False)
    return path


def set_active(test_id: str, suite: str, is_active: bool, user: str) -> None:
    """Write-through of the activate toggle to taf_test_suite, verified by re-query."""
    execute(f"""UPDATE {fqn('taf_test_suite')} SET is_active = :a, deactivated_by = CASE WHEN :a = 'true' THEN NULL ELSE :u END,
               deactivated_at = CASE WHEN :a = 'true' THEN NULL ELSE current_timestamp() END, updated_at = current_timestamp()
               WHERE test_id = :t AND suite = :s""", {"a": str(is_active).lower(), "u": user, "t": test_id, "s": suite})
    got = query(f"SELECT is_active FROM {fqn('vw_validation_test_suite')} WHERE test_id = :t AND suite = :s LIMIT 1", {"t": test_id, "s": suite})
    if not got or str(got[0]["is_active"]).lower() != str(is_active).lower():
        raise RuntimeError("the toggle did not persist in taf_test_suite (re-query disagrees)")


def suite_rows() -> List[Dict[str, Any]]:
    return query(f"SELECT * FROM {fqn('vw_validation_test_suite')} ORDER BY suite, test_id LIMIT 10000")
