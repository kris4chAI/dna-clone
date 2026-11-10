# Databricks engine: making the test suite toggle reach the next run

The standalone TAF operator app shipped a defect: the Activate/Deactivate toggle wrote to
`taf_test_suite` while execution read `taf_test_catalog.is_enabled`, so
deactivating a case changed nothing.

The assurance workbench persists the toggle in its own store (`taf_case.is_active`) and, on the Databricks engine, writes it through to `taf_test_suite` (verified by re-query). Because
`02_Load_Test_Catalog` rebuilds the catalog partition from the workbook and YAML
on every run, writing through to old catalog partitions would not reach the next
run. The fix therefore lives in the loader: **after loading cases and before the
`DELETE WHERE run_id = … then INSERT`, apply the suite overrides.**

```python
# 02_Load_Test_Catalog - after taf_loader.load_test_cases(...), before writing
inactive = {
    r.test_id
    for r in spark.sql(f"""
        SELECT test_id FROM {catalog}.{raw_schema}.vw_validation_test_suite
        WHERE suite = 'TAF' AND is_active = false
    """).collect()
}
for case in cases:
    if case.test_id in inactive:
        case.is_enabled = False                       # loads as Not_Run - visible, not dropped
        case.notes = ((case.notes or "") + " | deactivated in assurance workbench").strip(" |")
logprint(f"Operator-deactivated cases applied: {len(inactive & {c.test_id for c in cases})}")
```

For the external suite, `External_Suite_Runner` should skip scenarios whose
`test_id` is inactive in `vw_validation_test_suite` with `suite = 'EXTERNAL'` and
record them as `Not_Run`.

Acceptance check: deactivate a case in the workbench (Design > Data checks (TAF)), start a run, confirm that case
appears in Results as `Not_Run` (not missing, not executed).
