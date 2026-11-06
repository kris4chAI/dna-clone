---
name: "sf-tune-warehouse"
description: "Diagnose a warehouse from ACCOUNT_USAGE (queueing, spill, credits) and emit sizing, multi-cluster, auto-suspend, query acceleration and resource-monitor settings. Delivery skill /tune-warehouse for the assurance stage; emits Snowflake-ready artefacts for human review."
---

# Tune warehouse (/tune-warehouse)

**Stage:** assurance · **Agent:** Performance Agent · **Human gate:** Platform owner approves sizing and credit quotas

Diagnose a warehouse from ACCOUNT_USAGE (queueing, spill, credits) and emit sizing, multi-cluster, auto-suspend, query acceleration and resource-monitor settings.

## When to use

Use this skill when the delivery pod reaches the assurance stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `warehouse` | Warehouse | text |
| `size` | Current size | choice |
| `avg_queued` | Avg queued load (from diagnosis, 0 if unknown) | number |
| `spill_gb` | Remote spill GB / day | number |
| `monthly_credits` | Monthly credit quota | number |
| `users_peak` | Peak concurrent users | number |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/tune-warehouse` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Run diagnose.sql and enter the figures.
2. Apply tuning.sql in a change window; re-run /load-test.
3. Keep the resource monitor on every warehouse.

## Snowflake features used

- WAREHOUSE_LOAD_HISTORY / WAREHOUSE_METERING_HISTORY
- Multi-cluster + scaling policy
- Query Acceleration Service
- Resource monitors
- Search optimization

## Outputs

- `diagnose.sql`
- `tuning.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
