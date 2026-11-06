---
name: "sf-test-cdc"
description: "Check pipes, streams and tasks: pipe status, load errors, freshness against SLA, late-arriving rows, stale streams and failed task runs. Delivery skill /test-cdc for the assurance stage; emits Snowflake-ready artefacts for human review."
---

# Test CDC and file loads (/test-cdc)

**Stage:** assurance · **Agent:** Pipeline Monitor · **Human gate:** Pipeline monitor results reviewed before UAT

Check pipes, streams and tasks: pipe status, load errors, freshness against SLA, late-arriving rows, stale streams and failed task runs.

## When to use

Use this skill when the delivery pod reaches the assurance stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `pipes` | Pipes (one per line) | lines |
| `tables` | Tables (table | timestamp column | SLA minutes) | lines |
| `schema` | Schema with streams and tasks | text |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/test-cdc` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Run cdc_checks.sql during SIT and keep it as a monitoring query.
2. Convert the freshness block into an alert with /gen-runbook.

## Snowflake features used

- SYSTEM$PIPE_STATUS
- COPY_HISTORY
- SHOW STREAMS (stale)
- TASK_HISTORY

## Outputs

- `cdc_checks.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
