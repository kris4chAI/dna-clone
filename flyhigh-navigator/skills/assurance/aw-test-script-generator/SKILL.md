---
name: aw-test-script-generator
description: "Generate keyword-driven pytest scripts or BDD features for a test case over reusable components (login, navigation, filters, KPI tiles, SQL, legacy comparison, row access, masking, latency, Cortex)."
---

# Test script generator (assurance)

## Framework

- **Applications:** Tableau Cloud dashboards, customer portal, Snowflake data platform, Cortex Analyst.
- **Reusable components (keywords):** Login, NavigateTo, ApplyFilter, ReadKpiTile, RunSql, CompareToLegacy, AssertRowAccess, AssertMasked, MeasureLatency, AskCortex, AssertDenied.
- **Standard suites:** smoke, regression, reconciliation, security, performance.
- **Services:** Snowflake SQL API, Tableau REST API, Jira, GitHub Actions.

## Rules

1. Map each test-case type to its keyword sequence:
   - functional: Login → NavigateTo → ApplyFilter → ReadKpiTile → AssertEquals;
   - data: RunSql → CompareToLegacy → AssertWithinTolerance;
   - security: Login (restricted role) → NavigateTo → AssertRowAccess → AssertMasked;
   - performance: Login → NavigateTo → MeasureLatency;
   - negative: Login (no access) → NavigateTo → AssertDenied.
2. Keywords are implemented once in `keywords.py`; tests only compose them.
3. Mark each test with its type so suites can select it (`pytest -m security`).

## Output

`test_<case>.py` (or `<case>.feature` for BDD) and a `keywords.py` stub.
