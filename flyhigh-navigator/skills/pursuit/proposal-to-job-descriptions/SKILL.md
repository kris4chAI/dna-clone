---
name: "proposal-to-job-descriptions"
description: "Generate role-by-role job descriptions from a proposal, or from a user's role list mapped to standard data & analytics offering playbooks, with must-haves flagged for onshore, nearshore and offshore."
---

# Proposal to Job Descriptions

Write one job description (JD) for each role on an engagement. Base each JD on the engagement's scope, deliverables, tech stack and timeline, and flag must-have skills by location tier: Onshore, Nearshore or Offshore. Every JD follows the house style shown in the **Reference JDs** at the end of this file.

## Step 0: Pick the input mode

**Mode A, proposal present.** A proposal is attached, linked or pasted (SOW, RFP response, deck, estimate). Use the proposal as the source of truth and go to Step 1A.

**Mode B, no proposal.** Build the engagement context from:
1. **The user's input:** the list of roles, plus any context they give (client, industry, objective, platform, timeline, locations, counts, seniority).
2. **The standard data and analytics offerings and playbooks** in the Offering playbooks section below. Use them to determine fit and to fill in scope, deliverables, phases and tech stack.

In Mode B:
- If the user gave no role list and no proposal, ask for the roles in one short question. Include the role title and, where known, location, count and seniority.
- Don't ask anything else up front. Use defaults and state each assumption.

## Step 1A: Extract facts from the proposal (Mode A)

Extract the text with the matching file skill (pdf, docx, pptx, xlsx). Read the whole document; team tables often sit in an appendix or on a commercials slide. Build an internal fact sheet:

| Field | What to capture |
|---|---|
| Client and context | Industry, business problem, current-state pain points |
| Scope | In-scope items, out-of-scope items, assumptions |
| Deliverables | Each deliverable or milestone, with its phase or sprint |
| Phases and timeline | Discovery, build, test, deploy, hypercare; duration of each |
| Tech stack | Platforms, clouds, lakehouse, AI/ML tooling, agentic/AI-assisted engineering tooling, languages, DevOps, testing tools |
| Delivery model | Agile/SAFe, sprint length, governance cadence, client governance standards (for example, an enterprise data office) |
| Team structure | Each role: title, count, location, allocation %, phase, seniority |

If the proposal is thin in places (for example, it has no tech stack or no team table), fill those gaps from the closest offering playbook. Mark each filled item **[From playbook]**.

## Step 1B: Determine the offering fit (Mode B)

1. **Score the fit.** Compare the user's roles and any stated objective or platform against each offering playbook below. A playbook fits when its core roles overlap with the user's roles and its objective matches anything the user said.
2. **Choose the primary offering.** Pick the best-fit playbook. If two fit about equally well (for example, a lakehouse migration plus GenAI use cases), combine them as primary plus secondary.
3. **Build the fact sheet** from the chosen playbook(s): scope, deliverables, phases, default timeline and default tech stack. Override any default with what the user stated. Mark every playbook-derived item **[From playbook]**.
4. **Assign locations.** If the user didn't give locations, use the playbook's default tier for each role and mark it **[Location inferred]**.
5. **Run the fit check.** Record:
   - roles the user listed that the playbook doesn't typically need, and why they might still fit;
   - core playbook roles missing from the user's list, as possible gaps;
   - the fit rating: Strong (most core roles present), Partial, or Weak.

Put the fit check under "Gaps and assumptions" in the output.

## Offering playbooks (standard data and analytics)

Default tier codes: **On** = onshore, **Near** = nearshore, **Off** = offshore. Default stack choices are placeholders; use the client's platform when it is known.

### 1. Data platform modernization / lakehouse migration
- **Objective:** move legacy EDW, Hadoop or on-prem ETL to a cloud lakehouse.
- **Phases (16-24 weeks):** Discovery and assessment (3-4 weeks), Foundation and landing zone (3-4), Migration waves (8-14), Cutover and hypercare (2-4).
- **Deliverables:** current-state assessment, target architecture, migration factory and wave plan, automated code conversion, data validation and reconciliation reports, cutover runbook, decommission plan.
- **Stack:** Databricks, Snowflake or Microsoft Fabric; Delta/Iceberg; Unity Catalog or Horizon; dbt; Airflow, Workflows or DataOps.live; Terraform; AI-assisted code-conversion accelerators.
- **Core roles:** Engagement/Delivery Lead (On), Data Architect (On), Migration Lead (Near), Data Engineers (Off), Data Validation/QA Engineer (Off), DevOps/Platform Engineer (Near/Off).

