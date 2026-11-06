---
name: "sf-lint-sql"
description: "Enforce one SQL standard with SQLFluff (Snowflake dialect), a pre-commit hook and a quick check of a pasted script for common Snowflake anti-patterns. Delivery skill /lint-sql for the release stage; emits Snowflake-ready artefacts for human review."
---

# Lint SQL (/lint-sql)

**Stage:** release · **Agent:** Quality Gate · **Human gate:** Quality gate: lint must pass on every PR

Enforce one SQL standard with SQLFluff (Snowflake dialect), a pre-commit hook and a quick check of a pasted script for common Snowflake anti-patterns.

## When to use

Use this skill when the delivery pod reaches the release stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `sql` | SQL to check (optional) | textarea |
| `max_line` | Max line length | number |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/lint-sql` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Commit .sqlfluff and .pre-commit-config.yaml.
2. Fix every finding or justify it in the PR.

## Snowflake features used

- SQLFluff snowflake dialect
- Anti-pattern checks (SELECT *, ORDER BY without LIMIT, CREATE OR REPLACE on tables)

## Outputs

- `.sqlfluff`
- `.pre-commit-config.yaml`
- `findings.md`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
