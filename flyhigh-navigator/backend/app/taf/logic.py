"""TAF (test automation framework) pure logic: no database, no FastAPI, no SDK.

Merged from the TAF operator app into the assurance workbench. The rules are kept as the
framework defines them (scopes, filter modes, run ids, validation, Passed/Partial/Error),
and extended with an execution engine: Simulator, Snowflake or Databricks.
On Databricks a scope maps to a notebook chain; on Snowflake and the simulator it maps to
the assertion types it runs. Unit-tested in backend/tests/test_taf_logic.py.
"""
from __future__ import annotations

import re
import secrets
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Tuple

# ── vocabulary (spec §2) ─────────────────────────────────────────────────────
STATUSES = ("Pass", "Fail", "Warn", "Error", "Skipped", "Manual", "Info", "Not_Run", "Blocked")
FILTER_MODES = ("FULL", "LATEST_LOAD", "SINGLE_DATE", "DATE_RANGE", "INCREMENTAL", "CDF_RANGE")
DATE_SOURCES = ("BUSINESS", "CDF")
TRIGGERED_BY = "ui_manual"
ENGINES = ("Simulator", "Snowflake", "Databricks")

# ── §10.3 test_scope -> notebook chain ───────────────────────────────────────
SCOPE_ALL = "All Active Test Cases"
SCOPE_CLIENT = "Client Specific Cases"
SCOPE_COLUMN = "Column Assertions Only"
SCOPE_TEMPLATE = "Template Assertions Only"
SCOPE_SQL = "SQL Assertions Only"
SCOPE_EXTERNAL = "External Suite"

TEST_SCOPE_CHAINS: Dict[str, Tuple[str, ...]] = {
    SCOPE_ALL: ("00_Full_Run",),
    SCOPE_CLIENT: ("00_Full_Run",),
    SCOPE_COLUMN: ("02_Load_Test_Catalog", "03_Compile_Plans", "05_Column_Runner"),
    SCOPE_TEMPLATE: ("02_Load_Test_Catalog", "03_Compile_Plans", "06_Template_Runner"),
    SCOPE_SQL: ("02_Load_Test_Catalog", "03_Compile_Plans", "07_SQL_Runner"),
    SCOPE_EXTERNAL: ("External_Suite_Runner",),
}
# Snowflake and simulator: scope -> assertion types it runs (suite EXTERNAL for the external suite)
SCOPE_TYPES: Dict[str, Tuple[str, ...]] = {
    SCOPE_ALL: ("COLUMN", "TEMPLATE", "SQL", "MANUAL"),
    SCOPE_CLIENT: ("COLUMN", "TEMPLATE", "SQL", "MANUAL"),
    SCOPE_COLUMN: ("COLUMN",), SCOPE_TEMPLATE: ("TEMPLATE",), SCOPE_SQL: ("SQL",),
    SCOPE_EXTERNAL: ("COLUMN", "TEMPLATE", "SQL", "MANUAL"),
}
# Per-notebook task timeouts, seconds. 00_Full_Run matches the 10 h job timeout (§9.4).
TASK_TIMEOUTS = {
    "00_Full_Run": 36000, "02_Load_Test_Catalog": 600, "03_Compile_Plans": 600,
    "05_Column_Runner": 600, "06_Template_Runner": 600, "07_SQL_Runner": 900,
    "External_Suite_Runner": 13500,
}

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._\-]+")
UPLOAD_EXTENSIONS = (".xlsx", ".xlsm", ".yaml", ".yml")


class ValidationError(ValueError):
    """A request the UI should show back to the operator (HTTP 400)."""


def new_ui_run_id(now: Optional[datetime] = None) -> str:
    """"UI" + %Y%m%d_%H%M%S + "_" + 6 hex. Distinct from the numeric job run id."""
    now = now or datetime.now(timezone.utc)
    return f"UI{now.strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(3)}"


