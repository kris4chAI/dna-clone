---
name: "sf-gen-scim"
description: "Create the SCIM security integration and provisioner role for Okta or Microsoft Entra ID, and the token for the IdP app. Delivery skill /gen-scim for the foundation stage; emits Snowflake-ready artefacts for human review."
---

# Generate SCIM provisioning (/gen-scim)

**Stage:** foundation · **Agent:** Identity Mapper · **Human gate:** Account admin and identity owner approve; token stored in the vault, never in the repo

Create the SCIM security integration and provisioner role for Okta or Microsoft Entra ID, and the token for the IdP app.

## When to use

Use this skill when the delivery pod reaches the foundation stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `idp` | Identity provider | choice |
| `network_policy` | Network policy for the SCIM endpoint (optional) | text |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/gen-scim` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Run as ACCOUNTADMIN after approval.
2. Generate the token and paste it into the IdP provisioning app (valid 6 months).
3. Set a reminder to rotate the token.

## Snowflake features used

- CREATE SECURITY INTEGRATION TYPE = SCIM
- SYSTEM$GENERATE_SCIM_ACCESS_TOKEN

## Outputs

- `scim.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
