---
name: "sf-discover"
description: "Profile the legacy Oracle estate and the Snowflake account: objects, sizes, usage, lineage and report consumers, ready for wave planning. Delivery skill /discover for the discover stage; emits Snowflake-ready artefacts for human review."
---

# Estate discovery (/discover)

**Stage:** discover · **Agent:** Estate Analyzer agent · **Human gate:** Migration lead reviews the inventory before waves are planned

Profile the legacy Oracle estate and the Snowflake account: objects, sizes, usage, lineage and report consumers, ready for wave planning.

## When to use

Use this skill when the delivery pod reaches the discover stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `schemas` | Legacy Oracle schemas (one per line) | lines |
| `days` | Usage window (days) | number |
| `database` | Snowflake database to profile | text |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/discover` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Run oracle_inventory.sql on the legacy database and export the result to inventory.csv.
2. Run snowflake_profile.sql to see what has landed and who reads it.
3. Feed inventory.csv to /plan-waves.

## Snowflake features used

- ACCOUNT_USAGE.TABLES
- ACCOUNT_USAGE.ACCESS_HISTORY (lineage)
- ACCOUNT_USAGE.QUERY_HISTORY

## Outputs

- `oracle_inventory.sql`
- `snowflake_profile.sql`
- `inventory_template.csv`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