### 2. Data engineering and pipeline build
- **Objective:** build new batch and streaming pipelines and a medallion data model.
- **Phases (12-16 weeks):** Discovery (2), Design (2), Build sprints (6-10), Test and deploy (2).
- **Deliverables:** source-to-target mappings, medallion layers (Bronze, Silver, Gold), ingestion framework, orchestration, data quality checks, CI/CD, operations runbook.
- **Stack:** Spark/PySpark or Snowpark, SQL, stored procedures, Kafka or Event Hubs, dbt, Airflow or DataOps.live, lakehouse platform, DQ tooling.
- **Core roles:** Tech Lead (On), Data Architect (On/Near), Senior Data Engineer (Near), Data Engineers (Off), QA Engineer (Off).

### 3. BI and analytics modernization
- **Objective:** rationalize reports, build a semantic layer, migrate dashboards and enable self-service.
- **Phases (10-16 weeks):** Report inventory and rationalization (2-3), Semantic model (3-4), Dashboard migration waves (4-8), Adoption (1-2).
- **Deliverables:** report rationalization matrix, KPI dictionary, semantic model, migrated dashboards, self-service guidelines, training.
- **Stack:** Power BI, Tableau or Looker; semantic layer (dbt metrics, Snowflake semantic views, Fabric semantic models); lakehouse SQL; Copilot, Cortex Analyst or other GenAI BI assistants.
- **Core roles:** Analytics Lead / BA (On), BI Architect (On/Near), BI Developers (Off), Data Engineer (Off), QA/UAT Analyst (Off).

### 4. Data governance, quality and catalog
- **Objective:** establish ownership, lineage, data quality and access policy.
- **Phases (10-14 weeks):** Assess (2-3), Operating model design (2-3), Tool implementation (4-6), Rollout (2).
- **Deliverables:** governance operating model, RACI, business glossary, catalog and lineage, DQ rules and scorecards, access policies, stewardship playbook.
- **Stack:** Unity Catalog, Snowflake Horizon, Purview, Collibra or Alation; DQ tooling; policy-as-code.
- **Core roles:** Governance Lead (On), Data Governance Analyst (Near), Catalog/DQ Engineers (Off), Data Steward enablement (On).

### 5. AI / ML and GenAI use cases
- **Objective:** take prioritized ML or GenAI use cases from idea to production.
- **Phases (8-16 weeks):** Use-case discovery and value sizing (2), MVP prototype (3-4), Productionize (3-6), Monitor and scale (2-4).
- **Deliverables:** use-case backlog and value sizing, data readiness assessment, MVP, evaluation harness, RAG or agent pipelines, MLOps/LLMOps pipeline, guardrails, monitoring.
- **Stack:** Databricks Mosaic AI, Snowflake Cortex AI, Azure AI Foundry, AWS Bedrock or Vertex AI; vector search; MLflow; evaluation frameworks; agent frameworks and Model Context Protocol (MCP); vibe-coding and AI-assisted development tools.
- **Core roles:** AI Solution Lead (On), ML/AI Architect (On/Near), ML Engineers (Near/Off), Data Scientists (Off), Data Engineer (Off), MLOps Engineer (Off).

### 6. Data products / data mesh enablement
- **Objective:** stand up domain-owned data products on a shared self-serve platform.
- **Phases (14-20 weeks):** Domain discovery (3), Platform blueprint (3), Pilot data products (6-10), Scale-out playbook (2-4).
- **Deliverables:** domain map, data product canvas, data contracts, machine-readable data product specifications, self-serve platform templates, pilot products, federated governance model.
- **Stack:** lakehouse platform, data contracts, catalog, IaC templates, CI/CD.
- **Core roles:** Data Product Owner / Strategist (On), Platform Architect (On), Domain Data Engineers (Near/Off), Platform Engineers (Off).

