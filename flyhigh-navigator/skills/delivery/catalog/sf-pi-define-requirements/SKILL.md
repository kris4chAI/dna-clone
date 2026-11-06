---
name: "sf-pi-define-requirements"
description: "Turn one prompt plus clarifying answers into a product requirements document, check the persona and map every data need to a Snowflake object or a logged gap. Delivery skill /pi-define-requirements for the discover stage; emits Snowflake-ready artefacts for human review."
---

# Define requirements (PRD) (/pi-define-requirements)

**Stage:** discover · **Agent:** PRD Agent · **Human gate:** G1 · product owner approves the PRD in a pull request

Turn one prompt plus clarifying answers into a product requirements document, check the persona and map every data need to a Snowflake object or a logged gap.

## When to use

Use this skill when the delivery pod reaches the discover stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `need` | The need in one prompt | textarea |
| `persona` | Persona | text |
| `pain_points` | Pain points (one per line) | lines |
| `outcomes` | Outcomes with numeric targets (outcome | metric | target) | lines |
| `data_needs` | Data needs (one concept per line) | lines |
| `scope_out` | Out of scope | lines |
| `database` | Snowflake database to probe | text |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/pi-define-requirements` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Read the need and persona; ask only for missing outcomes or data needs.
2. Confirm the persona against the persona catalogue; log a gap if it is new.
3. Run catalog_probe.sql in Snowflake to map each data need to existing objects; anything without a match becomes a data gap.
4. Confirm numeric targets with the business owner before raising the PR.

## Snowflake features used

- SNOWFLAKE.ACCOUNT_USAGE.TABLES / COLUMNS (catalog probe)
- Horizon catalog search

## Outputs

- `prd.md`
- `catalog_probe.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
