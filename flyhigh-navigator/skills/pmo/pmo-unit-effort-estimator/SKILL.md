---
name: pmo-unit-effort-estimator
description: "Estimate an AI-native Snowflake program with the unit-effort model: objects by complexity, AI frameworks and discovery, pilot share and wave speed-up, returning person-days, person-months and average FTE."
---

# Unit-effort estimator (PMO)

Size the build with a transparent unit-effort model that assumes no AI gain until the pilot proves it.

## Model

| Component | Unit | Base (person-days) |
|---|---|---|
| ETL | pipeline or mapping | 1 |
| DW | fact, dim or semantic view | 1 |
| BI | dashboard or report | 6 |

- Complexity multipliers: simple ×1, medium ×2, complex ×4.
- AI frameworks (build or adapt + validation): simple 6 + 3, medium 15 + 5, complex 25 + 8 person-days.
- Discovery components (logical sources or report groups): simple 10, medium 20, complex 30 person-days.
- **Pilot share** runs at full effort; the rest runs at full effort ÷ **wave speed-up** (3× conversion for migration, 1.5× model-first for data products, none until proven).
- Object effort splits Build 40%, SIT 35%, UAT 25%.
- Person-months = person-days ÷ 22; average FTE = person-months ÷ delivery months.

Framework complexity points: agents ×2, sub-agents ×1.5, skills ×1, tools ×0.5, function calls ×0.5. Simple ≤ 20, medium ≤ 36, else complex.

## Steps

1. Take object counts by complexity from the estate assessment (AIM, report catalog).
2. Set the pilot share, the wave speed-up for the archetype and the delivery months.
3. Run the model; compare with and without the speed-up.
4. Save the scenario and reset wave unit effort from pilot evidence.

## Output

- `estimate.md` and `estimate.json`: totals, components, activity split and the saving versus pilot effort.

## Rules

- Excludes program management, cut-over and hypercare, which are loaded by role in the resource plan.
- Present AI-driven savings as INDICATIVE until the pilot proves the conversion rate.
