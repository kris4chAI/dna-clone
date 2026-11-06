# Persona lens

Each user picks a persona. The persona maps to a lens, and the lens decides what the UI shows and what the API allows.

| Lens | Personas | Sees |
|---|---|---|
| **Pursuit** | Pursuit lead, client partner, proposal manager, solution architect (pre-sales), experience lead, deal lead and finance, Legal, alliance lead | All 9 pursuit stages, pursuit kit, win room, response quality (all sections), solution content, pursuit skills |
| **Delivery** | Delivery lead, product owner, architecture lead, platform engineer, migration lead, data engineer, BI lead, QA lead, release manager, platform operations | Implementation workflow, toolkit catalog, solution content, all 46 Snowflake skills, the delivery playbook, plan and execute, team and RACI, plus the **shared final pursuit stages** 5, 8, 9 |
| **PMO** | AI program manager, AI Champion (AI Native data lead), client program head, PMO analyst, data governance lead, FinOps and commercial controller | The program office: delivery playbook, readiness scorecard, plan and execute, unit-effort estimator, AI use-case matrix, KPI scorecard, governance and RAID, team and RACI; the implementation workflow; solution content; pursuit stages 5 and 9; the PMO skills plus the planning and release skills |
| **Sales** *(coming soon)* | — | Sales strategy and pipeline generation. Listed in the picker but not yet available |

## Shared final pursuit stages

| Stage | Shared with | Why |
|---|---|---|
| 5 · Delivery plan and effort (G4) | Delivery, PMO | The delivery lead signs zero-variance effort; the loading becomes the mobilization baseline the PMO plans from |
| 8 · Assemble, brand and red team (G7) | Delivery | Delivery reviewers score the engineering, delivery plan and team sections for feasibility |
| 9 · Submit, orals and learn (G8) | Delivery, PMO | Delivery leads present in orals; the hand-over feeds implementation Discover and the PMO's Align phase |

Within shared stages, delivery personas can also use the pursuit skills that belong to them: the orchestrator (shared stages only), the section rubric, loop and builder, job descriptions, the brand guardian and the deck spec. The PMO uses the orchestrator and job descriptions. The win scorecard and the commercials model stay with the pursuit lens.

## Enforcement

- Every API call carries `X-Persona`. Without it the API returns **401**; outside the lens it returns **403**, naming the lens that owns the resource. The chat guide filters its retrieval the same way.
- Lenses live in the `lens` table; personas in `lens_role`. The rules live in `access_rule` (resource = `screen`, `pursuit_stage` or `skill`) with a `lenses` array, so you can change them without code. For example:

  ```sql
  UPDATE access_rule SET lenses = lenses || 'delivery' WHERE resource = 'pursuit_stage' AND code = 'commercials';
  ```

- **Adding the sales lens later:** set `available = TRUE` on the `sales` row in `lens`, add its personas to `lens_role`, add `'sales'` to the `lenses` of the screens it should open, and add its screens to the UI. In the seed this is `LENSES`, `LENS_ROLES` and `SCREEN_ACCESS` in `backend/app/pursuit_data.py`.
- The persona picker is a role lens, not authentication. For production, put SSO in front of the app and derive `X-Persona` from identity-provider groups.
