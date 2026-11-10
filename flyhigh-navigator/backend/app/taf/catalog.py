"""FlyHigh's seed TAF suite: data checks on the Snowflake lakehouse, tagged to the lakehouse test map.

TAF cases are authored in the framework's workbook and YAML (requirement groups, column and template
assertions, SQL assertions). EXTERNAL rows stand for a client's existing test suite run alongside it:
one generated query can cover several scenarios, so they share a check_id.
"""

# test_id, type, severity, group, req_id, title, table, column, date_col, tenant_col, assertion/template, params, sql, expected, lakehouse type
TAF = [
    ("TAF-ING-001", "COLUMN", "High", "Ingestion", "REQ-ING-01", "WMS order keys are never null", "BRONZE.WMS_ORDERS", "ORDER_ID", "LOAD_DATE", "CUSTOMER_CODE", "not_null", {}, None, "0 nulls", "L2.1"),
    ("TAF-ING-002", "COLUMN", "High", "Ingestion", "REQ-ING-01", "WMS order keys are unique per load", "BRONZE.WMS_ORDERS", "ORDER_ID", "LOAD_DATE", "CUSTOMER_CODE", "unique", {}, None, "0 duplicates", "L2.4"),
    ("TAF-ING-003", "TEMPLATE", "High", "Ingestion", "REQ-ING-02", "Bronze WMS orders match the source extract row count", "BRONZE.WMS_ORDERS", None, "LOAD_DATE", None, "row_count_match", {"source_table": "LEGACY.ODI_WMS_ORDERS", "tolerance_pct": 0}, None, "counts equal", "L2.4"),
    ("TAF-ING-004", "TEMPLATE", "Medium", "Ingestion", "REQ-ING-03", "WMS feed lands within its 15-minute SLA", "BRONZE.WMS_ORDERS", None, "LOADED_AT", None, "freshness_sla", {"sla_minutes": 15}, None, "last load within 15 min", "X8.3"),
    ("TAF-ING-005", "SQL", "High", "Ingestion", "REQ-ING-04", "CDC applies every delete from the source", "SILVER.ORDERS", None, "LOAD_DATE", None, None, None,
     "SELECT s.ORDER_ID FROM LEGACY.ODI_DELETED_ORDERS s JOIN SILVER.ORDERS o ON o.ORDER_ID = s.ORDER_ID WHERE {filter}", "deleted orders absent", "L2.2"),
    ("TAF-ING-006", "SQL", "Medium", "Ingestion", "REQ-ING-05", "Streaming shipment events arrive without gaps", "BRONZE.TMS_EVENTS", None, "EVENT_DATE", None, None, None,
     "SELECT SHIPMENT_ID FROM (SELECT SHIPMENT_ID, EVENT_SEQ, LAG(EVENT_SEQ) OVER (PARTITION BY SHIPMENT_ID ORDER BY EVENT_SEQ) AS PREV FROM BRONZE.TMS_EVENTS WHERE {filter}) WHERE EVENT_SEQ - PREV > 1",
     "no sequence gaps", "L2.3"),
    ("TAF-CORE-001", "TEMPLATE", "High", "Lakehouse core", "REQ-CORE-01", "Silver orders reconcile to Bronze after quarantine", "SILVER.ORDERS", None, "LOAD_DATE", None, "row_count_match", {"source_table": "BRONZE.WMS_ORDERS", "tolerance_pct": 0.5}, None, "within 0.5%", "L3.1"),
    ("TAF-CORE-002", "TEMPLATE", "High", "Lakehouse core", "REQ-CORE-01", "Gold shipment value sums to Silver", "GOLD.FCT_SHIPMENT", None, "SHIP_DATE", "CUSTOMER_KEY", "sum_match", {"source_table": "SILVER.SHIPMENTS", "measure": "FREIGHT_COST", "tolerance_pct": 0}, None, "sums equal", "L3.1"),
    ("TAF-CORE-003", "COLUMN", "High", "Lakehouse core", "REQ-CORE-02", "On-time flag only takes Y or N", "GOLD.FCT_SHIPMENT", "ON_TIME_FLAG", "SHIP_DATE", "CUSTOMER_KEY", "accepted_values", {"values": ["Y", "N"]}, None, "only Y/N", "L3.2"),
    ("TAF-CORE-004", "COLUMN", "Medium", "Lakehouse core", "REQ-CORE-02", "Units shipped are within 0–100 000", "GOLD.FCT_SHIPMENT", "UNITS", "SHIP_DATE", "CUSTOMER_KEY", "range", {"min": 0, "max": 100000}, None, "all in range", "L3.2"),
    ("TAF-CORE-005", "SQL", "High", "Lakehouse core", "REQ-CORE-03", "Customer SCD2 keeps one current row per customer", "SILVER.DIM_CUSTOMER", None, None, None, None, None,
     "SELECT CUSTOMER_ID FROM SILVER.DIM_CUSTOMER WHERE IS_CURRENT GROUP BY CUSTOMER_ID HAVING COUNT(*) <> 1", "exactly one current row", "L3.3"),
    ("TAF-CORE-006", "TEMPLATE", "High", "Lakehouse core", "REQ-CORE-04", "Every shipment has a known customer", "GOLD.FCT_SHIPMENT", "CUSTOMER_KEY", "SHIP_DATE", "CUSTOMER_KEY", "referential_integrity", {"parent_table": "GOLD.DIM_CUSTOMER", "parent_column": "CUSTOMER_KEY"}, None, "no orphans", "L3.2"),
    ("TAF-CORE-007", "COLUMN", "Medium", "Lakehouse core", "REQ-CORE-05", "Inventory snapshot is fresh (under 24 h)", "GOLD.FCT_INVENTORY_SNAPSHOT", "SNAPSHOT_TS", None, None, "max_age_hours", {"hours": 24}, None, "latest within 24 h", "L3.4"),
    ("TAF-CORE-008", "COLUMN", "Low", "Lakehouse core", "REQ-CORE-06", "Site codes follow the three-letter standard", "GOLD.DIM_SITE", "SITE_CODE", None, None, "regex", {"pattern": "^[A-Z]{3}$"}, None, "all match", "X7.5"),
    ("TAF-SEM-001", "SQL", "High", "Semantics", "REQ-SEM-01", "OTIF in the semantic view equals the golden query", "SEMANTIC.SV_KPI_CERTIFIED", None, "SHIP_DATE", None, None, None,
     "SELECT * FROM (SELECT ROUND(100 * AVG(IFF(ON_TIME_FLAG = 'Y' AND IN_FULL_FLAG = 'Y', 1, 0)), 2) AS GOLDEN FROM GOLD.FCT_SHIPMENT WHERE {filter}) g, (SELECT OTIF_PCT FROM SEMANTIC.SV_KPI_CERTIFIED) s WHERE ABS(g.GOLDEN - s.OTIF_PCT) > 0.1",
     "within 0.1 pt", "L4.2"),
    ("TAF-SEM-002", "SQL", "High", "Semantics", "REQ-SEM-02", "Fill rate matches the legacy OAC report", "SEMANTIC.SV_KPI_CERTIFIED", None, None, None, None, None,
     "SELECT * FROM LEGACY.OAC_FILL_RATE l JOIN SEMANTIC.SV_KPI_CERTIFIED s ON s.SITE_CODE = l.SITE_CODE WHERE ABS(l.FILL_RATE - s.FILL_RATE_PCT) > 0.1",
     "parity within 0.1 pt", "L4.1"),
    ("TAF-SEC-001", "SQL", "High", "Security", "REQ-SEC-01", "Customer role sees only its own shipments", "GOLD.FCT_SHIPMENT", None, None, None, None, None,
     "SELECT * FROM GOLD.FCT_SHIPMENT WHERE CUSTOMER_KEY <> (SELECT CUSTOMER_KEY FROM GOVERNANCE.TEST_USER_CUSTOMER WHERE ROLE_NAME = CURRENT_ROLE())",
     "0 foreign rows", "L6.2"),
    ("TAF-SEC-002", "SQL", "High", "Security", "REQ-SEC-02", "Carrier rates are masked for non-finance roles", "GOLD.FCT_SHIPMENT", "CARRIER_RATE", None, None, None, None,
     "SELECT CARRIER_RATE FROM GOLD.FCT_SHIPMENT WHERE CURRENT_ROLE() <> 'FINANCE_ANALYST' AND CARRIER_RATE IS NOT NULL AND CARRIER_RATE::STRING <> '***MASKED***' LIMIT 100",
     "masked", "X7.2"),
    ("TAF-SEC-003", "SQL", "Medium", "Security", "REQ-SEC-03", "Every sensitive column carries a classification tag", "GOVERNANCE.TAG_REFERENCES", None, None, None, None, None,
     "SELECT c.TABLE_NAME, c.COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS c LEFT JOIN SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES t ON t.COLUMN_NAME = c.COLUMN_NAME AND t.OBJECT_NAME = c.TABLE_NAME WHERE c.COLUMN_NAME IN ('EMAIL', 'CARRIER_RATE', 'SSN_LAST4') AND t.TAG_NAME IS NULL",
     "all tagged", "X7.1"),
    ("TAF-OPS-001", "SQL", "Medium", "Operations", "REQ-OPS-01", "No warehouse is over its monthly credit budget", "SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY", None, None, None, None, None,
     "SELECT WAREHOUSE_NAME, SUM(CREDITS_USED) AS CREDITS FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY m JOIN GOVERNANCE.WAREHOUSE_BUDGET b USING (WAREHOUSE_NAME) WHERE START_TIME >= DATE_TRUNC('month', CURRENT_DATE()) GROUP BY WAREHOUSE_NAME, b.MONTHLY_CREDITS HAVING SUM(CREDITS_USED) > b.MONTHLY_CREDITS",
     "within budget", "X8.5"),
    ("TAF-OPS-002", "SQL", "Medium", "Operations", "REQ-OPS-02", "No failed tasks in the last 24 hours", "INFORMATION_SCHEMA.TASK_HISTORY", None, None, None, None, None,
     "SELECT NAME, ERROR_MESSAGE FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(SCHEDULED_TIME_RANGE_START => DATEADD(hour, -24, CURRENT_TIMESTAMP()))) WHERE STATE = 'FAILED'",
     "0 failed tasks", "X8.1"),
    ("TAF-MAN-001", "MANUAL", "Medium", "UAT", "REQ-UAT-01", "Business sign-off on the warehouse operations dashboard", "TABLEAU.WAREHOUSE_OPS", None, None, None, None, None, None, "signed", "L6.4"),
]

