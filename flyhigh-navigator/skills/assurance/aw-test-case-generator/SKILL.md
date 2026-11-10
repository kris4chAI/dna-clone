---
name: aw-test-case-generator
description: "Generate a versioned suite of functional, negative, data, security, performance, UI and API test cases from user stories or from requirements, screen lists and API endpoints, for a Snowflake modernization program."
---

# Test case generator (assurance)

## Sources

- **User stories:** from the ALM (Jira, Rally, Azure DevOps) or requirement documents (PDF, XLSX, DOCX, S3). In FlyHigh, stories also come from the persona journeys.
- **Other documents:** FSD or BRD (one requirement per line), UI/UX (one screen per line) and API docs (one endpoint per line, for example `GET /shipments/{id}`).

## Rules

1. One test case per acceptance criterion. Classify it by what it checks:
   - **data:** reconcile, legacy, match, row count, history, SCD, idempotent, load;
   - **security:** only, row access, mask, role, confidential, denied, declined;
   - **performance:** under N s, latency, respond, SLA, budget;
   - **api:** an HTTP verb and a path;
   - **functional:** everything else.
2. Add one **negative** case per story: a user without access is refused and the attempt is logged.
3. Priority is High for data and security cases and for High-priority stories.
4. Steps follow the type template (sign in, open, act, check; or golden query on legacy and Snowflake, compare, record in the ledger).
5. Expected results are observable: certified values, counts within tolerance, only permitted rows, inside the threshold.
6. Every generation creates a new suite version; earlier versions stay for the audit trail.

## Output

`test_cases.md` (review table) and `test_cases.csv` (import into the ALM or the workbench).
