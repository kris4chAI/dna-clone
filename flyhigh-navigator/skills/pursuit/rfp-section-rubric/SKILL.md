---
name: "rfp-section-rubric"
description: "Independently score one RFP response section against a 10-criterion weighted rubric and its must-haves, citing evidence, and return the highest-leverage fixes."
---

# RFP section rubric

Use this skill to score one section (or all 14) of an RFP response. Run it as a separate agent with fresh context: give it only the rendered slides or slide text, the client inputs and this rubric, never the builder's reasoning. Be strict; do not inflate.

## Criteria (100 points)

| Criterion | Weight | Full marks when |
| --- | --- | --- |
| Client specificity | 15 | Client systems, volumes, dates, people and terms; nothing generic |
| Requirement coverage | 15 | Every requirement mapped to this section is answered |
| Differentiation | 10 | Shows what we add beyond rivals with the same partner badges |
| Evidence | 10 | Quantified, sourced, relevant proof |
| Storyline and clarity | 10 | Titles of three words or fewer, message in subtitles, one idea per slide, flows from the previous section |
| Feasibility and honesty | 10 | Assumptions explicit; unvalidated items stamped; guardrails visible |
| Buyer outcomes | 10 | Revenue, cost, speed or risk for named stakeholders |
| Visual and brand quality | 10 | Brand palette and type, no overlaps, readable, logos approved or flagged |
| Risk and governance | 5 | Risks, owners and decision rights where implied |
| Next action | 5 | What the client should decide, validate or provide |

Anchors: 0 absent, 1 generic, 2 partial, 3 strong with one gap, 4 complete with evidence. Points = weight × score ÷ 4. Every 3 or 4 must cite the slide number and the words that earn it.

## Must-haves

Use the section's must-haves from `rfp-section-builder`. A section passes only at 90 points or more with every must-have met. A missing must-have caps the section at 89.

## Consistency checks (always)

Flag any number, date, count or name that conflicts with another slide or section (for example estate size, cut-over date, dashboard counts, pilot timing, prices). Flag ROI or value logic that counts vendor- or partner-funded items as client savings, or counts run savings before go-live. Flag content that is off-scope or references a rival platform.

## Output (compact)

For each section scored:

- Score out of 100, and the per-criterion scores with one line of evidence or gap each.
- Must-haves missing.
- The top three fixes ranked by points recovered, each specific (slide number, what to change).
- Blocked-by for any fix that needs client, legal or reference input the team cannot create.

For a full deck, add the weighted overall score: executive summary and next steps 15%, understanding 10%, sections 3–8 together 25%, delivery 10%, team 10%, proof 10%, Why Niche Consulting 10%, commercials 10%.