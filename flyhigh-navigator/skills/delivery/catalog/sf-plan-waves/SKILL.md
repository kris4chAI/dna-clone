---
name: "sf-plan-waves"
description: "Order objects into dependency-safe migration waves (topological sort) with a size cap per wave and complexity scoring. Delivery skill /plan-waves for the discover stage; emits Snowflake-ready artefacts for human review."
---

# Plan migration waves (/plan-waves)

**Stage:** discover · **Agent:** Estate Analyzer agent · **Human gate:** Migration lead signs the wave plan

Order objects into dependency-safe migration waves (topological sort) with a size cap per wave and complexity scoring.

## When to use

Use this skill when the delivery pod reaches the discover stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `inventory` | Inventory CSV (object,type,depends_on,complexity,usage) | table |
| `max_per_wave` | Max objects per wave | number |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/plan-waves` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Load the inventory from /discover.
2. Run the skill; review cycles and high-complexity objects.
3. Agree the wave plan with the migration lead.

## Snowflake features used

- Wave plan drives Snowflake AIM and schemachange folders

## Outputs

- `waves.yaml`
- `wave_plan.md`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
