---
name: "sf-convert-procs"
description: "Translate an Oracle PL/SQL procedure into a Snowflake Scripting stored procedure skeleton: signature, declarations, common functions, exceptions, with TODOs for constructs that need judgement. Delivery skill /convert-procs for the migration stage; emits Snowflake-ready artefacts for human review."
---

# Convert PL/SQL procedures (/convert-procs)

**Stage:** migration · **Agent:** Code Converter agent · **Human gate:** Code converter output peer-reviewed; parity proven by reconciliation, not by the converter

Translate an Oracle PL/SQL procedure into a Snowflake Scripting stored procedure skeleton: signature, declarations, common functions, exceptions, with TODOs for constructs that need judgement.

## When to use

Use this skill when the delivery pod reaches the migration stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `plsql` | PL/SQL source | textarea |
| `target_schema` | Target schema | text |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/convert-procs` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Prefer SnowConvert AI for bulk conversion; use this skill for single procedures and review.
2. Resolve every TODO; set-based rewrites beat row loops.
3. Prove parity with /gen-etl-tests and /reconcile.

## Snowflake features used

- Snowflake Scripting (LANGUAGE SQL)
- EXECUTE IMMEDIATE
- RESULTSET / cursors
- SnowConvert AI for full estates

## Outputs

- `p_load_labor.sql`
- `todo.md`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
