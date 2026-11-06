---
name: "sf-convert-etl"
description: "Turn an ODI-style mapping spec into a dbt incremental model with sources and tests, plus a Snowflake-native dynamic table alternative. Delivery skill /convert-etl for the migration stage; emits Snowflake-ready artefacts for human review."
---

# Convert ETL mappings (/convert-etl)

**Stage:** migration · **Agent:** Pipeline Converter · **Human gate:** Pipeline converter output reviewed; parity proven by /gen-etl-tests

Turn an ODI-style mapping spec into a dbt incremental model with sources and tests, plus a Snowflake-native dynamic table alternative.

## When to use

Use this skill when the delivery pod reaches the migration stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `model` | Target model name | text |
| `source` | Source (schema.table alias) | text |
| `joins` | Joins (one per line) | lines |
| `columns` | Columns (target = expression) | lines |
| `filter` | Filter | text |
| `unique_key` | Unique key | text |
| `watermark` | Incremental watermark column | text |
| `target_lag` | Dynamic table target lag | text |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/convert-etl` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Describe the mapping (from the ODI repository or the converter).
2. Commit the dbt model and run dbt build in DEV.
3. Pick dbt or the dynamic table per pipeline; do not run both in production.

## Snowflake features used

- dbt-snowflake (incremental, merge)
- Dynamic tables (TARGET_LAG)
- Snowflake-native workflows

## Outputs

- `models/fact_shipment_leg.sql`
- `models/fact_shipment_leg.yml`
- `models/sources.yml`
- `dynamic_table.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
