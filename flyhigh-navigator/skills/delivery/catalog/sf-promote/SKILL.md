---
name: "sf-promote"
description: "Promote the same artefacts through environments with GitHub environment approvals, schemachange per environment and post-deploy checks. Delivery skill /promote for the release stage; emits Snowflake-ready artefacts for human review."
---

# Promote dev → stage → prod (/promote)

**Stage:** release · **Agent:** Promotion Agent · **Human gate:** Release manager approves each promotion

Promote the same artefacts through environments with GitHub environment approvals, schemachange per environment and post-deploy checks.

## When to use

Use this skill when the delivery pod reaches the release stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `envs` | Environments in promotion order | lines |
| `prefix` | Database prefix | text |
| `approvers` | Approvers for production | text |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/promote` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Create GitHub environments with required reviewers (STG, PRD).
2. Tag a release; the workflow deploys DEV → STG → PRD with approval at each step.
3. Golden queries must pass before the next environment.

## Snowflake features used

- schemachange per environment
- Snowflake CLI
- Golden queries after deploy

## Outputs

- `.github/workflows/promote.yml`
- `promotion.md`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
