---
name: "sf-design-auth"
description: "Design SSO, network rules and policies, password and session policies, and key-pair auth for service users. Delivery skill /design-auth for the foundation stage; emits Snowflake-ready artefacts for human review."
---

# Design authentication and encryption (/design-auth)

**Stage:** foundation · **Agent:** Auth Designer · **Human gate:** Security architect approves; FOR JOINT REVIEW with the client security team

Design SSO, network rules and policies, password and session policies, and key-pair auth for service users.

## When to use

Use this skill when the delivery pod reaches the foundation stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `idp` | IdP | choice |
| `allowed_ips` | Allowed IPv4 ranges (one per line) | lines |
| `service_users` | Service users (one per line) | lines |
| `idle_minutes` | Session idle timeout (minutes) | number |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/design-auth` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Complete the SAML values from the IdP metadata.
2. Apply in DEV, test a login per persona, then STG and PRD.
3. Generate keys for service users with /gen-keypair.

## Snowflake features used

- SAML2 security integration
- Network rules + network policies
- Authentication / password / session policies
- Service users (TYPE = SERVICE)

## Outputs

- `auth.sql`
- `auth_design.md`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
