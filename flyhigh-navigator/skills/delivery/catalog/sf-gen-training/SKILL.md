---
name: "sf-gen-training"
description: "Build a role-based curriculum with Snowflake hands-on labs, shadow and reverse-shadow weeks and completion checks. Delivery skill /gen-training for the monitor stage; emits Snowflake-ready artefacts for human review."
---

# Role-based training plan (/gen-training)

**Stage:** monitor · **Agent:** Enablement Agent · **Human gate:** Client role owners confirm readiness

Build a role-based curriculum with Snowflake hands-on labs, shadow and reverse-shadow weeks and completion checks.

## When to use

Use this skill when the delivery pod reaches the monitor stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `roles` | Roles (role | modules comma) | lines |
| `weeks` | Shadow weeks / reverse-shadow weeks | text |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/gen-training` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Agree roles and names with the client.
2. Run labs in the SBX environment with cloned data.
3. Track completion before the handover gate.

## Snowflake features used

- Snowsight
- Cortex Analyst
- Semantic views
- Task and alert operations

## Outputs

- `training_plan.md`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