EXTERNAL = [  # one query (check_id) can cover several scenarios
    ("EXT-001", "Sheet 1 · Orders", "Completeness", "P1", "Full", "Order header count matches ODI staging", "CHK-A", "L2.4"),
    ("EXT-002", "Sheet 1 · Orders", "Completeness", "P1", "Full", "Order line count matches ODI staging", "CHK-A", "L2.4"),
    ("EXT-003", "Sheet 1 · Orders", "Accuracy", "P2", "Incremental", "Order amount totals match per day", "CHK-B", "L3.1"),
    ("EXT-004", "Sheet 2 · Shipments", "Accuracy", "P1", "Incremental", "Freight cost totals match per carrier", "CHK-C", "L3.1"),
    ("EXT-005", "Sheet 2 · Shipments", "Accuracy", "P2", "Incremental", "Delivered date never precedes ship date", "CHK-D", "L3.2"),
    ("EXT-006", "Sheet 2 · Shipments", "Validity", "P3", "Full", "Carrier codes exist in the carrier master", "CHK-E", "X7.5"),
    ("EXT-007", "Sheet 3 · Inventory", "Timeliness", "P2", "Full", "Inventory snapshot loaded before 06:00", "CHK-F", "X8.3"),
    ("EXT-008", "Sheet 3 · Inventory", "Accuracy", "P2", "Full", "On-hand units match the WMS snapshot", "CHK-G", "L3.1"),
    ("EXT-009", "Sheet 3 · Inventory", "Accuracy", "P2", "Full", "Allocated units never exceed on-hand", "CHK-G", "L3.2"),
    ("EXT-010", "Sheet 4 · HR", "Privacy", "P1", "Full", "Employee emails are masked in reporting views", "CHK-H", "X7.2"),
]


