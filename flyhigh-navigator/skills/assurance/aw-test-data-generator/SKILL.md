---
name: aw-test-data-generator
description: "Generate synthetic Snowflake test data for valid, boundary, invalid and masked scenarios from a schema file (CREATE TABLE DDL, CSV header) or a data-model entity, with INSERT SQL and data-quality checks."
---

# Test data generator (assurance)

## Inputs

- A schema: `CREATE TABLE` DDL, a CSV header, or an entity from the FlyHigh data model.
- Row count and scenarios.

## Scenarios

| Scenario | What it does |
|---|---|
| valid | Realistic values by column name: keys, dates, amounts, quantities, percentages, flags, names, codes |
| boundary | Zero quantities, 100% ratios, year-end dates, zero amounts |
| invalid | Nulls in non-key columns, negative amounts and quantities, impossible dates, ratios over 100% |
| masked | Sensitive columns (email, rate, cost) replaced with `***MASKED***` |

## Rules

- Values are deterministic for the same schema and row number, so tests are repeatable.
- Load only into a TEST schema; never into production.
- Invalid rows must end up in quarantine; the generated checks count them.

## Output

`test_data.csv` and `load_test_data.sql` (INSERT statements plus the expected data-quality checks).
