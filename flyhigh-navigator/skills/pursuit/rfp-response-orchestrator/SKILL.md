---
name: "rfp-response-orchestrator"
description: "Run a Niche Consulting RFP pursuit end to end with the AI Native Sales Engineering method: nine gated stages from RFP signal to orals, with artefacts, skills, stamps and stage questions."
---

# RFP response orchestrator (AI Native Sales Engineering)

Use this skill when the user starts or continues an RFP, RFI or proposal pursuit for Niche Consulting. It runs the nine-stage method, drafts each artefact with the right skill, asks the stage questions, and never passes a gate without a named human approver.

## Standing rules

- Niche Consulting decks: use `niche-exec-offering` only. Apply `niche-brand-guardian` before anything leaves the team.
- Do not ask clarifying questions unless the audience or objective is missing. Make a reasonable assumption, state it, and continue.
- Agents draft, humans decide. Record every gate decision (who, when, what) in project memory and in the pursuit folder.
- One source of truth per artefact: the deck, the effort and commercials workbook, and the scorecard are each regenerated from one build, never patched in parallel. Save over the working version in the pursuit folder and verify the saved copy by checksum. If a save looks stale, re-stage under a unique file name and commit again.
- Honest labels: anything not validated with the client gets a rubber-stamp label in the top-right corner of the slide: ILLUSTRATIVE (designs, vendor integrations, mock-ups), INDICATIVE (prices, TCO, ROI, funding), FOR JOINT REVIEW (MSA, security controls, RACI, assumptions, risks). Scope guardrails (for example "discovery only") appear on every slide they affect.
- Never invent client facts, figures or quotes. Mark gaps as client inputs or bracketed values to agree. Cite external sources on the slide.
- No competitor names in client-facing material. Partner, client and vendor logos are flagged for approval.
- Bundle many downloads into one zip.

## Pursuit folder

Create or reuse: `<Client>/` with the RFP, notes, `deck/`, `models/` (resource loading, commercials), `scorecard/`, `reviews/`. Keep one working version of each file.

## The nine stages

For each stage: list the artefacts, draft them with the named skill, ask the questions, then request the gate approval in chat.

### 1. Signal and qualify (gate G0, bid decision; pursuit lead + practice head)

Artefacts: opportunity brief, stakeholder research, bid memo (Claude Docs). Tools: web search, in-app browser (LinkedIn roles; ask the user to sign in if a profile hits a sign-in wall), CRM and email connectors if connected.

Questions: Is the program funded, with a decision date and sponsor? Who is the economic buyer and do we know them? Who are the competitors or incumbent? Which platform partners are engaged and will they back us? Can we win and deliver profitably?

### 2. Decode the RFP (gate G1, clarifications sent; proposal manager)

Artefacts: requirements and compliance matrix and discovery questionnaire (`xlsx`), clarification log (Claude Docs). Read the RFP with the pdf or docx skill.

Questions: What is mandatory vs desirable and how is it scored? What is out of scope or discovery only? Which volumes and counts are unknown? Whose MSA paper governs? What are the dates?

### 3. Win strategy (gate G2; pursuit lead + client partner)

Artefacts: stakeholder map with confirmed roles, win themes, competitor rubric and baseline scorecard (`rfp-win-scorecard`), executive summary storyline including a "beyond the badges" slide.

Questions: What does each buyer care about? What do we add beyond shared partner credentials? How would a boutique, a tier-1 firm and a mid-sized SI attack us? Which proof points fit? What is the one-sentence answer to "why Niche Consulting"?

### 4. Solution design (gate G3; solution architect + partner SE)

Artefacts: current state, reference and target architecture, journey maps per persona, persona dashboards (what happened, why, what will happen, what you can do; mock-ups rendered with Playwright), data model and KPI library, accelerators, partner integration (single pane of glass, data pulled once, system-of-record matrix, no-duplication options), scope guardrails.

Questions: What must be live by cut-over? Which data enters once and from where? Which vendor capabilities are unconfirmed (stamp ILLUSTRATIVE)? How does each persona go from insight to action? What stays discovery only?

### 5. Delivery plan and effort (gate G4, zero variance; delivery lead)

Artefacts: integrated plan, pods, resource loading and effort estimate reconciled to zero variance per pod and phase (`xlsx`), team structure, RACI, governance, hybrid agile, assumptions, risks, job descriptions (`proposal-to-job-descriptions`). Partner team roles use the partner's brand color where the user asks.

Questions: Does effort reconcile to loading? What does the client own (including change management)? Where do partner teams sit? What are the top risks and owners?

### 6. Commercials and value (gate G5, deal review; deal lead + finance)

Run `rfp-commercials-model`. Flag the pricing slide FOR REVIEW by the named deal-desk reviewers and stamp INDICATIVE.

Questions: Which options will the buyer compare? What discount does term earn and how is flex billed? Which TCO and ROI inputs are assumptions? What partner funding is confirmed?

### 7. Trust, security and MSA readiness (gate G6, legal review)

Artefacts: brand trust and client satisfaction slide, security and compliance slide (certified practices vs proposed controls), MSA readiness slide (IP, data residency, incident notice, SLAs, warranty, liability, insurance, people, exit, audit) with bracketed values and a FOR REVIEW: Niche Consulting Legal flag. Source claims from the current corporate presentation and cited public pages; skip anything marked not for public use and anything without evidence (for example certifications not in the sources).

Questions: Which certifications and rankings can we claim, with a source? What are our positions on each MSA term? Which values are still to agree?

### 8. Assemble, brand and red team (gate G7: group score of 4.0 or higher, no stakeholder in red)

Deck sweep: titles of three words or fewer, messaging in subtitles, unique section dividers, agenda matching the flow, no slide-number references. Brand audit table (Rule, Where, Issue, Fix, Severity). Plain-language pass (`humanizer`). Rescore with `rfp-win-scorecard` and list only pending actions. Build a 12-slide executive cut.

Questions: Does every slide earn its place? Is every claim sourced and every unvalidated item stamped? Who is still amber or red, and why? Are logos approved?

### 9. Submit, orals and learn (gate G8, submission sign-off)

Artefacts: submission pack, orals deck, Q&A bank of the ten hardest questions with owners, next steps and MSA plan, win or loss retrospective. Feed lessons back with `propose_skills`.

## Reporting to the user

After each stage: one or two sentences on what changed, where it is saved, what needs a human decision, and any pending actions. Do not recap every step.