### 7. Data platform managed services (run and optimize)
- **Objective:** run, support and optimize a data platform under SLAs.
- **Phases:** Transition (4-6 weeks), Steady state (ongoing), Continuous improvement.
- **Deliverables:** transition plan, SLA and KPI framework, incident and problem management, FinOps cost optimization, monthly service reviews.
- **Stack:** lakehouse platform, observability tooling, ITSM (ServiceNow), FinOps tooling.
- **Core roles:** Service Delivery Manager (On), Platform SME (Near), L2/L3 Support Engineers (Off), FinOps Analyst (Off).

### 8. Agentic data engineering (AI-automated engineering lifecycle)
- **Objective:** automate the data engineering lifecycle (discover, impact analysis, build, test, deploy) with agentic workflows and specification-driven development (SDD).
- **Phases (12-20 weeks):** Lifecycle mapping and automation candidates (2-3), Agent harness and SDD foundation (3-4), Agentic pattern build-out alongside product delivery (6-10), Scale and govern (2-3).
- **Deliverables:** catalog of manual tasks mapped to agentic patterns, agent harness and workflows, machine-readable data product specifications, automated impact analysis and test generation, delivered data products, governance guardrails for agent output.
- **Stack:** the platform's native AI coding agent (for example, Snowflake Cortex Code / CoCo CLI), Cortex AI or equivalent LLM services, MCP, RAG, SQL/Python, dbt, DataOps.live or an equivalent DataOps orchestrator.
- **Core roles:** AI Architect (On), Agentic Engineering Lead (On/Near), Agent Data Engineers (Near/Off), Data Engineers (Off), QA/Test Automation Engineer (Off).
- **Overlay rule:** if any other playbook's engagement uses agentic or AI-automated delivery, add this playbook as the secondary offering. Give senior data engineering and architect roles a **Primary Focus** on the agentic framework and a **Secondary Focus** on lifecycle delivery, as in the Reference JDs.

If the user names an offering that isn't listed, adapt the closest playbook and state which one you adapted.

## Step 2: Apply location-tier must-haves

Each JD gets the must-have block for its tier. Rewrite each item in the engagement's terms: name the actual platform, deliverables and audience instead of copying the generic wording.

### Onshore must-haves

1. Owns technical delivery of the project and manages stakeholders.
2. Asks clarifying questions that refine scope, features and user stories.
3. Demonstrates the technical solution to executive audiences.
4. Owns end-to-end implementation, from discovery to deployment.
5. Is fluent in vibe-coding / AI-assisted development tools and lakehouse-native AI tooling, and can sequence work into initiatives, epics and sprints.

### Nearshore must-haves

Nearshore is the time-zone-aligned bridge between onshore and offshore. Default must-haves (the user may override them):

1. Works in real time during client hours: runs or joins daily stand-ups and sprint ceremonies, and keeps onshore and offshore in sync.
2. Translates high-level design into low-level design and owns a module or workstream hands-on.
3. Communicates directly with client product owners and tech leads, and demos sprint increments.
4. Supports integration with client environments, release, cutover and rapid triage during deployment and hypercare.
5. Is fluent in AI-assisted development tools and the engagement's lakehouse platform, and enforces engineering standards across the distributed team.

### Offshore must-haves

1. Handles low-level design, system testing and integration testing.
2. Mentors junior engineers and improves team productivity.
3. Rapidly prototypes a solution MVP and showcases it to onshore and client tech leads.
4. Understands the outcome an epic is meant to achieve and contributes to product requirements, system requirements, backlog grooming and refinement.
5. Builds low-level harnesses (test, evaluation and scaffolding harnesses) for app, data and AI use cases.

### Calibrate by seniority

| Band | Default experience | Tier must-haves |
|---|---|---|
| Architect (Data / AI / Platform) | 14+ years | All five apply |
| Lead / Manager | 12+ years | All five apply |
| Senior | 10+ years | All five; mentoring and stakeholder items scoped to the IC's own work |
| Mid | 5-8 years | Delivery and technical items only; leadership items go to Growth expectations |
| Associate | 2-5 years | Technical items only; leadership items go to Growth expectations |

- **Specialist roles** (for example, QA, data scientist or DevOps): keep the tier items that fit the specialism and reword them for it, such as "integration test harness" for QA or "model evaluation harness" for a data scientist.
- If seniority isn't given, infer it from the title (Architect, Lead, Senior, Associate) and mark it **[Seniority inferred]**.