def _yn(v, default: str) -> str:
    if v is None or v == "":
        return default
    if isinstance(v, bool):
        return "yes" if v else "no"
    s = str(v).strip().lower()
    if s in ("yes", "y", "true", "1"):
        return "yes"
    if s in ("no", "n", "false", "0"):
        return "no"
    raise ValidationError(f"expected yes/no, got {v!r}")


def _parse_date(name: str, v: str) -> date:
    if not _DATE_RE.match(v or ""):
        raise ValidationError(f"{name} must be YYYY-MM-DD, got {v!r}")
    try:
        return date.fromisoformat(v)
    except ValueError as exc:
        raise ValidationError(f"{name} is not a real date: {v!r}") from exc


@dataclass
class ExecuteRequest:
    engine: str = "Simulator"
    test_scope: str = SCOPE_ALL
    run_scope: str = "ALL"
    filter_mode: str = "FULL"
    date_source: str = "BUSINESS"
    filter_start_date: str = ""
    filter_end_date: str = ""
    lookback_days: str = ""
    filter_tenant_code: str = ""
    filter_period: str = ""
    filter_segment: str = ""
    sheet_filter: str = "ALL"
    source_file_path: str = ""
    run_external_suite: str = "yes"
    capture_records: str = "yes"
    failure_max_rows: str = "10000"
    passing_sample_pct: str = "0"
    send_report: str = "no"
    send_alerts: str = "no"
    report_recipients: str = ""
    alert_recipients: str = ""
    warnings: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Dict) -> "ExecuteRequest":
        known = {k: v for k, v in (d or {}).items() if k in cls.__dataclass_fields__ and k != "warnings"}
        req = cls(**{k: ("" if v is None else v) for k, v in known.items()})
        req.validate()
        return req

    def validate(self) -> None:
        self.engine = str(self.engine or "Simulator").strip().title()
        if self.engine not in ENGINES:
            raise ValidationError(f"unknown engine {self.engine!r}; one of {list(ENGINES)}")
        if self.test_scope not in TEST_SCOPE_CHAINS:
            raise ValidationError(f"unknown test_scope {self.test_scope!r}; one of {list(TEST_SCOPE_CHAINS)}")
        self.filter_mode = str(self.filter_mode or "FULL").upper()
        self.date_source = str(self.date_source or "BUSINESS").upper()
        if self.filter_mode not in FILTER_MODES:
            raise ValidationError(f"unknown filter_mode {self.filter_mode!r}")
        if self.date_source not in DATE_SOURCES:
            raise ValidationError(f"unknown date_source {self.date_source!r}")
        # §10.3: reject LATEST_LOAD + CDF
        if self.filter_mode == "LATEST_LOAD" and self.date_source == "CDF":
            raise ValidationError("LATEST_LOAD cannot be combined with date_source=CDF: "
                                  "CDF has no notion of a 'latest load' date")
        # §10.3: reject SINGLE_DATE / DATE_RANGE without dates (CDF_RANGE is a DATE_RANGE alias)
        self.filter_start_date = str(self.filter_start_date or "").strip()
        self.filter_end_date = str(self.filter_end_date or "").strip()
        if self.filter_mode == "SINGLE_DATE":
            if not self.filter_start_date:
                raise ValidationError("SINGLE_DATE needs filter_start_date")
            _parse_date("filter_start_date", self.filter_start_date)
            if self.filter_end_date and self.filter_end_date != self.filter_start_date:
                raise ValidationError("SINGLE_DATE takes one date: leave filter_end_date blank")
        if self.filter_mode in ("DATE_RANGE", "CDF_RANGE"):
            if not (self.filter_start_date and self.filter_end_date):
                raise ValidationError(f"{self.filter_mode} needs both filter_start_date and filter_end_date")
            s = _parse_date("filter_start_date", self.filter_start_date)
            e = _parse_date("filter_end_date", self.filter_end_date)
            if s > e:
                raise ValidationError("filter_start_date is after filter_end_date")
        if self.filter_mode in ("FULL", "LATEST_LOAD", "INCREMENTAL") and (self.filter_start_date or self.filter_end_date):
            self.warnings.append(f"dates are ignored under filter_mode={self.filter_mode}")
        lb = str(self.lookback_days or "").strip()
        if lb:
            if not lb.isdigit() or int(lb) < 1:
                raise ValidationError("lookback_days must be a positive integer")
            if self.filter_mode != "INCREMENTAL":
                self.warnings.append("lookback_days only applies to INCREMENTAL")
        self.lookback_days = lb  # empty -> taf_filters applies its own default of 1
        if self.test_scope == SCOPE_CLIENT and (self.run_scope in ("", "ALL")) and not self.filter_tenant_code:
            raise ValidationError("Client Specific Cases needs a run_scope tag or a filter_tenant_code")
        for name in ("run_external_suite", "capture_records", "send_report", "send_alerts"):
            setattr(self, name, _yn(getattr(self, name), "no" if name.startswith("send") else "yes"))
        if not str(self.failure_max_rows).strip().isdigit():
            raise ValidationError("failure_max_rows must be a non-negative integer")
        try:
            pct = float(self.passing_sample_pct or 0)
        except ValueError as exc:
            raise ValidationError("passing_sample_pct must be a number") from exc
        if not 0.0 <= pct <= 100.0:
            raise ValidationError("passing_sample_pct must be between 0 and 100")
        if self.engine == "Databricks" and self.source_file_path and not str(self.source_file_path).startswith("/Volumes/"):
            raise ValidationError("source_file_path must be a /Volumes/... path from /upload "
                                  "(job compute cannot see the app's local disk)")
        if self.test_scope == SCOPE_EXTERNAL:
            self.run_external_suite = "yes"


