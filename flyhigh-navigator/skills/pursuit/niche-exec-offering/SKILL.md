---
name: "niche-exec-offering"
description: "Turn a pursuit section into a slide spec (titles of three words or fewer, message in subtitles, stamps, evidence tags) for the firm's deck builder."
---

# Niche Consulting exec offering (deck spec)

Use this skill when a pursuit artefact needs slides: executive summary, architecture, journeys, plan, team, partners, pricing or trust.

## Workflow

1. Brief: audience, objective and the ask. Ask once only if the audience or objective is missing.
2. Pick the section from the 14-section response structure and its must-haves.
3. Draft one slide per idea: a title of three words or fewer, a subtitle that carries the message, 3–5 body points, and a stamp where the content is not validated.
4. Hand the spec to the deck builder on the firm's master template, then run the brand guardian.

## Spec schema

```json
{"section": 13, "title": "Commercials and value", "slides": [
  {"title": "Three clear options", "subtitle": "Option 2 balances scope and cost", "body": ["..."], "stamp": "INDICATIVE", "evidence": ["rate card"]}
]}
```

The builder scripts, master template, icons and fonts stay in the original exec-offering package; the app produces the spec.
