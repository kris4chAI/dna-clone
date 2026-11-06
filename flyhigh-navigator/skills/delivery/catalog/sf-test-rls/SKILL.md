---
name: "sf-test-rls"
description: "Prove each persona sees exactly its rows: simulate roles with POLICY_CONTEXT, compare visible counts with expectations and check masked columns. Delivery skill /test-rls for the assurance stage; emits Snowflake-ready artefacts for human review."
---

# Test row-level security (/test-rls)

**Stage:** assurance · **Agent:** BI Comparator · **Human gate:** Data owner signs the persona visibility matrix

Prove each persona sees exactly its rows: simulate roles with POLICY_CONTEXT, compare visible counts with expectations and check masked columns.

## When to use

Use this skill when the delivery pod reaches the assurance stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `table` | Protected table | text |
| `column` | Entitlement column | text |
| `cases` | Cases (role | expected visible values comma, or *) | lines |
| `masked` | Masked column to check (optional) | text |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/test-rls` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Run as a role allowed to use POLICY_CONTEXT (policy admin).
2. Every 'FAIL' row is a defect; re-run after each policy change.

## Snowflake features used

- EXECUTE USING POLICY_CONTEXT
- Row access and masking policies

## Outputs

- `rls_tests.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
