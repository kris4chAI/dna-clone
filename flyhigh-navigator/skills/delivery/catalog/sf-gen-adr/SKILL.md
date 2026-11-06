---
name: "sf-gen-adr"
description: "Write an ADR (MADR style) with context, options, decision, consequences and the Snowflake features involved. Delivery skill /gen-adr for the monitor stage; emits Snowflake-ready artefacts for human review."
---

# Architecture decision record (/gen-adr)

**Stage:** monitor · **Agent:** Docs Agent · **Human gate:** Architecture lead accepts the ADR

Write an ADR (MADR style) with context, options, decision, consequences and the Snowflake features involved.

## When to use

Use this skill when the delivery pod reaches the monitor stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `number` | ADR number | text |
| `title` | Title | text |
| `context` | Context | textarea |
| `options` | Options (one per line) | lines |
| `decision` | Decision | text |
| `consequences` | Consequences (one per line) | lines |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/gen-adr` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Draft when a decision is taken, not after.
2. Link it from the design and the PR.

## Snowflake features used

- Decision records next to Snowflake code

## Outputs

- `docs/adr/007-use-dynamic-tables-for-near-real-time-silver.md`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
