---
name: "sf-gen-changelog"
description: "Turn conventional commits since the last tag into a CHANGELOG.md section and the next semantic version. Delivery skill /gen-changelog for the release stage; emits Snowflake-ready artefacts for human review."
---

# Generate changelog (/gen-changelog)

**Stage:** release · **Agent:** Release Agent · **Human gate:** Release agent output reviewed by the release manager

Turn conventional commits since the last tag into a CHANGELOG.md section and the next semantic version.

## When to use

Use this skill when the delivery pod reaches the release stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `last_version` | Last version | text |
| `commits` | Commits since last tag (one per line) | lines |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/gen-changelog` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Paste `git log --pretty=%s vLAST..HEAD`.
2. Commit the section on the release branch; tag the version.

## Snowflake features used

- Release metadata for schemachange versions

## Outputs

- `CHANGELOG_SECTION.md`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
