---
name: "sf-gen-zone-ddl"
description: "Emit idempotent Snowflake DDL and the equivalent Terraform for the zone model, with managed-access schemas, retention and a sandbox cleanup task. Delivery skill /gen-zone-ddl for the foundation stage; emits Snowflake-ready artefacts for human review."
---

# Generate zone DDL (/gen-zone-ddl)

**Stage:** foundation · **Agent:** Zone Mapper · **Human gate:** Peer review gate: no DDL reaches STG or PRD without an approved PR

Emit idempotent Snowflake DDL and the equivalent Terraform for the zone model, with managed-access schemas, retention and a sandbox cleanup task.

## When to use

Use this skill when the delivery pod reaches the foundation stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `prefix` | Program prefix | text |
| `envs` | Environments (one per line) | lines |
| `layers` | Layers (name | transient | retention days in PRD) | lines |
| `domains` | Domains / schemas (one per line) | lines |
| `owner_role` | Owning role | text |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/gen-zone-ddl` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Run with the same inputs as /map-zones.
2. Review zones.sql; apply to DEV first with snow sql.
3. Commit main.tf if the team manages Snowflake with Terraform instead.

## Snowflake features used

- CREATE DATABASE / SCHEMA ... WITH MANAGED ACCESS
- Object tags
- Tasks
- Terraform snowflake provider

## Outputs

- `zones.sql`
- `main.tf`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
