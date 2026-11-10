from datetime import datetime, timezone

import pytest

from app.taf import logic as L


def req(**kw):
    return L.ExecuteRequest.from_dict(kw)


def test_run_id_shape():
    rid = L.new_ui_run_id(datetime(2026, 7, 1, 9, 5, 3, tzinfo=timezone.utc))
    assert rid.startswith("UI20260701_090503_") and len(rid.split("_")[-1]) == 6


@pytest.mark.parametrize("scope,chain", [
    (L.SCOPE_ALL, ["00_Full_Run"]),
    (L.SCOPE_COLUMN, ["02_Load_Test_Catalog", "03_Compile_Plans", "05_Column_Runner"]),
    (L.SCOPE_TEMPLATE, ["02_Load_Test_Catalog", "03_Compile_Plans", "06_Template_Runner"]),
    (L.SCOPE_SQL, ["02_Load_Test_Catalog", "03_Compile_Plans", "07_SQL_Runner"]),
    (L.SCOPE_EXTERNAL, ["External_Suite_Runner"]),
])
def test_chain_mapping(scope, chain):
    out = L.build_chain(scope, "/W/nb")
    assert [t["notebook_path"].split("/")[-1] for t in out] == chain
    assert out[0]["depends_on"] == []
    for prev, cur in zip(out, out[1:]):
        assert cur["depends_on"] == [prev["task_key"]]


def test_reject_latest_load_cdf():
    with pytest.raises(L.ValidationError, match="LATEST_LOAD"):
        req(filter_mode="LATEST_LOAD", date_source="CDF")


@pytest.mark.parametrize("mode,kw", [
    ("SINGLE_DATE", {}), ("DATE_RANGE", {"filter_start_date": "2026-07-01"}),
    ("CDF_RANGE", {"filter_end_date": "2026-07-01"}),
])
def test_reject_date_modes_without_dates(mode, kw):
    with pytest.raises(L.ValidationError):
        req(filter_mode=mode, **kw)


def test_date_range_ok_and_order_checked():
    r = req(filter_mode="DATE_RANGE", filter_start_date="2026-07-01", filter_end_date="2026-07-10")
    assert r.filter_mode == "DATE_RANGE"
    with pytest.raises(L.ValidationError, match="after"):
        req(filter_mode="DATE_RANGE", filter_start_date="2026-07-10", filter_end_date="2026-07-01")
    with pytest.raises(L.ValidationError, match="real date"):
        req(filter_mode="SINGLE_DATE", filter_start_date="2026-02-30")


def test_client_scope_needs_a_scope():
    with pytest.raises(L.ValidationError):
        req(test_scope=L.SCOPE_CLIENT)
    assert req(test_scope=L.SCOPE_CLIENT, filter_tenant_code="TENANT_A")


def test_yes_no_are_strings_and_lookback_empty_by_default():
    r = req(send_report=True, capture_records=False)
    p = L.build_base_parameters(r, run_id="UI1", catalog="c", schema="s", log_file="/l", environment="dev")
    assert p["send_report"] == "yes" and p["capture_records"] == "no"
    assert p["lookback_days"] == ""            # taf_filters applies the default 1
    assert p["triggered_by"] == "ui_manual"
    assert all(isinstance(v, str) for v in p.values())


def test_source_file_must_be_volume_on_databricks():
    with pytest.raises(L.ValidationError, match="Volumes"):
        req(engine="Databricks", source_file_path="/tmp/x.xlsx")
    req(engine="Simulator", source_file_path="/tmp/x.xlsx")  # workbench engines import uploads locally
    p = L.build_base_parameters(req(engine="Databricks", source_file_path="/Volumes/c/s/taf_uploads/x.xlsx"),
                                run_id="r", catalog="c", schema="s", log_file="l", environment="dev")
    assert p["source_file_path"] == p["external_tc_path"] == "/Volumes/c/s/taf_uploads/x.xlsx"


def test_upload_path_sanitised():
    p = L.upload_path("/Volumes/c/s/taf_uploads", "../../my book (v3).xlsx",
                      datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
    assert p == "/Volumes/c/s/taf_uploads/20260102_030405_my_book_v3_.xlsx"
    with pytest.raises(L.ValidationError):
        L.upload_path("/V", "evil.sh")


def test_failure_id():
    assert L.split_failure_id("SQL_001::R20260701_000000") == ("SQL_001", "R20260701_000000")
    for bad in ("x", "a::b::c", "::r", "t::"):
        with pytest.raises(L.ValidationError):
            L.split_failure_id(bad)


def test_tally_and_final_status():
    c = L.tally([{"status": "Pass", "n": 5}, {"status": "Fail", "n": 2}, {"status": "Manual", "n": 1},
                 {"status": "Not_Run", "n": 1}])
    assert c["total_tests"] == 9 and c["pass_count"] == 5 and c["fail_count"] == 2
    assert L.final_manifest_status("SUCCESS", c)[0] == "Partial"
    assert L.final_manifest_status("FAILED", c)[0] == "Error"
    zero = L.tally([{"status": "Not_Run", "n": 3}])
    status, note = L.final_manifest_status("SUCCESS", zero)
    assert status == "Error" and "checks nothing" in note
    assert L.final_manifest_status("SUCCESS", L.tally([{"status": "Pass", "n": 1}]))[0] == "Passed"


def test_engine_validated():
    assert req().engine == "Simulator"
    with pytest.raises(L.ValidationError):
        req(engine="Oracle")
    assert set(L.SCOPE_TYPES) == set(L.TEST_SCOPE_CHAINS)
