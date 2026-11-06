---
name: "rfp-commercials-model"
description: "Turn a proposal's resource loading into commercials: rate card, scope options, managed services, fixed and flex term discounts, contract value, TCO and ROI, plus the matching pricing slides."
---

# RFP commercials model

Use this skill when the user gives rates and asks for pricing, options, managed services, discounts, TCO or ROI for a proposal.

## Inputs

- The resource-loading workbook (roles, pods, location, monthly FTE) and its effort estimate.
- Rates by location (for example onsite and offshore per hour), billable hours per day, billable days per month.
- The scope building blocks the user names (for example foundation, track A, track B must-have, track B nice-to-have discovery).
- The managed-services team (for example 1 onsite and 4 offshore for 24 months) and the term options (up to 3 years).

## Edit the existing workbook in place (xlsx skill)

Match its conventions: input cells blue on light yellow, headers dark purple, totals highlighted. Leave existing formulas untouched.

1. **Resource loading:** add rate, billable hours and cost columns per role, with totals and a blended rate.
2. **Commercials sheet** (new), with a yellow banner naming the internal reviewers:
   - Rate card inputs.
   - Cost by pod and location, tied to the loading total.
   - Scope building blocks priced from the pods; discovery-only items priced from the effort estimate at the core team's cost per person-day. Check that the blocks add up to the total.
   - Scope options (baseline, option 1, option 2 and so on) with person-months, rate-card price, term-discounted price, peak FTE and blended rate.
   - Managed services: role, location, FTE, rate, monthly cost, months, total and annual run cost.
   - Discount model: committed-term tiers with fixed-capacity and flex-capacity discounts (flex at half the fixed discount by default), the tier that applies by committed months, and a flex pool (FTE, expected use, monthly cap).
   - Three-year view: fixed program, fixed managed services and flex, with rate-card value, discount, net price, total contract value and savings.
3. **Summary and Assumptions:** add the key commercial figures and number the new assumptions.

Recalculate and fix until zero formula errors. Verify the totals tie out.

## TCO and ROI (when asked)

Model the five cost levers: infrastructure (licenses and subscriptions, including dev, project, security and audit tools), implementation, maintenance, enablement (training, change, go-to-market, legal and compliance) and transient (new technology during transition, duplicate environments, vendor overlap). Show today vs target annual run cost and the savings. Model value inside the program (AI-assisted effort, partner funding, accelerators, shorter parallel run, retired licenses) less transient cost. State payback per $1M of net investment if price is not final. Every baseline is a stated planning assumption with a client-input placeholder.

## Slides (niche-exec-offering)

Pricing slide: option cards with the recommended one highlighted, the discount table, the three-year view and the rate-card footnote. TCO and ROI slides as needed. Stamp every one INDICATIVE in the top-right corner and add the FOR REVIEW note naming the deal-desk reviewers. Never present indicative numbers as validated.

## Output to the user

A short table of the options and totals, the managed-services and three-year figures, and the decisions the reviewers must make. Save over the working files in the pursuit folder and verify by checksum.