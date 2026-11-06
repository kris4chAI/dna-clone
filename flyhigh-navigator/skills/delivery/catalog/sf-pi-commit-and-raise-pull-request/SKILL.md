---
name: "sf-pi-commit-and-raise-pull-request"
description: "Create the branch, conventional commit and pull request (with reviewers and the gate checklist) for a PRD or design artefact. Delivery skill /pi-commit-and-raise-pull-request for the discover stage; emits Snowflake-ready artefacts for human review."
---

# Commit and raise pull request (/pi-commit-and-raise-pull-request)

**Stage:** discover · **Agent:** PRD Agent · **Human gate:** The named approver reviews the PR; merging records the gate

Create the branch, conventional commit and pull request (with reviewers and the gate checklist) for a PRD or design artefact.

## When to use

Use this skill when the delivery pod reaches the discover stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `artefact` | Artefact path | text |
| `kind` | Kind | choice |
| `title` | Short title | text |
| `reviewers` | Reviewers (GitHub handles, one per line) | lines |
| `ticket` | Ticket key | text |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/pi-commit-and-raise-pull-request` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Check the artefact passes its own checklist.
2. Run raise_pr.sh from the repository root.
3. Paste the PR link into the gate log.

## Snowflake features used

- Artefacts versioned next to Snowflake code

## Outputs

- `raise_pr.sh`
- `pr_body.md`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
