---
name: "sf-check-scd"
description: "Validate SCD type 2 dimensions: one current row per key, no overlapping or gapped intervals, valid dates, and facts joined to the version valid at event time. Delivery skill /check-scd for the assurance stage; emits Snowflake-ready artefacts for human review."
---

# Check SCD history (/check-scd)

**Stage:** assurance · **Agent:** DW Validator · **Human gate:** DW validator results reviewed by the QA lead

Validate SCD type 2 dimensions: one current row per key, no overlapping or gapped intervals, valid dates, and facts joined to the version valid at event time.

## When to use

Use this skill when the delivery pod reaches the assurance stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `dimension` | SCD2 dimension | text |
| `natural_key` | Natural key | text |
| `surrogate` | Surrogate key | text |
| `from_col` | Effective from | text |
| `to_col` | Effective to | text |
| `current_col` | Is-current flag | text |
| `fact` | Fact to check (table | fk | event date) | text |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/check-scd` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Run after each load into the dimension.
2. Any rows returned are defects; fix the merge logic, not the data.

## Snowflake features used

- Window functions (LAG / LEAD)
- QUALIFY
- Interval checks

## Outputs

- `scd_checks.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
