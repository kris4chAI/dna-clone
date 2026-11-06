---
name: "sf-map-zones"
description: "Generate the zone model (database per environment and layer, schema per domain) with retention and lifecycle rules from the standard. Delivery skill /map-zones for the foundation stage; emits Snowflake-ready artefacts for human review."
---

# Map data layers and zones (/map-zones)

**Stage:** foundation · **Agent:** Zone Mapper · **Human gate:** Platform engineer reviews the zone model in a PR

Generate the zone model (database per environment and layer, schema per domain) with retention and lifecycle rules from the standard.

## When to use

Use this skill when the delivery pod reaches the foundation stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `prefix` | Program prefix | text |
| `envs` | Environments (one per line) | lines |
| `layers` | Layers (name | transient | retention days in PRD) | lines |
| `domains` | Domains / schemas (one per line) | lines |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/map-zones` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Agree environments, layers and domains with the platform standard.
2. Generate zones.yaml and review naming.
3. Pass the same inputs to /gen-zone-ddl.

## Snowflake features used

- Databases and managed-access schemas
- DATA_RETENTION_TIME_IN_DAYS
- Transient tables

## Outputs

- `zones.yaml`
- `zones.md`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
