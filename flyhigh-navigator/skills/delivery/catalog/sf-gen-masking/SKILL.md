---
name: "sf-gen-masking"
description: "Create tag-based masking: a PII category tag, one tag-bound masking policy that masks each category its own way, and tags applied to classified columns. Delivery skill /gen-masking for the foundation stage; emits Snowflake-ready artefacts for human review."
---

# Generate masking policies (/gen-masking)

**Stage:** foundation · **Agent:** Policy Author · **Human gate:** Data owner approves categories; FOR JOINT REVIEW with privacy

Create tag-based masking: a PII category tag, one tag-bound masking policy that masks each category its own way, and tags applied to classified columns.

## When to use

Use this skill when the delivery pod reaches the foundation stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `columns` | Classified columns CSV (column,category) | table |
| `unmask_roles` | Roles that see clear values (one per line) | lines |
| `policy_schema` | Policy schema | text |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/gen-masking` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Optionally run SYSTEM$CLASSIFY to propose categories.
2. Confirm categories with the data owner.
3. Apply masking.sql; test with /test-rls style role checks.

## Snowflake features used

- Object tagging
- Tag-based masking policies
- IS_ROLE_IN_SESSION
- SYSTEM$CLASSIFY (optional discovery)

## Outputs

- `masking.sql`
- `verify_masking.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
