---
name: pmo-steering-pack
description: "Compile the FlyHigh steering pack: readiness per track, KPI scorecard by RAG, top risks and issues, decisions needed, playbook progress and recent gate decisions."
---

# Steering pack (PMO)

Agents compile the pack; the program manager owns the narrative; steering owns the decisions.

## Cadence

- **Monthly** steering committee: milestones, benefits and licence retirement.
- **Weekly** RAID review with the client, the integration vendor and Snowflake.
- **Bi-weekly** show-and-tell and gate reviews (G1 to G3).

## Contents

1. Overall status (red if any metric is red or a high-severity issue is open; amber if any metric is amber).
2. Readiness by track with lagging dimensions.
3. KPI scorecard: metric, target, actual, status, note; red first.
4. Top open risks, issues and dependencies with owner and date.
5. Decisions needed from this forum (high-severity issues and dependencies).
6. Decisions recorded since the last pack.
7. Playbook progress by stage checklist.
8. Recent gate decisions.

## Rules

- Measure trusted numbers and legacy retired on date, not the volume of AI-converted code.
- Every figure comes from the scorecard, ledger or plan; never invent actuals. Leave a metric as "—" when it is not measured yet.
- Separate client cost avoided from Niche Consulting-funded value.

## Output

- `steering_pack.md`, ready to paste into the steering deck.
