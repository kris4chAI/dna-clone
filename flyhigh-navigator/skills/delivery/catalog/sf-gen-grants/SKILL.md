---
name: "sf-gen-grants"
description: "Emit database roles, schema and future grants, and functional-role bindings from the RBAC design, plus an access-review query. Delivery skill /gen-grants for the foundation stage; emits Snowflake-ready artefacts for human review."
---

# Generate grants (/gen-grants)

**Stage:** foundation · **Agent:** RBAC Designer · **Human gate:** Security approves grants; access review evidence stored per gate

Emit database roles, schema and future grants, and functional-role bindings from the RBAC design, plus an access-review query.

## When to use

Use this skill when the delivery pod reaches the foundation stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `prefix` | Program prefix | text |
| `env` | Environment | text |
| `layers` | Layers | lines |
| `domains` | Domains / schemas (one per line) | lines |
| `functional` | Functional roles (role | access: layer.schema:level, ...) | lines |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/gen-grants` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Run with the inputs agreed in /design-rbac.
2. Apply grants.sql with SECURITYADMIN after review.
3. Run access_review.sql each quarter and file the output as evidence.

## Snowflake features used

- CREATE DATABASE ROLE
- GRANT ... ON FUTURE TABLES / VIEWS
- GRANT DATABASE ROLE TO ROLE
- SHOW GRANTS

## Outputs

- `grants.sql`
- `access_review.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
