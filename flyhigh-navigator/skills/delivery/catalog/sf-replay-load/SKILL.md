---
name: "sf-replay-load"
description: "Replay files or a time window idempotently: refresh the pipe, force-reload specific files and deduplicate on the key so reruns never double count. Delivery skill /replay-load for the assurance stage; emits Snowflake-ready artefacts for human review."
---

# Replay a load (/replay-load)

**Stage:** assurance · **Agent:** Pipeline Monitor · **Human gate:** Pipeline owner approves replays in production

Replay files or a time window idempotently: refresh the pipe, force-reload specific files and deduplicate on the key so reruns never double count.

## When to use

Use this skill when the delivery pod reaches the assurance stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `pipe` | Pipe | text |
| `stage` | Stage | text |
| `table` | Bronze table | text |
| `files` | Files to force-reload (one per line) | lines |
| `since` | Replay files modified after (timestamp) | text |
| `key` | Dedupe key | text |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/replay-load` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Pick refresh (missed notifications) or force (bad data fixed upstream).
2. Run, then run the dedupe block.
3. Re-run /test-cdc and /reconcile for the window.

## Snowflake features used

- ALTER PIPE ... REFRESH
- COPY INTO ... FORCE / FILES
- MERGE with QUALIFY dedupe

## Outputs

- `replay.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
