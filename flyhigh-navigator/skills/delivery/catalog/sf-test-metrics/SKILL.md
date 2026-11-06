---
name: "sf-test-metrics"
description: "Check each certified KPI in the semantic view against an independent base-table query, so the semantic layer returns the legacy numbers. Delivery skill /test-metrics for the assurance stage; emits Snowflake-ready artefacts for human review."
---

# Test semantic metrics (/test-metrics)

**Stage:** assurance · **Agent:** Semantic Tester · **Human gate:** Semantic tester evidence signed by the BI lead

Check each certified KPI in the semantic view against an independent base-table query, so the semantic layer returns the legacy numbers.

## When to use

Use this skill when the delivery pod reaches the assurance stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `view` | Semantic view | text |
| `cases` | Cases (metric | dimension | base SQL returning dimension, value) | lines |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/test-metrics` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Pull formulas from the KPI library.
2. Run metric_tests.sql; mismatches block publishing the semantic view.

## Snowflake features used

- SEMANTIC_VIEW() query clause
- Cortex Analyst consumes the same view

## Outputs

- `metric_tests.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
