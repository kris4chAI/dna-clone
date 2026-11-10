"""Workbench-side TAF: Databricks config, health scenarios and the Snowflake/Simulator compiler."""
import json

import pytest

from app.taf import databricks as dbx
from app.taf import local
from app.taf import logic as L
from app.taf import scenarios as sc
from app.taf.catalog import taf_rows


@pytest.fixture(autouse=True)
def clear(monkeypatch):
    for k in ("APP_TAF_CATALOG", "APP_TAF_SCHEMA", "APP_TAF_HTTP_PATH", "APP_UC_CREDENTIAL_NAME", "APP_DOWNSTREAM_DB_ENDPOINT",
              "DATABRICKS_HOST", "DATABRICKS_TOKEN", "DATABRICKS_CLIENT_ID", "DATABRICKS_CLIENT_SECRET", "APP_TAF_ENVIRONMENT", "APP_TAF_NOTEBOOK_DIR"):
        monkeypatch.delenv(k, raising=False)
    dbx.config.cache_clear()
    yield
    dbx.config.cache_clear()


def test_placeholders_degrade_to_dev(monkeypatch):
    monkeypatch.setenv("APP_TAF_CATALOG", "__TAF_CATALOG__")
    monkeypatch.setenv("APP_TAF_HTTP_PATH", "__TAF_HTTP_PATH__")
    cfg = dbx.config()
    assert cfg.environment == "dev" and cfg.catalog == "taf_dev" and cfg.http_path is None
    assert "catalog" in cfg.defaults_applied and "http_path" not in cfg.public()
    assert cfg.configured is False


def test_configured_needs_host_and_credentials(monkeypatch):
    monkeypatch.setenv("DATABRICKS_HOST", "https://adb-dev-1.azuredatabricks.net")
    assert dbx.config().configured is False
    dbx.config.cache_clear()
    monkeypatch.setenv("DATABRICKS_TOKEN", "x")
    assert dbx.config().configured is True


def test_env_detection_order(monkeypatch):
    monkeypatch.setenv("DATABRICKS_HOST", "https://adb-prd-123.azuredatabricks.net")
    monkeypatch.setenv("APP_DOWNSTREAM_DB_ENDPOINT", "pg-stg.example")
    assert dbx.detect_environment() == "stg"
    monkeypatch.setenv("APP_UC_CREDENTIAL_NAME", "cred_tst_taf")
    assert dbx.detect_environment() == "tst"


def test_bad_catalog_identifier_rejected(monkeypatch):
    monkeypatch.setenv("APP_TAF_CATALOG", "x; DROP")
    with pytest.raises(ValueError):
        dbx.config()


def test_scenario_status_rules():
    assert sc.evaluate("find", [], None) == sc.PASS
    assert sc.evaluate("find", [{"a": 1}], None) == sc.FAIL
    assert sc.evaluate("summary", [], None) == sc.NO_DATA
    assert sc.evaluate("summary", [{"a": 1}], None) == sc.PASS
    assert sc.evaluate("find", None, RuntimeError("x")) == sc.ERROR


def test_every_builtin_has_caveat_and_both_forms_render():
    for s in sc.BUILTIN_SCENARIOS:
        assert s.caveat
        pg = s.render(25, 12)
        assert "{" not in pg and "taf_result" in pg or "taf_run" in pg
        if s.sql_databricks:
            d = s.render(25, 12, databricks=True, catalog="taf_dev", schema="raw")
            assert "{" not in d and "taf_dev" in d


def test_extra_scenarios_validated(tmp_path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps([{"scenario_id": "S1", "scenario": "s", "kind": "find", "sql": "SELECT 1 FROM taf_run", "caveat": "c"}]))
    assert any(s.scenario_id == "S1" for s in sc.load_scenarios(str(p)))
    for bad in ({"caveat": ""}, {"sql": "DELETE FROM t"}, {"sql": "SELECT 1; DROP TABLE t"}):
        p.write_text(json.dumps([{"scenario_id": "S2", "scenario": "s", "kind": "find", "sql": "SELECT 1", "caveat": "c", **bad}]))
        with pytest.raises(ValueError):
            sc.load_scenarios(str(p))


CASE = {"test_id": "T1", "check_id": "T1", "test_type": "COLUMN", "assertion_name": "not_null", "target_table": "SILVER.ORDERS",
        "target_column": "ORDER_ID", "date_column": "LOAD_DATE", "tenant_column": None, "severity": "High", "is_active": True, "suite": "TAF"}


def test_compile_full_and_date_range():
    sql, applied, skipped = local.compile_case(CASE, L.ExecuteRequest.from_dict({}))
    assert sql == "SELECT * FROM SILVER.ORDERS WHERE ORDER_ID IS NULL" and applied == "FULL" and skipped is None
    r = L.ExecuteRequest.from_dict({"filter_mode": "DATE_RANGE", "filter_start_date": "2026-11-01", "filter_end_date": "2026-11-05"})
    sql, applied, _ = local.compile_case(CASE, r)
    assert "LOAD_DATE BETWEEN '2026-11-01'::DATE AND '2026-11-05'::DATE" in sql and applied.startswith("DATE_RANGE")


def test_cdf_uses_snowflake_changes():
    r = L.ExecuteRequest.from_dict({"filter_mode": "CDF_RANGE", "date_source": "CDF", "filter_start_date": "2026-11-01", "filter_end_date": "2026-11-02"})
    sql, applied, _ = local.compile_case(CASE, r)
    assert "CHANGES(INFORMATION => DEFAULT)" in sql and applied.startswith("CHANGES")


def test_missing_filter_columns_recorded_as_skips():
    r = L.ExecuteRequest.from_dict({"filter_mode": "SINGLE_DATE", "filter_start_date": "2026-11-01", "filter_tenant_code": "ACME"})
    _, _, skipped = local.compile_case({**CASE, "date_column": None}, r)
    assert "no date column" in skipped and "no tenant column" in skipped
    sql_case = {**CASE, "test_type": "SQL", "sql_expression": "SELECT * FROM GOLD.X WHERE v < 0"}
    sql, applied, skipped = local.compile_case(sql_case, L.ExecuteRequest.from_dict({"filter_mode": "SINGLE_DATE", "filter_start_date": "2026-11-01"}))
    assert applied == "FULL" and "unscoped SQL case" in skipped


def test_run_case_statuses_and_determinism():
    req = L.ExecuteRequest.from_dict({})
    assert local.run_case({**CASE, "is_active": False}, req, 1)["status"] == "Not_Run"
    assert local.run_case({**CASE, "test_type": "MANUAL"}, req, 1)["status"] == "Manual"
    a, b = local.run_case(CASE, req, 3), local.run_case(CASE, req, 3)
    assert a["status"] == b["status"] and a["violation_count"] == b["violation_count"]
    assert a["status"] in L.STATUSES and a["executed_sql"].startswith("SELECT COUNT(*)")


def test_every_seed_case_compiles():
    req = L.ExecuteRequest.from_dict({"filter_mode": "INCREMENTAL"})
    rows = taf_rows()
    assert len(rows) == 32
    for c in rows:
        local.compile_case(c, req)
