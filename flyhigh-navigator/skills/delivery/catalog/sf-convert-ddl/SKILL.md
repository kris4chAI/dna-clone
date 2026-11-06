---
name: "sf-convert-ddl"
description: "Translate Oracle DDL (tables, sequences, indexes) to Snowflake: type mapping, storage clauses removed, constraints kept as informational, with a warning per manual decision. Delivery skill /convert-ddl for the foundation stage; emits Snowflake-ready artefacts for human review."
---

# Convert legacy DDL (/convert-ddl)

**Stage:** foundation · **Agent:** DDL Converter · **Human gate:** DDL converter output is peer-reviewed; parity proven later by /reconcile

Translate Oracle DDL (tables, sequences, indexes) to Snowflake: type mapping, storage clauses removed, constraints kept as informational, with a warning per manual decision.

## When to use

Use this skill when the delivery pod reaches the foundation stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `ddl` | Oracle DDL | textarea |
| `target` | Target database.schema (replaces the Oracle owner) | text |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/convert-ddl` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Paste DDL or point at an extract from /discover.
2. Review every warning; numbers without precision default to NUMBER(38,10).
3. Use SnowConvert AI (Snowflake AIM) for full-estate conversion; use this skill for targeted objects and fixes.
4. Hand the output to /gen-migration.

## Snowflake features used

- Snowflake data types
- Informational constraints
- Sequences / IDENTITY
- SnowConvert AI for full estates

## Outputs

- `converted.sql`
- `warnings.md`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
