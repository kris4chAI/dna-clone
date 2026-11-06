---
name: "sf-parallel-run"
description: "Schedule daily parity checks during the parallel run with a task, an alert on variances and exit criteria for cut-over. Delivery skill /parallel-run for the migration stage; emits Snowflake-ready artefacts for human review."
---

# Parallel run (/parallel-run)

**Stage:** migration · **Agent:** Cutover Validator · **Human gate:** Steering committee confirms exit criteria before cut-over

Schedule daily parity checks during the parallel run with a task, an alert on variances and exit criteria for cut-over.

## When to use

Use this skill when the delivery pod reaches the migration stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `days` | Parallel-run length (days) | number |
| `cron` | Daily check time (CRON, UTC) | text |
| `email` | Alert recipient | text |
| `integration` | Email notification integration | text |
| `exit` | Exit criteria (one per line) | lines |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/parallel-run` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Load the Oracle-side numbers daily (from /reconcile).
2. Resume the task and alert after review.
3. Track exit criteria in the cut-over checklist.

## Snowflake features used

- Tasks with CRON schedules
- Alerts + SYSTEM$SEND_EMAIL
- Notification integrations

## Outputs

- `parallel_run.sql`
- `exit_criteria.md`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
