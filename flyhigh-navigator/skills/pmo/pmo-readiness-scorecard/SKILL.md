---
name: pmo-readiness-scorecard
description: "Score a Snowflake modernization track on the 17-question AI-native readiness model across five weighted dimensions, set the qualification band and turn lagging dimensions into owned remediation actions."
---

# Readiness scorecard (PMO)

Decide whether each track is ready for AI-native data modernization, and close qualification gaps before Sprint 0 ends.

## When to use

- Month 1, during **Qualify**, for every track in scope.
- Again before each pilot and whenever a lagging dimension's remediation lands.

## Inputs

- The track name and the 17 answers, each scored 0 to 3 with the client team (not alone).
- Evidence for each answer: scope baseline, dashboard catalog, KPI dictionary, environment status, AI tool approval.

## Model

| Dimension | Weight |
|---|---|
| Program fundamentals | 30% |
| Data estate and work suitability | 20% |
| KPIs and ways of working | 15% |
| Platform, people and governance | 25% |
| Measurement and value | 10% |

- Dimension score = sum of answers ÷ (answered × 3).
- Overall = Σ dimension score × weight.
- **75%+ Ready · 50–74% Ready with remediation · below 50% Not ready yet.**
- A dimension below 67% is *lagging*: its remediation actions become owned items with dates.

## Steps

1. Score every question with the client program head and the AI Champion.
2. Compute the dimension and overall scores and the band.
3. For each lagging dimension, list its remediation actions, name an owner and a date, and raise them in the RAID log.
4. Record the qualification decision: status, key gaps, constraints, remediation and the assessment owner.

## Output

- `readiness_scorecard.md`: overall band, dimension table, low-scoring questions, remediation by dimension, qualification.
- `readiness.json`: the full scoring, for the steering pack.

## Rules

- Never mark a track Ready while a constraint that fixes the date (licence renewal, edition decision, AI tool approval) is unresolved; flag it as a dependency.
- The score informs the decision; the client program head and the AI Champion make it.
