---
name: "sf-reconcile"
description: "Prove parity between Oracle and Snowflake: counts, measure sums and per-key hashes, with paired queries for both sides and a Snowflake results table. Delivery skill /reconcile for the migration stage; emits Snowflake-ready artefacts for human review."
---

# Reconcile source and target (/reconcile)

**Stage:** migration · **Agent:** Migration Runner · **Human gate:** QA lead signs every variance as fixed or explained before cut-over

Prove parity between Oracle and Snowflake: counts, measure sums and per-key hashes, with paired queries for both sides and a Snowflake results table.

## When to use

Use this skill when the delivery pod reaches the migration stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `pairs` | Pairs (source oracle table | target snowflake table | key | measures comma) | lines |
| `wave` | Wave | text |
| `tolerance` | Measure tolerance (absolute) | number |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/reconcile` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Run oracle_side.sql on the legacy database and load its output into RECON_SOURCE (CSV via stage).
2. Run snowflake_side.sql, then compare.sql.
3. Attach the RECON_RESULT rows as evidence for the wave sign-off.

## Snowflake features used

- HASH_AGG
- MINUS set comparison
- Results table for evidence

## Outputs

- `oracle_side.sql`
- `snowflake_side.sql`
- `compare.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
