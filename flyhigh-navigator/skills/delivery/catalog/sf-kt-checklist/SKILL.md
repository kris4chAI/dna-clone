---
name: "sf-kt-checklist"
description: "Handover checklist with ownership transfer SQL so the client's roles own every Snowflake object, plus sign-off steps. Delivery skill /kt-checklist for the monitor stage; emits Snowflake-ready artefacts for human review."
---

# Knowledge transfer and handover (/kt-checklist)

**Stage:** monitor · **Agent:** Enablement Agent · **Human gate:** Formal handover sign-off by the client

Handover checklist with ownership transfer SQL so the client's roles own every Snowflake object, plus sign-off steps.

## When to use

Use this skill when the delivery pod reaches the monitor stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `schemas` | Schemas to hand over | lines |
| `from_role` | Current owner role (vendor) | text |
| `to_role` | New owner role (client) | text |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/kt-checklist` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Walk the checklist in the last two hypercare weeks.
2. Run ownership.sql with SECURITYADMIN.
3. Sign the handover with the client platform owner.

## Snowflake features used

- GRANT OWNERSHIP ... COPY CURRENT GRANTS
- Service user and key handover
- Resource monitor ownership

## Outputs

- `kt_checklist.md`
- `ownership.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
