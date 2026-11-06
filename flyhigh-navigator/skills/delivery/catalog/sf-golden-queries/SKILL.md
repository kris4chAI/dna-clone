---
name: "sf-golden-queries"
description: "Register golden queries with expected result fingerprints and a procedure that re-runs them and flags drift after every release. Delivery skill /golden-queries for the assurance stage; emits Snowflake-ready artefacts for human review."
---

# Golden queries (/golden-queries)

**Stage:** assurance · **Agent:** Semantic Tester · **Human gate:** Semantic tester owns the golden set; changes need BI lead approval

Register golden queries with expected result fingerprints and a procedure that re-runs them and flags drift after every release.

## When to use

Use this skill when the delivery pod reaches the assurance stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `queries` | Golden queries (id | SQL) | lines |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/golden-queries` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Capture expected fingerprints once from a signed-off baseline.
2. Call the procedure after each promotion; drift fails the release.

## Snowflake features used

- HASH_AGG fingerprints
- Snowflake Scripting procedure
- RESULT_SCAN

## Outputs

- `golden_queries.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
