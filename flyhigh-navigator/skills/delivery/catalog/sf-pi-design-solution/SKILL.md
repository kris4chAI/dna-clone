---
name: "sf-pi-design-solution"
description: "Draft the solution design from an approved PRD: Snowflake architecture (databases, warehouses, roles), interfaces, NFRs and a scope.yaml traceability map to Jira. Delivery skill /pi-design-solution for the design stage; emits Snowflake-ready artefacts for human review."
---

# Design the solution (/pi-design-solution)

**Stage:** design · **Agent:** Solution Design Agent · **Human gate:** G2 · architecture lead approves the design

Draft the solution design from an approved PRD: Snowflake architecture (databases, warehouses, roles), interfaces, NFRs and a scope.yaml traceability map to Jira.

## When to use

Use this skill when the delivery pod reaches the design stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `prd_title` | PRD title | text |
| `requirements` | Requirements (id | text) | lines |
| `components` | Components (name | type | requirements) | lines |
| `project_key` | Jira project key | text |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/pi-design-solution` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Start from the merged PRD.
2. Generate the design and scope.yaml; add ADRs for each decision.
3. Accept, edit or skip the proposed reviewers; run the checklist.

## Snowflake features used

- Database per layer and environment
- Warehouses per workload
- Database roles
- Semantic views

## Outputs

- `solution_design.md`
- `scope.yaml`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
