---
name: "sf-map-groups"
description: "Map identity-provider groups to Snowflake functional roles for SCIM provisioning, with default roles, warehouses and a validation query. Delivery skill /map-groups for the foundation stage; emits Snowflake-ready artefacts for human review."
---

# Map IdP groups to roles (/map-groups)

**Stage:** foundation · **Agent:** Identity Mapper · **Human gate:** Identity owner confirms the mapping

Map identity-provider groups to Snowflake functional roles for SCIM provisioning, with default roles, warehouses and a validation query.

## When to use

Use this skill when the delivery pod reaches the foundation stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `mapping` | Mapping CSV (idp_group,snowflake_role,default_warehouse) | table |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/map-groups` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Agree group names with the identity team.
2. Provision groups via /gen-scim; SCIM creates a role per group.
3. Apply role_bindings.sql to grant functional roles to the SCIM roles.

## Snowflake features used

- SCIM-provisioned roles
- DEFAULT_ROLE / DEFAULT_WAREHOUSE
- GRANT ROLE

## Outputs

- `group_mapping.yaml`
- `role_bindings.sql`
- `validate.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
