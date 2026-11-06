---
name: pmo-usecase-prioritizer
description: "Rank data modernization activities for AI and agent enablement on value, repeatability, feasibility, trust and automation, and assign each a lane: pilot wave, next wave, assist only or human gate."
---

# AI use-case prioritizer (PMO)

Decide where agents work first, and where people must stay in charge.

## Criteria and weights

| Criterion | Question | Weight |
|---|---|---|
| Value impact | How much effort, risk or time can AI remove from the wave? | 30 |
| Repeatability | Is the activity repeated across many objects with a pattern? | 20 |
| Feasibility | Can it be split into skill-sized tasks (low complexity scores high)? | 20 |
| Trust and safety | Does the output keep numbers right and data secure (low risk scores high)? | 15 |
| Automation potential | Execute or orchestrate 3, recommend 2, human 0 | 15 |

High = 3, medium = 2, low = 1. Score = weighted average ÷ 3 × 100.

## Lanes

- **Human gate:** manual activities and anything rated high risk (masking design, agent tool permissions, G3 sign-off, go / no-go).
- **Pilot wave:** score 80 or more.
- **Next wave:** 65 to 79.
- **Assist only:** below 65.

## Steps

1. Rate each activity per archetype with the AI Champion and pod leads.
2. Check context availability and prerequisites for every pilot-lane item.
3. Confirm autonomy: Tier 1 draft only, Tier 2 agent with PR review, Tier 3 unattended runs.
4. Feed the pilot lane into the wave plan and the skill coverage KPI.

## Output

- `usecase_priorities.md`: the ranked activities by lane with prerequisites.
