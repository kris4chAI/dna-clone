---
name: "sf-load-test"
description: "Run dashboard queries concurrently against a warehouse with a query tag, then report p50/p95 latency, queueing and spill from QUERY_HISTORY against the 5-second target. Delivery skill /load-test for the assurance stage; emits Snowflake-ready artefacts for human review."
---

# Load test (/load-test)

**Stage:** assurance · **Agent:** Performance Agent · **Human gate:** Performance agent results reviewed with the platform owner

Run dashboard queries concurrently against a warehouse with a query tag, then report p50/p95 latency, queueing and spill from QUERY_HISTORY against the 5-second target.

## When to use

Use this skill when the delivery pod reaches the assurance stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `warehouse` | Warehouse | text |
| `users` | Concurrent users | number |
| `iterations` | Iterations per user | number |
| `target_ms` | Target p95 (ms) | number |
| `queries` | Dashboard queries (one per line) | lines |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/load-test` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Run load_test.py from a machine near the account region with a service user.
2. Run analyze.sql with the printed tag.
3. Hand results to /tune-warehouse.

## Snowflake features used

- QUERY_TAG
- INFORMATION_SCHEMA.QUERY_HISTORY_BY_WAREHOUSE
- Multi-cluster warehouses
- snowflake-connector-python

## Outputs

- `load_test.py`
- `analyze.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
