---
name: "sf-release-notes"
description: "Write business-readable release notes from the changelog with Snowflake objects changed, evidence and rollback pointer. Delivery skill /release-notes for the release stage; emits Snowflake-ready artefacts for human review."
---

# Release notes (/release-notes)

**Stage:** release · **Agent:** Release Agent · **Human gate:** Release manager publishes after production approval

Write business-readable release notes from the changelog with Snowflake objects changed, evidence and rollback pointer.

## When to use

Use this skill when the delivery pod reaches the release stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `version` | Version | text |
| `highlights` | Highlights for users (one per line) | lines |
| `objects` | Snowflake objects changed | lines |
| `evidence` | Evidence links | lines |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/release-notes` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Generate after the changelog.
2. Attach to the GitHub release and the change ticket.

## Snowflake features used

- Objects changed
- Evidence: GOLDEN_RUN, RECON_RESULT query IDs

## Outputs

- `release-notes-2.0.0.md`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
