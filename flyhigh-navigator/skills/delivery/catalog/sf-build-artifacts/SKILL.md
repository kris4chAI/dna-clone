---
name: "sf-build-artifacts"
description: "Scaffold the repository for Snowflake as code (schemachange migrations, dbt, policies) and a GitHub Actions build that validates every change against a zero-copy clone. Delivery skill /build-artifacts for the release stage; emits Snowflake-ready artefacts for human review."
---

# Build Snowflake artefacts (/build-artifacts)

**Stage:** release · **Agent:** Build Agent · **Human gate:** Build must be green before review

Scaffold the repository for Snowflake as code (schemachange migrations, dbt, policies) and a GitHub Actions build that validates every change against a zero-copy clone.

## When to use

Use this skill when the delivery pod reaches the release stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `repo` | Repository name | text |
| `database` | Database validated per PR | text |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/build-artifacts` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Create the layout and commit it.
2. Add SNOWFLAKE_* secrets in GitHub (key-pair).
3. Every PR clones the DEV database, deploys into the clone, runs tests and drops it.

## Snowflake features used

- schemachange
- Snowflake CLI (snow)
- Zero-copy clone for PR validation
- dbt-snowflake

## Outputs

- `REPO_LAYOUT.md`
- `.github/workflows/build.yml`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