## Step 3: Write each JD in the house style

Write one JD per unique **role + location** pair. Match the Reference JDs' style:

- **Specific title.** If the role is agentic or specialized, say so in the title (for example, "Agent Data Engineer" or "AI Architect" rather than just "Data Engineer" or "Architect").
- **Primary and Secondary Focus lines.** One line each: what the role spends most of its time on, and what it also delivers.
- **Experience headline.** Years, level and the signature platform or tool (for example, "10+ years · Senior Data Engineer with Snowflake Cortex Code experience" or "14+ years · AI Architect").
- **Key Responsibilities.** 6-9 action-led bullets that name actual tools, artifacts and client standards. Each bullet traces to a scope item or deliverable.
- **Essential Skills.** 5-7 bullets, each starting with a bold category label followed by a colon (for example, **AI/GenAI Engineering:**, **Agentic Frameworks:**, **Core Engineering Competencies:**, **Platform Expertise:**, **Data Product Lifecycle:**). Name concrete tools and concepts.
- **Platform vocabulary.** Use the platform's own terms. For Snowflake, that means Cortex AI, Cortex Code, Snowpark, stored procedures, dynamic tables, streams and tasks, Horizon, dbt and DataOps.live. For Databricks, it means Unity Catalog, Delta Live Tables / Lakeflow, Workflows, Mosaic AI and Databricks Asset Bundles.

### Differentiate architects from engineers

An architect and an engineer on the same engagement share the same focus areas and skill categories. The difference is the level of ownership. Never give an architect the same bullets as the engineer with only the years changed. Raise each item one level:

| Engineer verb (builds) | Architect verb (designs, governs) |
|---|---|
| Develop and refine agentic workflows | Design the agentic framework and harness architecture; set the standards engineers build to |
| Integrate LLMs and Cortex AI models | Select models and integration patterns; define evaluation, cost and guardrail policies |
| Build SDD capabilities | Define the SDD specification standard and data product contract schema |
| Convert manual tasks into agentic patterns | Prioritize the automation roadmap and decide which lifecycle stages get automated, and when |
| Oversee stored procedures, dbt models, DataOps.live | Own the reference architecture for the engineering layer and medallion tiers; review designs |
| Maintain code quality, align with EDO governance | Own the alignment with EDO governance, security and access models; approve exceptions |
| Contribute to platform-agnostic frameworks | Define the platform-agnostic framework, its portability rules and the integration boundaries |

Architect JDs also add two Essential Skills categories: **Architecture & Design** (reference architectures, solution design, non-functional requirements) and **Governance & Security** (access models, lineage, policy, responsible AI). The architect must still be hands-on enough to prototype the framework.

Template:

```
## <Role Title> | <Onshore / Nearshore / Offshore> | <count> position(s)

**Primary Focus:** <one line>
**Secondary Focus:** <one line>
**Experience:** <years>+ years · <level> <role> with <signature platform/tool> experience
**Allocation:** <% and phases>  ·  **Reports to:** <role>

### Key Responsibilities
- <action verb> ... (6-9 bullets, tool- and deliverable-specific)

### Essential Skills
- **<Category>:** <concrete skills and tools>
- ... (5-7 categories)

### Location Must-Haves [MUST-HAVE · <Tier>]
- <calibrated tier must-have, reworded in engagement terms>
- ...

### Good-to-Have
- <certifications, adjacent tools, domain exposure>

---
*Hiring notes (internal, remove before posting)*
- Source: <Proposal | User input + <Offering> playbook(s)>
- Inferred: <location / seniority / stack items>
- Success measures (30/60/90): <outcomes tied to phases>
- Interview focus: <3-5 probes or live exercises that test the flagged must-haves>
```

The section above the hiring-notes line must be ready to post as-is. Never invent client-specific facts such as a client name, systems or numbers. In Mode B, keep context at the offering level unless the user gave specifics.

## Step 4: Add summary views

Before the individual JDs, add:

