---
name: "sf-design-rbac"
description: "Design a two-tier role hierarchy: database roles for object access (read, write, own per schema) granted to functional account roles per persona. Delivery skill /design-rbac for the foundation stage; emits Snowflake-ready artefacts for human review."
---

# Design role-based access (/design-rbac)

**Stage:** foundation · **Agent:** RBAC Designer · **Human gate:** Security reviews the role design; access review evidence kept

Design a two-tier role hierarchy: database roles for object access (read, write, own per schema) granted to functional account roles per persona.

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

In the FlyHigh Navigator app: Skills studio → `/design-rbac` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. List personas as functional roles and the schemas each needs.
2. Generate rbac.yaml and the diagram; review least privilege.
3. Feed the same inputs to /gen-grants.

## Snowflake features used

- Database roles
- Functional account roles
- Future grants
- Role hierarchy under SYSADMIN

## Outputs

- `rbac.yaml`
- `rbac.mmd`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
