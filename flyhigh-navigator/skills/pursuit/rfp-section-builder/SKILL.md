---
name: "rfp-section-builder"
description: "Extract the section structure of a Niche Consulting RFP response, then generate or revise any one of its 14 sections independently from a section brief, ready for rubric scoring."
---

# RFP section builder

Use this skill to (a) extract the structure of an existing proposal deck, or (b) generate or revise ONE section of an RFP response without touching the rest. It is the generator in the `rfp-section-loop`; `rfp-section-rubric` scores its output.

## Standing rules

- Niche Consulting slides: `niche-exec-offering` only; check with `niche-brand-guardian`.
- Titles of three words or fewer, sentence case, assertive; the message goes in a subtitle line under the title.
- Never invent client facts, numbers, names or quotes. Use client inputs; otherwise insert a labelled placeholder ([client input], bracketed values) and a stamp: ILLUSTRATIVE (designs, mock-ups, unconfirmed vendor capability), INDICATIVE (money, TCO, ROI, funding), FOR JOINT REVIEW (contract, security, RACI, assumptions, risks).
- No competitor names. Flag partner, client and vendor logos for approval. Cite external facts on the slide.
- Keep numbers consistent with the rest of the deck (estate size, dates, counts, prices). Read the other sections' key figures before writing.

## Mode A: extract the structure

Render or text-extract the deck, read every slide's section label, title and subtitle, and group slides into the 14 standard sections below. Output a table: section, slide range, slide count, what it must prove, and any slides that do not fit (flag them as candidates to cut). Save it as `structure.md` in the pursuit folder.

## Mode B: build one section

Inputs: the section number, client inputs (RFP, notes, discovery answers, models), the current deck (for consistency), and, on later rounds, the evaluator's fix list. On a revision, change only what the fix list names.

## The 14 sections (brief and must-haves)

1. **Executive summary** (3 slides): value framework, value levers, "beyond the badges" differentiation. Must-haves: headline value figure; 3–4 value levers; differentiation beyond shared partner badges; the ask with a date.
2. **Our understanding** (4–5): drivers, current state per track, must-haves and priorities. Must-haves: drivers with quantified pain; current state per track; must-haves with dates; a requirement-to-slide trace table.
3. **Target state and architecture** (4–6): tenets, reference architecture, platform architecture, partner platforms. Must-haves: reference and platform architecture; system of record per domain; non-functional requirements (availability, freshness, latency, security, RPO and RTO, recovery); partner integration patterns labelled; discovery-only items on one slide with a scope guardrail.
4. **Journey maps** (2–3): one lane per persona, four stages each. Must-haves: named personas; each stage shows the question, the tool and the KPI; act stages name the system written back to; baseline and target per KPI.
5. **Persona dashboards** (3–5): MacBook mock-up rendered with Playwright, the four questions (what happened, why, what will happen, what you can do) with click-through animation. Must-haves: one per key persona (executive, operations, transportation, customer); KPI tiles tagged with KPI-library IDs; illustrative-data label.
6. **Data model and KPIs** (4–5): subject areas, star schemas, KPI library. Must-haves: grain, keys and conformed dimensions; history (SCD) and data-quality rules; source system per fact; KPI definitions that match the dashboards. Reference only models aligned to the proposed platform.
7. **Engineering** (3–4): accelerators and AI frameworks with human gates, tied to the client's objects (mappings, reports, tables). Must-haves: human gates per framework; productivity targets with a stated baseline; CI/CD, environments and infrastructure as code.
8. **AI** (1–2): use cases and roadmap. Must-haves: value-by-readiness matrix (INDICATIVE); AI governance and guardrails; data stays in the platform; owner and success metric per pilot.
9. **Delivery plan** (5–8): phases, waves, integrated timeline, transition. Must-haves: calendar months; gates; parallel run and cut-over; client dependencies with need-by dates; no timing conflicts between slides.
10. **Team and governance** (6–9): team structure, engagement model, governance, agile, quality, RACI, assumptions, risks. Must-haves: locations as cities and named leads; RACI with client duties; governance cadence; assumptions; risks with owner and trigger.
11. **Proof** (4–6): case studies. Must-haves: at least three relevant cases with achieved, quantified outcomes; at least one in the client's industry; at least one matching the migration pattern; references offered.
12. **Why Niche Consulting** (5–7): trust and client satisfaction, security and compliance, partnerships, MSA readiness. Must-haves: sourced credentials; partner tiers; MSA positions with values to agree, flagged for Legal.
13. **Commercials and value** (3–5): pricing options, TCO, ROI, partner funding. Must-haves: options compared; rate card; term discounts; TCO and ROI with client-input placeholders; client cost avoided kept separate from Niche Consulting- or partner-funded value; INDICATIVE stamp and deal-desk review flag. Use `rfp-commercials-model` for the numbers.
14. **Next steps** (1): decision and mobilization. Must-haves: the decision; a dated mutual action plan with a client owner and a Niche Consulting owner per step; what we need from the client; a realistic contract timeline.

## Output

The revised slides in the deck (one build, saved over the working version and verified), plus a short change note listing what changed against each fix. Hand the section to `rfp-section-rubric` for scoring.