---
name: "sf-compare-reports"
description: "Compare legacy report numbers (OAC, Power BI) with the new Snowflake/Tableau numbers per filter combination, within tolerance, and produce signed evidence. Delivery skill /compare-reports for the assurance stage; emits Snowflake-ready artefacts for human review."
---

# Compare reports (/compare-reports)

**Stage:** assurance · **Agent:** BI Comparator · **Human gate:** Business owner signs each report as matching or explained

Compare legacy report numbers (OAC, Power BI) with the new Snowflake/Tableau numbers per filter combination, within tolerance, and produce signed evidence.

## When to use

Use this skill when the delivery pod reaches the assurance stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `report` | Report | text |
| `checks` | Checks (metric | filter | new-value SQL) | lines |
| `tolerance_pct` | Tolerance % | number |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/compare-reports` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Fill legacy_values.csv from the legacy report export.
2. Load it to REPORT_COMPARE_LEGACY, run compare.sql.
3. Attach the result to the BI validation evidence.

## Snowflake features used

- Comparison table + query
- Snowflake values from semantic views or gold tables

## Outputs

- `legacy_values.csv`
- `compare.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