def build_base_parameters(req: ExecuteRequest, *, run_id: str, catalog: str, schema: str,
                          log_file: str, environment: str) -> Dict[str, str]:
    """Widget values shared by every notebook in the chain. Every notebook gets
    the same run_id and log_file so one consolidated log explains the run.
    All values are strings: yes/no stay the strings "yes"/"no"."""
    p = {
        "catalog": catalog, "raw_schema": schema, "run_id": run_id, "environment": environment,
        "triggered_by": TRIGGERED_BY,
        # The job run id is only known after submit; the app links it through the
        # Running manifest row it inserts, and recovers run_id from the task's
        # base_parameters if the orchestrator later rewrites that row.
        "upstream_pipeline_run": "",
        "log_file": log_file, "run_scope": req.run_scope or "ALL",
        "filter_mode": req.filter_mode, "date_source": req.date_source,
        "filter_start_date": req.filter_start_date, "filter_end_date": req.filter_end_date,
        "lookback_days": req.lookback_days, "filter_tenant_code": req.filter_tenant_code,
        "filter_period": req.filter_period, "filter_segment": req.filter_segment,
        "sheet_filter": req.sheet_filter or "ALL", "run_external_suite": req.run_external_suite,
        "capture_records": req.capture_records, "failure_max_rows": str(req.failure_max_rows),
        "passing_sample_pct": str(req.passing_sample_pct or "0"),
        "send_report": req.send_report, "send_alerts": req.send_alerts,
        "report_recipients": req.report_recipients, "alert_recipients": req.alert_recipients,
        "absorb_child_logs": "yes",
    }
    if req.source_file_path:
        p["source_file_path"] = req.source_file_path
        p["external_tc_path"] = req.source_file_path
    return {k: str(v) for k, v in p.items()}


