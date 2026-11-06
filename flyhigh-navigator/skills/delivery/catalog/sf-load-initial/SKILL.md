---
name: "sf-load-initial"
description: "Load historical extracts (landed in S3 by DMS or export) with COPY INTO, validate first, and record row counts in a load audit table. Delivery skill /load-initial for the migration stage; emits Snowflake-ready artefacts for human review."
---

# Initial history load (/load-initial)

**Stage:** migration · **Agent:** Migration Runner · **Human gate:** Migration lead confirms counts against the source before reconciliation

Load historical extracts (landed in S3 by DMS or export) with COPY INTO, validate first, and record row counts in a load audit table.

## When to use

Use this skill when the delivery pod reaches the migration stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `stage` | Stage | text |
| `tables` | Tables (target | stage path) | lines |
| `format` | File format | choice |
| `clone_to` | Clone to non-prod database (optional) | text |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/load-initial` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Run the VALIDATION_MODE block first and fix errors.
2. Run the loads, then the audit insert.
3. Clone to STG for testing instead of reloading.

## Snowflake features used

- COPY INTO with VALIDATION_MODE
- Parquet / CSV file formats
- LOAD_HISTORY / COPY_HISTORY
- Zero-copy clone for non-prod

## Outputs

- `load_initial.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
