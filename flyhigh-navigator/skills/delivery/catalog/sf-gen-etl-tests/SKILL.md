---
name: "sf-gen-etl-tests"
description: "Check converted mappings against legacy output: row counts by business date, transformation rules recomputed from source, and lookup integrity. Delivery skill /gen-etl-tests for the assurance stage; emits Snowflake-ready artefacts for human review."
---

# Generate ETL tests (/gen-etl-tests)

**Stage:** assurance · **Agent:** ETL Test Agent · **Human gate:** QA lead reviews each failure; evidence kept per wave

Check converted mappings against legacy output: row counts by business date, transformation rules recomputed from source, and lookup integrity.

## When to use

Use this skill when the delivery pod reaches the assurance stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `target` | Target table | text |
| `source` | Source table (landed legacy output) | text |
| `key` | Key | text |
| `date_col` | Business date column | text |
| `rules` | Rules (column = expected expression over source alias s) | lines |
| `lookups` | Lookups (column | dimension.key) | lines |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/gen-etl-tests` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Land legacy output for the same window.
2. Run etl_tests.sql; each block must return zero rows.
3. Commit as dbt singular tests for CI.

## Snowflake features used

- Set-based assertions
- MINUS comparisons
- dbt singular tests

## Outputs

- `etl_tests.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
