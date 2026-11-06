---
name: "sf-gen-runbook"
description: "Write a runbook for a pipeline or warehouse (set up, configure, run, troubleshoot, monitor) with Snowflake diagnostic queries and alerts that email the on-call team. Delivery skill /gen-runbook for the monitor stage; emits Snowflake-ready artefacts for human review."
---

# Runbook with alerts (/gen-runbook)

**Stage:** monitor · **Agent:** Docs Agent · **Human gate:** Platform operations accepts the runbook at handover

Write a runbook for a pipeline or warehouse (set up, configure, run, troubleshoot, monitor) with Snowflake diagnostic queries and alerts that email the on-call team.

## When to use

Use this skill when the delivery pod reaches the monitor stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `component` | Component | text |
| `task` | Task to watch | text |
| `table` | Table + freshness column | text |
| `sla_minutes` | Freshness SLA (minutes) | number |
| `email` | On-call email | text |
| `integration` | Email notification integration | text |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/gen-runbook` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Generate per component at build time.
2. Apply alerts.sql and resume the alerts.
3. Rehearse the troubleshooting steps during hypercare.

## Snowflake features used

- CREATE ALERT
- SYSTEM$SEND_EMAIL
- TASK_HISTORY / COPY_HISTORY / QUERY_HISTORY
- Event tables (optional)

## Outputs

- `runbook.md`
- `alerts.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
