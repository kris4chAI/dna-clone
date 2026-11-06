---
name: "rfp-section-loop"
description: "Improve RFP response sections with a generate, score and revise loop until each reaches 90% of the rubric with all must-haves, or escalate the inputs needed."
---

# RFP section loop (loop engineering)

Use this skill when the user asks to make a proposal section, or the whole response, better until it meets the rubric threshold. It combines `rfp-section-builder` (generator) and `rfp-section-rubric` (evaluator).

## Set up

1. Run `rfp-section-builder` in extract mode if no `structure.md` exists.
2. Choose sections: the ones the user names, otherwise all 14, ordered by weight and gap (largest weighted gap first).
3. Get a baseline: run `rfp-section-rubric` on each chosen section with a fresh agent. Save `loop-log.md` in the pursuit folder with the baseline table.

## The loop (per section, at most four rounds)

1. **Target:** threshold 90 points AND every must-have met.
2. **Revise:** run `rfp-section-builder` on that section with the evaluator's ranked fix list. Fix missing must-haves first, then the criteria with the most points lost. Change nothing the fix list does not name.
3. **Render and self-check:** render the changed slides; fix overlaps, brand breaks and number conflicts with other sections before scoring. Validate the file.
4. **Rescore with fresh eyes:** a new evaluator agent with only the slides, inputs and rubric. No anchoring on the previous score or the builder's notes.
5. **Regression guard:** compare every criterion with the previous round. Keep the best-scoring version. Reject any revision that lowers a criterion by more than one anchor, and revert it.
6. **Stop or continue:**
   - Stop with PASS at 90 or more with all must-haves.
   - Stop with PLATEAU if the score gains less than 2 points over two rounds.
   - Stop with BLOCKED if the remaining fixes need client, legal or reference input. Insert labelled placeholders (INDICATIVE, FOR JOINT REVIEW, bracketed values, [client input]) so nothing is invented, and list each input needed with an owner and a due date.
7. **Log:** append the round's scores, fixes made and evaluator notes to `loop-log.md`.

## Whole-deck pass

After the sections, rebuild the cover, agenda and close from the section titles. Rerun the evaluator on the full deck for cross-section consistency, then `rfp-win-scorecard` to update stakeholder scores. Save over the working deck, verify by checksum, and report.

## Guidelines

- Separate generator and evaluator contexts every round; the evaluator never sees the builder's reasoning.
- Evidence over opinion: every point awarded cites slide text.
- Smallest change that recovers the most points; do not rewrite strong slides.
- Never raise a score by removing honesty labels or by asserting unvalidated facts.
- Budget: at most four rounds per section; tell the user before a full 14-section run, since it uses many agent calls.

## Report to the user

A table per section: baseline, final score, rounds, status (PASS, PLATEAU, BLOCKED), and the inputs still needed. Then the weighted overall score before and after.