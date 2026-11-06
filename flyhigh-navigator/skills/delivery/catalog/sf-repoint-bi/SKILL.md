---
name: "sf-repoint-bi"
description: "Publish certified KPIs as a Snowflake semantic view (tables, relationships, facts, dimensions, metrics) for Tableau live connections and Cortex Analyst. Delivery skill /repoint-bi for the migration stage; emits Snowflake-ready artefacts for human review."
---

# Repoint BI to semantic views (/repoint-bi)

**Stage:** migration · **Agent:** BI Repoint agent · **Human gate:** BI lead and data owner certify each metric before publishing

Publish certified KPIs as a Snowflake semantic view (tables, relationships, facts, dimensions, metrics) for Tableau live connections and Cortex Analyst.

## When to use

Use this skill when the delivery pod reaches the migration stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `name` | Semantic view | text |
| `tables` | Tables (alias | fq name | primary key) | lines |
| `relationships` | Relationships (from_alias(col) -> to_alias) | lines |
| `facts` | Facts (alias.name = expression) | lines |
| `dimensions` | Dimensions (alias.name = expression) | lines |
| `metrics` | Metrics (alias.name = expression · use KPI library formulas) | lines |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/repoint-bi` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Take metric definitions from the certified KPI library.
2. Apply the semantic view; query it with SEMANTIC_VIEW() to check numbers.
3. Point Tableau workbooks at it with a live connection; validate with /compare-reports.

## Snowflake features used

- CREATE SEMANTIC VIEW
- SEMANTIC_VIEW() queries
- Cortex Analyst
- Tableau live connection

## Outputs

- `semantic_view.sql`
- `tableau_repoint.md`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
