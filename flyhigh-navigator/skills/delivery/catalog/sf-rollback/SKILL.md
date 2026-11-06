---
name: "sf-rollback"
description: "Generate rollback steps per object using Time Travel (clone at timestamp, UNDROP) and a forward-fix template, with verification queries. Delivery skill /rollback for the release stage; emits Snowflake-ready artefacts for human review."
---

# Roll back a release (/rollback)

**Stage:** release · **Agent:** Promotion Agent · **Human gate:** Release manager authorizes production rollback

Generate rollback steps per object using Time Travel (clone at timestamp, UNDROP) and a forward-fix template, with verification queries.

## When to use

Use this skill when the delivery pod reaches the release stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `release_ts` | Release start timestamp (UTC) | text |
| `objects` | Objects changed (type | name) | lines |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/rollback` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Decide rollback vs forward fix with the release manager.
2. Run rollback.sql object by object; verify counts.
3. Record the incident and update the runbook.

## Snowflake features used

- Time Travel AT (TIMESTAMP)
- UNDROP
- Zero-copy clone
- Fail-safe awareness

## Outputs

- `rollback.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