def taf_rows():
    out = []
    for (tid, typ, sev, grp, rid, title, tbl, col, dcol, tcol, a, params, sql, exp, lh) in TAF:
        out.append({"test_id": tid, "suite": "TAF", "check_id": tid, "test_type": typ, "severity": sev, "requirement_group": grp,
                    "requirement_id": rid, "requirement_title": title, "sheet_name": grp, "functional_category": grp,
                    "load_type": "Incremental" if dcol else "Full", "target_table": tbl, "target_column": col, "date_column": dcol,
                    "tenant_column": tcol, "assertion_name": a if typ == "COLUMN" else None, "assertion_params": params if typ == "COLUMN" else None,
                    "template_name": a if typ == "TEMPLATE" else None, "template_params": params if typ == "TEMPLATE" else None,
                    "sql_expression": sql, "expected_result": exp, "explanation": title, "owner": "Testing lead",
                    "source_ref": f"cases/{grp.lower().replace(' ', '_')}.yaml#{tid}", "lakehouse_type": lh})
    for (tid, sheet, cat, pri, load, scen, chk, lh) in EXTERNAL:
        sev = "High" if pri == "P1" else "Low" if pri == "P3" else "Medium"
        out.append({"test_id": tid, "suite": "EXTERNAL", "check_id": chk, "test_type": "SQL", "severity": sev, "requirement_group": cat,
                    "requirement_id": None, "requirement_title": scen, "sheet_name": sheet, "functional_category": cat, "load_type": load,
                    "target_table": "CLIENT_SUITE." + chk.replace("-", "_"), "target_column": None, "date_column": None, "tenant_column": None,
                    "assertion_name": None, "assertion_params": None, "template_name": None, "template_params": None,
                    "sql_expression": f"SELECT * FROM CLIENT_SUITE.{chk.replace('-', '_')}_FAILURES", "expected_result": "0 failures",
                    "explanation": scen, "owner": "Client QA", "source_ref": f"external_suite.xlsx!{sheet}", "lakehouse_type": lh})
    return out