def build_chain(test_scope: str, notebook_dir: str) -> List[Dict[str, object]]:
    """[{task_key, notebook_path, depends_on, timeout_seconds}] chained linearly."""
    chain = []
    prev = None
    for nb in TEST_SCOPE_CHAINS[test_scope]:
        key = re.sub(r"[^A-Za-z0-9_]", "_", nb).lower()
        chain.append({"task_key": key, "notebook_path": f"{notebook_dir}/{nb}",
                      "depends_on": [prev] if prev else [], "timeout_seconds": TASK_TIMEOUTS.get(nb, 900)})
        prev = key
    return chain


def log_file_for(log_dir: str, run_id: str) -> str:
    return f"{log_dir}/taf_run_{run_id}.log"


def upload_path(upload_dir: str, filename: str, now: Optional[datetime] = None) -> str:
    base = (filename or "").replace("\\", "/").split("/")[-1]
    if not base.lower().endswith(UPLOAD_EXTENSIONS):
        raise ValidationError(f"only {', '.join(UPLOAD_EXTENSIONS)} uploads are accepted")
    safe = _SAFE_NAME_RE.sub("_", base).strip("._") or "upload.xlsx"
    ts = (now or datetime.now(timezone.utc)).strftime("%Y%m%d_%H%M%S")
    return f"{upload_dir}/{ts}_{safe}"


def split_failure_id(failure_id: str) -> Tuple[str, str]:
    """failure_id is the composite "{test_id}::{run_id}" (spec §4.5)."""
    if failure_id.count("::") != 1:
        raise ValidationError("failure_id must be '<test_id>::<run_id>'")
    test_id, run_id = failure_id.split("::")
    if not test_id or not run_id:
        raise ValidationError("failure_id must be '<test_id>::<run_id>'")
    return test_id, run_id


# ── run lifecycle ────────────────────────────────────────────────────────────
TERMINAL_LIFECYCLE = ("TERMINATED", "SKIPPED", "INTERNAL_ERROR")


def tally(status_rows: List[Dict]) -> Dict[str, int]:
    """[{status, n}] -> manifest counts. Unknown statuses count toward total only."""
    out = {"total_tests": 0, "pass_count": 0, "fail_count": 0, "warn_count": 0,
           "error_count": 0, "manual_count": 0, "not_run_count": 0}
    key = {"Pass": "pass_count", "Fail": "fail_count", "Warn": "warn_count", "Error": "error_count",
           "Manual": "manual_count", "Not_Run": "not_run_count", "Skipped": "not_run_count"}
    norm = {"PASS": "Pass", "PASSED": "Pass", "FAIL": "Fail", "FAILED": "Fail", "WARN": "Warn",
            "WARNING": "Warn", "ERROR": "Error", "MANUAL": "Manual", "NOT_RUN": "Not_Run",
            "NOT RUN": "Not_Run", "SKIPPED": "Skipped"}
    for r in status_rows:
        s = norm.get(str(r.get("status") or "").strip().upper(), str(r.get("status") or ""))
        n = int(r.get("n") or 0)
        out["total_tests"] += n
        if s in key:
            out[key[s]] += n
    return out


def final_manifest_status(job_result_state: Optional[str], counts: Dict[str, int]) -> Tuple[str, str]:
    """(status, note). A UI-triggered run is ui_manual -> report_only semantics:
    findings are reported, never treated as a broken job (principle 6).
    Zero executed checks is Error, never green (principle 5)."""
    rs = (job_result_state or "").upper()
    executed = counts["pass_count"] + counts["fail_count"] + counts["warn_count"] + counts["error_count"]
    if rs not in ("SUCCESS", "SUCCESS_WITH_FAILURES"):
        return "Error", f"job ended {rs or 'UNKNOWN'}: the framework did not complete"
    if executed == 0:
        return "Error", "zero checks executed: a run that checks nothing is not green"
    if counts["fail_count"] or counts["error_count"]:
        return "Partial", (f"{counts['fail_count']} fail, {counts['error_count']} error "
                           "(manual trigger: findings reported, job not failed)")
    return "Passed", "clean"
