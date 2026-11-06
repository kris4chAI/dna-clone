---
name: "sf-pr-template"
description: "Pull request and CODEOWNERS templates that carry the gate evidence: tests, reconciliation, rollback, access changes and stamps. Delivery skill /pr-template for the release stage; emits Snowflake-ready artefacts for human review."
---

# Pull request template (/pr-template)

**Stage:** release · **Agent:** Quality Gate · **Human gate:** Release manager enforces the template

Pull request and CODEOWNERS templates that carry the gate evidence: tests, reconciliation, rollback, access changes and stamps.

## When to use

Use this skill when the delivery pod reaches the release stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `owners` | Code owners (path | team) | lines |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/pr-template` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Commit both files to .github/.
2. Branch protection: require code-owner review and the build check.

## Snowflake features used

- Evidence links to Snowflake query IDs and recon tables

## Outputs

- `.github/pull_request_template.md`
- `.github/CODEOWNERS`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
