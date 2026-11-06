---
name: "sf-gen-migration"
description: "Wrap reviewed SQL into a versioned schemachange script with a matching rollback note and change-history check. Delivery skill /gen-migration for the foundation stage; emits Snowflake-ready artefacts for human review."
---

# Generate schemachange migration (/gen-migration)

**Stage:** foundation · **Agent:** DDL Converter · **Human gate:** Release manager approves the migration PR

Wrap reviewed SQL into a versioned schemachange script with a matching rollback note and change-history check.

## When to use

Use this skill when the delivery pod reaches the foundation stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `version` | Version | text |
| `description` | Description | text |
| `kind` | Script kind | choice |
| `sql` | Reviewed SQL | textarea |
| `objects` | Objects created or changed (one per line) | lines |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/gen-migration` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Use V scripts for one-off changes, R for views and procedures, A for always-run grants.
2. Commit under migrations/ and let /promote deploy it.
3. Keep rollback.sql with the PR.

## Snowflake features used

- schemachange (versioned V__ / repeatable R__ scripts)
- Time Travel for rollback

## Outputs

- `migrations/V1.3.0__create_fact_warehouse_task.sql`
- `rollback.sql`
- `check_history.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
