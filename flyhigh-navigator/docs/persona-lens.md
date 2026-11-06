# Persona lens

Each user picks a persona. The persona maps to a lens, and the lens decides what the UI shows and what the API allows.

| Lens | Personas | Sees |
|---|---|---|
| **Sales** | Pursuit lead, client partner, proposal manager, solution architect (pre-sales), experience lead, deal lead and finance, Legal, alliance lead | All 9 pursuit stages, pursuit kit, win room, response quality (all sections), solution content, pursuit skills |
| **Delivery** | Delivery lead, product owner, architecture lead, platform engineer, migration lead, data engineer, BI lead, QA lead, release manager, platform operations | Implementation workflow, toolkit catalog, solution content, all 46 Snowflake skills, plus the **shared final pursuit stages** |

## Shared final pursuit stages

| Stage | Why it is shared |
|---|---|
| 5 · Delivery plan and effort (G4) | The delivery lead signs zero-variance effort; the loading becomes the mobilization baseline |
| 8 · Assemble, brand and red team (G7) | Delivery reviewers score the engineering, delivery plan and team sections for feasibility |
| 9 · Submit, orals and learn (G8) | Delivery leads present in orals and receive the handover into implementation Discover |

Within shared stages, delivery personas can also use the pursuit skills that belong to them: the orchestrator (shared stages only), the section rubric, loop and builder, job descriptions, the brand guardian and the deck spec. The win scorecard and the commercials model stay sales-only.

## Enforcement

- Every API call carries `X-Persona`. Without it the API returns **401**; across lenses it returns **403**. The chat guide filters its retrieval the same way.
- The rules live in the `access_rule` table (resource = `screen`, `pursuit_stage` or `skill`), so you can change them without code. For example:

  ```sql
  UPDATE access_rule SET delivery = TRUE WHERE resource = 'pursuit_stage' AND code = 'commercials';
  ```

- The persona picker is a role lens, not authentication. For production, put SSO in front of the app and derive `X-Persona` from identity-provider groups.
