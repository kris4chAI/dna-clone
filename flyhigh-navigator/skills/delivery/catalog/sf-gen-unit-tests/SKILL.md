---
name: "sf-gen-unit-tests"
description: "Generate dbt schema tests, plain SQL assertions and Snowflake data metric functions (DMFs) for a table's keys, nulls, accepted values and relationships. Delivery skill /gen-unit-tests for the migration stage; emits Snowflake-ready artefacts for human review."
---

# Generate unit tests (/gen-unit-tests)

**Stage:** migration · **Agent:** Test Generator · **Human gate:** QA lead reviews coverage; failures block promotion

Generate dbt schema tests, plain SQL assertions and Snowflake data metric functions (DMFs) for a table's keys, nulls, accepted values and relationships.

## When to use

Use this skill when the delivery pod reaches the migration stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `table` | Table | text |
| `pk` | Primary key columns (comma) | text |
| `not_null` | Not-null columns (one per line) | lines |
| `accepted` | Accepted values (column | v1,v2) | lines |
| `relationships` | Relationships (column | parent table.column) | lines |
| `freshness_col` | Freshness timestamp column | text |
| `schedule` | DMF schedule | text |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/gen-unit-tests` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Generate from the target model.
2. Run assertions.sql in CI after each deploy (every query must return 0 rows).
3. Apply dmfs.sql to keep monitoring in production.

## Snowflake features used

- Data metric functions (SNOWFLAKE.CORE.NULL_COUNT, DUPLICATE_COUNT, FRESHNESS)
- DATA_METRIC_SCHEDULE
- dbt tests

## Outputs

- `assertions.sql`
- `dmfs.sql`
- `tests/fact_warehouse_task.yml`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
