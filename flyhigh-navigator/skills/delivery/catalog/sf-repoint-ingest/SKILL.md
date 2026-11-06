---
name: "sf-repoint-ingest"
description: "Repoint Boomi/CDC and file feeds to Snowflake: storage integration, stage, file format, auto-ingest Snowpipe, stream and merge task into Silver, or a Kafka connector config. Delivery skill /repoint-ingest for the migration stage; emits Snowflake-ready artefacts for human review."
---

# Repoint ingestion (/repoint-ingest)

**Stage:** migration · **Agent:** Ingest Repoint agent · **Human gate:** Platform engineer reviews; data owner confirms the feed contract

Repoint Boomi/CDC and file feeds to Snowflake: storage integration, stage, file format, auto-ingest Snowpipe, stream and merge task into Silver, or a Kafka connector config.

## When to use

Use this skill when the delivery pod reaches the migration stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `feed` | Feed name | text |
| `pattern` | Pattern | choice |
| `s3_url` | S3 location | text |
| `role_arn` | AWS IAM role ARN | text |
| `bronze_table` | Bronze table | text |
| `silver_table` | Silver table | text |
| `key` | Merge key | text |
| `columns` | Columns (name type) | lines |
| `topic` | Kafka topic | text |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/repoint-ingest` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Create the storage integration once per bucket and share the IAM trust values with the cloud team.
2. Apply ingest.sql in DEV; drop a sample file and watch COPY_HISTORY.
3. Resume the task after review; monitor with /test-cdc.

## Snowflake features used

- Storage integration + external stage
- Snowpipe AUTO_INGEST
- Streams + tasks (MERGE)
- Snowflake Kafka connector / Snowpipe Streaming

## Outputs

- `ingest.sql`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
