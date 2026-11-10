---
name: aw-impact-analyzer
description: "From a list of changed files, find the impacted test cases through test-to-code mappings and rank the regression suite by risk (mapping score × priority × failure history)."
---

# Impact analyzer (assurance)

## Inputs

- Changed files, for example the output of `git diff --name-only main...HEAD`.
- The test-case-to-code mappings maintained in the workbench.

## Method

1. Match the changed paths to mapped code modules (dbt models, procedures, policies, semantic views, dashboards, harnesses).
2. Collect every test case mapped to those modules.
3. Risk = mapping score × priority weight (High 3, Medium 2, Low 1) × (1 + historical failure rate).
4. Keep the highest risk per case and sort descending.
5. Report paths that are not mapped yet so the mapping can be extended.

## Output

`impact_analysis.md`: the ranked regression suite. In the app, "Create regression plan" turns it into a test plan.
