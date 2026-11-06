---
name: "rfp-win-scorecard"
description: "Score a proposal against every buyer, evaluator and competitor archetype in a RAG-coloured Excel scorecard and list only the pending actions that lift the score."
---

# RFP win scorecard

Use this skill to create or rerun the internal win scorecard for a proposal. It is internal only and never goes to the client.

## Inputs

- The current proposal deck (read every slide, not just titles).
- The buying group: executives and named evaluators, with LinkedIn URLs where given.
- Competitor archetypes (default: boutique specialist firm, tier-1 consulting firm, mid-sized SI). Never name real competitors in client material; here they are archetypes, not intelligence on named firms.
- The previous scorecard, if one exists.

## Confirm roles first

Look up each person's title with the in-app browser. If LinkedIn shows a sign-in wall, ask the user to sign in, then retry. Mark each role Confirmed, Partly confirmed or Assumed. Assumed roles get a yellow fill. Merge duplicates (the same person under two names).

## Workbook (xlsx skill, openpyxl, Arial, formulas recalculated with recalc.py, zero errors)

Sheets:

1. **Summary:** executive, evaluator and whole-group averages (simple and influence-weighted), Niche Consulting vs best rival rubric score, projected score if all actions are done, RAG, and a Previous run and Change column.
2. **Executive scorecard** and **Evaluator scorecard:** one row per person with role, role status, influence (1–3), what they weigh, and scores of 1–5 on five dimensions: business value, delivery certainty, domain and solution fit, commercials and TCO, trust and MSA terms. Overall = average (formula); RAG = formula. Columns for what lands, the gap to close, action IDs, the previous overall and the change.
3. **Competitor rubric:** weighted criteria (for example logistics or industry depth, platform migration expertise, delivery certainty, cloud and security, BI modernization, AI native delivery, scale and continuity, TCO and business case, commercial flexibility, executive access), Niche Consulting and each archetype scored, SUMPRODUCT totals, rank, lead vs best rival, and how each rival will attack with our counter.
4. **Action items:** ID, action, stakeholders lifted, dimension, Niche Consulting owner role, due date, expected lift, status dropdown (Not started, In progress, Done) with RAG fill.

RAG thresholds: green 4.0 or higher, amber 3.0–3.9, red below 3.0. Blue text for score inputs, black for formulas, green for cross-sheet links.

## Scoring discipline

- Score the deck as written, not orals or relationships.
- Move a score only when the deck changed something that person weighs; state why in what lands and the gap.
- On a rerun, set Previous to the last run's values so Change shows this round's movement.
- Mark actions Done only when the artefact exists; In progress when drafted but pending review.

## Output to the user

A short table of the headline scores and changes, who moved and why, and, when asked, only the pending actions (not done), sorted by expected lift. Save over the working scorecard in the pursuit folder and verify by checksum.