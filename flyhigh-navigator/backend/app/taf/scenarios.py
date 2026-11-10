"""On-demand health scenarios (merged from the TAF operator app).

A scenario is one read-only query run on demand.
* kind="find"    -> the query returns offending rows: PASS if none, else FAIL.
* kind="summary" -> the query returns a summary: PASS if rows, else NO_DATA.
* any exception  -> ERROR, never a pass.

Every scenario states a caveat: what it cannot prove. The UI shows it next to the result so a
green tick never sits over an unprovable claim.

Each built-in has two forms: `sql` runs on the workbench's own store (every engine is mirrored
there), `sql_databricks` is the original against TAF's Unity Catalog views. Site-specific
scenarios can be added as data: a JSON list in TAF_SCENARIOS_FILE (or scenarios_extra.json here),
with {fail_pct} and {stranded_hours} substituted.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

PASS, FAIL, NO_DATA, ERROR = "PASS", "FAIL", "NO_DATA", "ERROR"
EVIDENCE_ROWS = 10
_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
_READ_ONLY_RE = re.compile(r"^\s*(--[^\n]*\n\s*)*(SELECT|WITH)\b", re.IGNORECASE)
_FORBIDDEN_RE = re.compile(r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE)\b", re.IGNORECASE)


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    scenario: str
    description: str
    kind: str
    sql: str
    caveat: str
    sql_databricks: str = ""

    def render(self, fail_pct: float, stranded_hours: float, databricks: bool = False, catalog: str = "", schema: str = "") -> str:
        s = self.sql_databricks if databricks and self.sql_databricks else self.sql
        return (s.replace("{catalog}", catalog).replace("{schema}", schema)
                 .replace("{fail_pct}", repr(float(fail_pct))).replace("{stranded_hours}", repr(float(stranded_hours))))

    def public(self) -> Dict[str, Any]:
        d = asdict(self)
        d["databricks"] = bool(self.sql_databricks)
        return d


LATEST = "(SELECT run_id FROM taf_run WHERE status <> 'Running' ORDER BY started_at DESC LIMIT 1)"
PREV = "(SELECT run_id FROM taf_run WHERE status <> 'Running' ORDER BY started_at DESC OFFSET 1 LIMIT 1)"


def _v(name: str) -> str:
    return f"`{{catalog}}`.`{{schema}}`.`{name}`"


_DB_LATEST = (f"(SELECT run_id FROM {_v('vw_ui_taf_runs')} WHERE status <> 'Running' ORDER BY started_at DESC LIMIT 1)")

BUILTIN_SCENARIOS: List[Scenario] = [
    Scenario("SC_REGRESSIONS", "Regressions vs previous run", "Checks that passed in the previous run and fail in the latest one.", "find",
             f"""SELECT cur.test_id, cur.test_type, cur.severity, prev.status AS prev_status, cur.status, cur.violation_count
                 FROM taf_result cur JOIN taf_result prev ON prev.test_id = cur.test_id AND prev.run_id = {PREV}
                 WHERE cur.run_id = {LATEST} AND prev.status = 'Pass' AND cur.status IN ('Fail', 'Error')""",
             "Only compares the two most recent completed runs. A check that was already failing, or did not run last time, is not a regression by this definition.",
             f"SELECT * FROM {_v('vw_taf_regressions')} WHERE run_id = {_DB_LATEST}"),
    Scenario("SC_ERRORED_TESTS", "Checks that could not execute", "Latest run: status Error, so the framework failed, not the data.", "find",
             f"SELECT test_id, test_type, severity, error_message FROM taf_result WHERE run_id = {LATEST} AND status = 'Error'",
             "Says nothing about data quality: an Error means the check did not run at all.",
             f"SELECT test_id, test_type, severity, error_message FROM {_v('vw_taf_report')} WHERE run_id = {_DB_LATEST} AND result_status = 'Error'"),
    Scenario("SC_UNRESOLVED_HIGH", "Unresolved High-severity failures without a fix", "Open High-severity failures in triage with no recommended fix recorded.", "find",
             """SELECT t.failure_id, r.test_id, r.run_id, r.severity FROM taf_result r
                JOIN aw_triage t ON t.failure_id = r.test_id || '::' || r.run_id
                WHERE r.severity = 'High' AND NOT t.resolved AND COALESCE(TRIM(t.recommended_fix), '') = ''""",
             "A recorded fix is free text. This cannot tell whether the fix is correct or applied.",
             f"""SELECT failure_id, test_id, run_id, severity FROM {_v('vw_validation_failures')}
                 WHERE severity = 'High' AND COALESCE(resolved, false) = false AND (recommended_fix IS NULL OR trim(recommended_fix) = '')"""),
    Scenario("SC_SCOPE_SKIPPED", "Requested scope not applied", "Latest run: checks where a requested filter dimension was skipped.", "find",
             f"SELECT test_id, filter_applied, filter_skipped_reason FROM taf_result WHERE run_id = {LATEST} AND COALESCE(TRIM(filter_skipped_reason), '') <> ''",
             "Checks that never asked for scoping are not listed. A skipped scope means the check ran on more data than requested, not that it is wrong.",
             f"""SELECT test_id, filter_applied, filter_skipped_reason FROM {_v('vw_taf_report')}
                 WHERE run_id = {_DB_LATEST} AND filter_skipped_reason IS NOT NULL AND trim(filter_skipped_reason) <> ''"""),
    Scenario("SC_STRANDED_RUNS", "Runs stranded at Running", "Runs still Running after the stranded threshold.", "find",
             "SELECT run_id, engine, started_at, triggered_by, upstream_pipeline_run FROM taf_run WHERE status = 'Running' AND started_at < now() - make_interval(hours => CAST({stranded_hours} AS INT))",
             "A long run may be legitimately slow. This cannot distinguish a stuck job from a large external suite.",
             f"""SELECT run_id, started_at, triggered_by, upstream_pipeline_run FROM {_v('vw_ui_taf_running_manifests')}
                 WHERE started_at < current_timestamp() - make_dt_interval(0, CAST({{stranded_hours}} AS INT))"""),
    Scenario("SC_MASS_FAILURE", "Mass-failure check (latest run)", "Flags the latest run if its fail percentage exceeds the threshold (TAF_MASS_FAIL_PCT).", "find",
             f"""SELECT run_id, total_tests, fail_count, error_count, ROUND(100.0 * (fail_count + error_count) / total_tests, 2) AS fail_pct
                 FROM taf_run WHERE run_id = {LATEST} AND total_tests > 0 AND 100.0 * (fail_count + error_count) / total_tests > {{fail_pct}}""",
             "The threshold is a configured guess. A bad upstream file and a broken framework both look like mass failure here.",
             f"""SELECT run_id, total_tests, fail_count, error_count, round(100.0 * (fail_count + error_count) / total_tests, 2) AS fail_pct
                 FROM {_v('vw_ui_taf_runs')} WHERE run_id = {_DB_LATEST} AND total_tests > 0 AND 100.0 * (fail_count + error_count) / total_tests > {{fail_pct}}"""),
    Scenario("SC_RUN_TREND", "Run trend (last 14 runs)", "Pass and fail counts across recent runs.", "summary",
             "SELECT run_id, engine, started_at, status, total_tests, pass_count, fail_count, warn_count, error_count FROM taf_run WHERE status <> 'Running' ORDER BY started_at DESC LIMIT 14",
             "A summary, not an assertion: PASS only means there is data to look at.",
             f"SELECT * FROM {_v('vw_taf_run_trend')} ORDER BY started_at DESC LIMIT 14"),
]


def _validate(raw: Dict[str, Any]) -> Scenario:
    sc = Scenario(scenario_id=str(raw["scenario_id"]), scenario=str(raw["scenario"]), description=str(raw.get("description", "")),
                  kind=str(raw.get("kind", "find")).lower(), sql=str(raw["sql"]), caveat=str(raw.get("caveat", "")).strip(),
                  sql_databricks=str(raw.get("sql_databricks", "")))
    if not _ID_RE.match(sc.scenario_id):
        raise ValueError(f"bad scenario_id {sc.scenario_id!r}")
    if sc.kind not in ("find", "summary"):
        raise ValueError(f"{sc.scenario_id}: kind must be find|summary")
    if not sc.caveat:
        raise ValueError(f"{sc.scenario_id}: every scenario must state a caveat")
    for q in (sc.sql, sc.sql_databricks):
        if q and (not _READ_ONLY_RE.match(q) or _FORBIDDEN_RE.search(q)):
            raise ValueError(f"{sc.scenario_id}: scenario SQL must be a single read-only SELECT/WITH")
        if q and ";" in q.strip().rstrip(";"):
            raise ValueError(f"{sc.scenario_id}: one statement only")
    return sc


def load_scenarios(extra_path: Optional[str] = None) -> List[Scenario]:
    out = {s.scenario_id: s for s in BUILTIN_SCENARIOS}
    path = extra_path or os.environ.get("TAF_SCENARIOS_FILE") or os.path.join(os.path.dirname(__file__), "scenarios_extra.json")
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for raw in json.load(fh):
                sc = _validate(raw)
                out[sc.scenario_id] = sc
    return list(out.values())


def evaluate(kind: str, rows: Optional[List[Dict[str, Any]]], error: Optional[BaseException]) -> str:
    if error is not None:
        return ERROR
    if kind == "summary":
        return PASS if rows else NO_DATA
    return FAIL if rows else PASS