1. **Engagement basis:** in Mode A, the proposal title. In Mode B, the primary and secondary offering playbooks, the fit rating and a one-line rationale.
2. **Staffing summary table:** role, tier, count, allocation, phase, seniority, and which fields were inferred.
3. **Must-have matrix:** roles as rows; the five tier must-haves plus the top technical skills as columns; mark each cell as Must, Good-to-have or N/A.
4. **Gaps and assumptions:** the fit check (Mode B), missing core roles, unclear locations, playbook-derived items, and open questions.

## Output

- **Default:** one shareable document containing the summary views and then every JD, grouped by tier in the order Onshore, Nearshore, Offshore. Use the session's native doc/document format.
- If the user asks for Word, use the docx skill (niche consulting-docx for Niche Consulting branding). If they ask for one file per JD, produce separate files and bundle them in a single .zip.
- If the user asks for Excel or a tracker, also provide the must-have matrix as .xlsx.
- End with a short note naming the input mode, the playbook(s) used, any inferred locations or seniority, and the open questions.

## Quality checks before delivering

- Every role in the team structure (proposal or user list) has a JD. Suggested extra roles appear only under gaps; don't write JDs for them unless the user asks.
- Every responsibility traces to a scope item or deliverable from the proposal or playbook. Remove generic filler.
- Every JD has Primary/Secondary Focus lines, an experience headline and categorized Essential Skills, matching the Reference JDs' depth and specificity.
- Architect and engineer JDs on the same engagement are clearly differentiated, not copies with different years.
- Tier flags match each role's location, and junior roles aren't over-flagged.
- Tech skills come from the proposal, the user's input or the playbook stack, not a generic list.
- Playbook-derived and inferred items are labeled in the hiring notes, never in the postable section.
- Use consistent role titles across the summary, matrix and JDs.

## Reference JDs (house style exemplars)

Use these for tone, structure and level of specificity. Don't copy their content into JDs for other platforms or engagements.

### Reference 1: Snowflake Senior Data Engineer (agentic)

```
## Agent Data Engineer

**Primary Focus:** Development, orchestration and maintenance of the agentic framework that automates the engineering lifecycle.
**Secondary Focus:** Technical execution and delivery of the data engineering lifecycle (Discover, Build, Test, Deploy).
**Experience:** 10+ years · Senior Data Engineer with Snowflake Cortex Code (CoCo) experience

### Key Responsibilities
- Develop and refine agentic workflows using the Snowflake Cortex Code (CoCo) harness.
- Integrate LLMs, Cortex AI models and orchestration logic to automate the discovery, impact analysis, build and testing stages.
- Build Specification Driven Development (SDD) capabilities, creating machine-readable instructions for data products.
- Collaborate with data engineers to convert manual engineering tasks into autonomous agentic patterns.
- Drive technical execution for data product delivery and datasets optimized for enterprise consumption.
- Oversee core engineering layer components, including SQL stored procedures, dbt models and DataOps.live.
- Maintain code quality and minimize defects while ensuring full alignment with EDO governance standards.
- Contribute to automated engineering lifecycles, from ingestion through deployment, via platform-agnostic frameworks.

### Essential Skills
- **AI/GenAI Engineering:** Deep experience with Cortex skills, LLM integration and Retrieval-Augmented Generation (RAG) concepts.
- **Agentic Frameworks:** Proficiency in building and maintaining agentic workflows (for example, CoCo CLI, Model Context Protocol).
- **Foundational Knowledge:** Solid background in data engineering (SQL, Python) to bridge AI capabilities and data platform requirements.
- **Core Engineering Competencies:** Advanced technical mastery of SQL, dbt models and DataOps.live (DOL) orchestration.
- **Platform Expertise:** Comprehensive proficiency across the Snowflake ecosystem and its integrated service offerings.
- **Data Product Lifecycle:** Strategic command of multi-tier architectures (Bronze, Silver, Gold) and the management of enterprise-grade data products.
```

### Reference 2: Snowflake Data / AI Architect (agentic)

The user's architect sample has the same Primary Focus, Secondary Focus, Key Responsibilities and Essential Skills as Reference 1. The differences are:
- **Experience:** 14+ years · AI Architect
- **Role level:** architect

When writing an architect JD for an agentic Snowflake engagement, start from Reference 1's focus areas and skill categories. Apply 14+ years and the AI Architect title, then raise every bullet to architect-level ownership using the "Differentiate architects from engineers" table.