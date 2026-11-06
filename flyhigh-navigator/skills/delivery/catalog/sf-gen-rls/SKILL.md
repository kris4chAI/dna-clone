---
name: "sf-gen-rls"
description: "Create an entitlement mapping table and a row access policy so each role sees only its own customers or sites (e.g. the customer portal). Delivery skill /gen-rls for the foundation stage; emits Snowflake-ready artefacts for human review."
---

# Generate row access policies (/gen-rls)

**Stage:** foundation · **Agent:** Policy Author · **Human gate:** Data owner signs off each persona's visible rows

Create an entitlement mapping table and a row access policy so each role sees only its own customers or sites (e.g. the customer portal).

## When to use

Use this skill when the delivery pod reaches the foundation stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `table` | Protected table | text |
| `column` | Entitlement column | text |
| `policy_schema` | Policy schema | text |
| `admin_roles` | Roles that see all rows | lines |
| `entitlements` | Entitlements CSV (role,value) | table |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/gen-rls` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Load entitlements from the source of truth (CRM / contract system).
2. Apply rls.sql; test every persona with /test-rls.
3. Use the same policy on every table carrying the column.

## Snowflake features used

- Row access policies
- Entitlement mapping table
- IS_ROLE_IN_SESSION / CURRENT_ROLE
- POLICY_CONTEXT for testing

## Outputs

- `rls.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
