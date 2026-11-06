"""Seed content for FlyHigh Navigator.

Source: Niche Consulting Proposal to ABC Retail - FlyHigh v.6
  - Slides 18-20  persona journeys
  - Slides 21-24  insight dashboards
  - Slides 25-29  logistics data model, schemas, KPI library
  - Slides 30-37  engineering accelerators: agents, skills, tools, frameworks
Everything here is a starting point. All rows are editable from the UI ("curation").
"""

# ---------------------------------------------------------------------------
# Delivery phases
# ---------------------------------------------------------------------------
PHASES = [
    {"num": 1, "name": "Mobilize + discover", "months": "Months 1-2", "output": "Lineage, prioritized waves, PRDs"},
    {"num": 2, "name": "Build frameworks", "months": "Months 1-3", "output": "Platform and frameworks ready"},
    {"num": 3, "name": "Pilot + wave build", "months": "Months 3-8", "output": "Converted code, Gold models, Tableau"},
    {"num": 4, "name": "SIT + UAT", "months": "Months 4-9", "output": "Test evidence and reconciliation"},
    {"num": 5, "name": "Cut-over + hypercare", "months": "Months 9-10", "output": "Monitored go-live and handover"},
]

# ---------------------------------------------------------------------------
# Component catalogue categories
# ---------------------------------------------------------------------------
TOOL_CATEGORY = {
    "Claude Code": "Agentic coding", "GitHub Copilot": "Agentic coding", "Cursor": "Agentic coding",
    "VS Code + Claude Code": "Agentic coding",
    "Cortex Code": "Snowflake-native", "Cortex Agents": "Snowflake-native", "Snowflake CLI": "Snowflake-native",
    "Cortex Analyst": "Snowflake-native", "Semantic views": "Snowflake-native", "Snowflake DMFs": "Snowflake-native",
    "Snowpipe · tasks": "Snowflake-native", "Query profile": "Snowflake-native", "Resource monitors": "Infrastructure",
    "Terraform": "Platform & policy", "dbt / schemachange": "Platform & policy", "OPA / Checkov": "Platform & policy",
    "schemachange": "CI/CD", "GitHub Actions": "CI/CD", "GitHub pull request": "CI/CD", "GitHub PR checks": "Quality",
    "GitHub": "CI/CD", "GitHub Releases": "CI/CD", "Semantic versioning": "CI/CD",
    "SQLFluff": "Quality", "dbt tests": "Quality", "PR templates": "Quality",
    "Zero-copy clones": "Infrastructure", "Jira": "Work management", "JIRA / Xray": "Work management",
    "IdP CLI": "Platform & policy", "Tableau Cloud": "BI", "Data Harness": "Niche Consulting accelerators",
    "Platform Assurance": "Niche Consulting accelerators", "Markdown in repo": "Documentation",
    "Recorded sessions": "Enablement", "Handover sign-off": "Enablement",
}

# Accelerator services = Niche Consulting frameworks
FRAMEWORKS = [
    ("Discovery and Design", "Estate, lineage and ~400 reports profiled."),
    ("Foundation", "Zones, RBAC and masking as code."),
    ("Code Promotion", "CI/CD on GitHub and Terraform; release, rollback and runbooks."),
    ("Data Harness", "Requirement in, pipeline out; monitoring, catalog and lineage."),
    ("Platform Migration", "ODI, PL/SQL and OAC logic converted."),
    ("BI Modernization", "Rationalize, convert, generate, validate."),
    ("Platform Assurance", "Data, report and < 5 s checks."),
]

# ---------------------------------------------------------------------------
# Workflow stages: discovery -> monitoring
# Each agent: name, capability, description, skills, tools
# ---------------------------------------------------------------------------
STAGES = [
    {
        "code": "discover", "seq": 1, "name": "Discover", "phase": 1, "slide": 31,
        "lead_role": "Product Owner", "mode": "Human-gated, iterative",
        "gate": "G1 · PRD approved",
        "summary": "Problem, users, data, goals, constraints and existing capabilities understood before choosing a solution. The estate, lineage and ~400 reports are profiled.",
        "key_steps": [
            "Describe the need in one prompt, with persona and scope if known",
            "Answer clarifying questions: pain points, journey, outcomes, data",
            "Confirm the persona against the catalogue; log any gap",
            "Map each data need to a PI data concept or record a gap",
            "Confirm numeric targets with the business, then raise the PR",
        ],
        "agents": [
            {"name": "PRD Agent", "capability": "Discover", "description": "Drafts the product requirements document from one prompt and clarifying questions.",
             "skills": ["/pi-define-requirements", "/pi-commit-and-raise-pull-request"], "tools": ["VS Code + Claude Code", "GitHub pull request"]},
            {"name": "Discovery agent", "capability": "Estate discovery", "description": "Profiles the estate, lineage and reports using Horizon catalog.",
             "skills": [], "tools": ["Claude Code"]},
            {"name": "Estate Analyzer agent", "capability": "Reverse engineering + planning", "description": "Builds the dependency graph and sequenced wave plan with Snowflake AIM.",
             "skills": ["/discover", "/plan-waves"], "tools": ["Claude Code"]},
        ],
        "frameworks": ["Discovery and Design"],
        "snowflake": ["Snowflake AIM assessment and planning", "Horizon catalog for discovery", "AIM dependency graph"],
        "outputs": ["PRD", "Lineage", "Prioritized waves"],
        "prompts": ["What does the PRD Agent do?", "Which personas should I confirm in Discover?"],
    },
    {
        "code": "design", "seq": 2, "name": "Design", "phase": 1, "slide": 31,
        "lead_role": "Architecture Lead", "mode": "Human-gated, iterative",
        "gate": "G2 · Solution design approved",
        "summary": "Target behaviour, architecture, data models, interfaces, ownership and non-functional requirements.",
        "key_steps": [
            "Draft the design from the approved PRD",
            "Accept, edit or skip the proposed reviewers",
            "Run the checklist: PRD, standards and ADRs linked; decisions captured",
            "Review scope.yaml, the traceability map to Jira",
            "Reviewer approves; merge as the input to Decompose",
        ],
        "agents": [
            {"name": "Solution Design Agent", "capability": "Design", "description": "Drafts the solution design and scope.yaml traceability map from the approved PRD.",
             "skills": ["/pi-design-solution"], "tools": ["VS Code + Claude Code", "GitHub pull request"]},
        ],
        "frameworks": ["Discovery and Design"],
        "snowflake": ["Semantic Views"],
        "outputs": ["Solution design", "scope.yaml traceability map"],
        "prompts": ["What is in scope.yaml?", "Which data models feed the design?"],
    },
    {
        "code": "decompose", "seq": 3, "name": "Decompose", "phase": 1, "slide": 31,
        "lead_role": "Agent-generated", "mode": "No human gate",
        "gate": "No human gate",
        "summary": "The approved Solution Design becomes actionable Jira items and Component Change Specifications.",
        "key_steps": [
            "Read the merged design and scope.yaml",
            "Create Jira epics and stories per component",
            "Write a change specification per component",
            "Link every item back to the PRD and design",
            "Hand the backlog to the delivery pod",
        ],
        "agents": [
            {"name": "Decompose Agent", "capability": "Decompose", "description": "Turns the approved design into Jira items and component change specs.",
             "skills": [], "tools": ["Jira", "GitHub"]},
        ],
        "frameworks": [],
        "snowflake": [],
        "outputs": ["Jira items", "Component change specs"],
        "prompts": ["Why is there no gate on Decompose?"],
    },
    {
        "code": "foundation", "seq": 4, "name": "Foundation build", "phase": 2, "slide": 32,
        "lead_role": "Platform engineer", "mode": "Engineer-led supervision",
        "gate": "Peer review gate on every change",
        "summary": "A Snowflake foundation built as code, with isolated production, non-production and sandbox environments. The engineer holds the plan, invokes each skill and reviews every change.",
        "key_steps": [
            "Generate the zone model, schemas and lifecycle from the standard",
            "Translate legacy DDL to Snowflake objects and migrations",
            "Design the role hierarchy, grant sets and future grants",
            "Map IdP groups to roles and provision with SCIM",
            "Set SSO, key-pair, network policy and key management",
            "Author masking, row access and tag-based classification policies",
        ],
        "agents": [
            {"name": "Zone Mapper", "capability": "Data Layers & Zones", "description": "Zone model, schemas and lifecycle generated from the standard.", "skills": ["/map-zones", "/gen-zone-ddl"], "tools": ["Claude Code", "Terraform"]},
            {"name": "DDL Converter", "capability": "Data Model & DDL", "description": "Legacy DDL translated to Snowflake objects and migrations.", "skills": ["/convert-ddl", "/gen-migration"], "tools": ["Cortex Code", "schemachange"]},
            {"name": "RBAC Designer", "capability": "Role Based Access", "description": "Role hierarchy, grant sets and future grants per schema.", "skills": ["/design-rbac", "/gen-grants"], "tools": ["GitHub Copilot", "Terraform"]},
            {"name": "Identity Mapper", "capability": "Users & Groups", "description": "Group-to-role mapping and SCIM provisioning from the IdP.", "skills": ["/map-groups", "/gen-scim"], "tools": ["Claude Code", "IdP CLI"]},
            {"name": "Auth Designer", "capability": "Auth & Encryption", "description": "SSO, key-pair, network policy and key management settings.", "skills": ["/design-auth", "/gen-keypair"], "tools": ["Cortex Code", "Terraform"]},
            {"name": "Policy Author", "capability": "Object & Data Security", "description": "Masking, row access and tag-based classification policies.", "skills": ["/gen-masking", "/gen-rls"], "tools": ["Claude Code", "Snowflake CLI"]},
            {"name": "Ingestion agent", "capability": "Ingestion", "description": "Sets up Snowpipe and Iceberg ingestion patterns.", "skills": [], "tools": ["Snowflake CLI"]},
        ],
        "frameworks": ["Foundation", "Code Promotion", "Data Harness"],
        "snowflake": ["Horizon: RBAC, masking, row access", "Adaptive Compute warehouses", "Snowpipe and Iceberg tables"],
        "outputs": ["Platform and frameworks ready", "Prod, non-prod and sandbox environments"],
        "evidence": ["Catalog & lineage", "Peer review gates", "Access review evidence", "Run & cost telemetry", "Change audit trail"],
        "prompts": ["Which skills build RBAC?", "What tools can I swap for Claude Code?"],
    },
    {
        "code": "harness", "seq": 5, "name": "Data harness", "phase": 2, "slide": 35,
        "lead_role": "Data engineer + approver", "mode": "Validator + human approval gate",
        "gate": "Gate · validator + human approval",
        "summary": "Describe the data product once, build it anywhere: requirement in plain English, nine agents propose with evidence, one canonical spec, deterministic harnesses, Snowflake first.",
        "key_steps": [
            "Write the requirement in plain English (e.g. Customer 360 revenue data product)",
            "Nine agents propose with evidence",
            "Review the canonical HIR: typed, versioned, neutral",
            "Pass the validator and human approval gate",
            "Compile through deterministic harnesses to the Snowflake adapter",
            "Schedule the run; confirm Bronze/Silver/Gold rows and data products",
        ],
        "agents": [
            {"name": n, "capability": "Data Harness", "description": d, "skills": [], "tools": ["Data Harness"]}
            for n, d in [
                ("Requirement agent", "Captures the plain-English requirement and rules."),
                ("Data discovery agent", "Finds candidate sources and entities."),
                ("Data profiling agent", "Profiles sources and proposes evidence."),
                ("Pipeline design agent", "Proposes Bronze, Silver and Gold flow."),
                ("Transformation agent", "Proposes transformations and joins."),
                ("Data quality agent", "Proposes DQ rules and quarantine."),
                ("Governance agent", "Tags PII and proposes masking."),
                ("Testing agent", "Generates tests and reconciliation."),
                ("Validation agent", "Validates the canonical spec before the gate."),
            ]
        ],
        "frameworks": ["Data Harness"],
        "snowflake": ["Streamlit in Snowflake", "Snowpipe and Iceberg tables"],
        "outputs": ["Bronze / Silver / Gold pipeline", "DQ rules + quarantine", "Tests + reconciliation", "PII masking", "Documentation + lineage", "Scheduled job"],
        "harnesses": ["Ingestion + schema", "DQ + quarantine", "Transformation", "PII tags + masking", "Tests + reconciliation", "Observability + audit", "Docs + lineage"],
        "metrics": [["Rows in Silver", "10,959"], ["Rows in Gold", "7,764"], ["Gold data products", "3"], ["Scheduled run", "~3 min"]],
        "prompts": ["What are the nine harness agents?", "What does one requirement produce?"],
    },
    {
        "code": "migration", "seq": 6, "name": "Platform migration", "phase": 3, "slide": 33,
        "lead_role": "Niche Consulting migration lead", "mode": "Engineer-led supervision · human + AI",
        "gate": "Wave sign-off per component",
        "summary": "Delivered on Snowflake AIM: AI converts the code, DMS lands history in S3. Parity is proven by reconciliation, not by the converter.",
        "key_steps": [
            "Reverse engineering + planning", "Code conversion", "ETL conversion", "DW conversion",
            "Pipeline conversion", "BI conversion", "Data migration", "Cut-over",
        ],
        "steps": [
            {"name": "Reverse engineering + planning", "snowflake": ["AIM assessment", "Dependency graph", "Sequenced wave plan"], "agent": "Estate Analyzer agent", "skills": ["/discover", "/plan-waves"], "framework": "Discovery and Design"},
            {"name": "Code conversion", "snowflake": ["SnowConvert AI / AIM", "In-line warnings", "Pattern-based fixes"], "agent": "Code Converter agent", "skills": ["/convert-ddl", "/convert-procs"], "framework": "Platform Migration"},
            {"name": "ETL conversion", "snowflake": ["AIM ETL conversion", "Tasks · dynamic tables", "Snowflake-native workflows"], "agent": "Pipeline Converter", "skills": ["/convert-etl"], "framework": "Platform Migration"},
            {"name": "DW conversion", "snowflake": ["Bronze · Silver · Gold", "Iceberg tables", "AIM unit tests"], "agent": "Test Generator", "skills": ["/gen-unit-tests"], "framework": "Foundation"},
            {"name": "Pipeline conversion", "snowflake": ["Snowpipe · streams", "Kafka / CDC connectors", "Cortex Code"], "agent": "Ingest Repoint agent", "skills": ["/repoint-ingest"], "framework": "Code Promotion"},
            {"name": "BI conversion", "snowflake": ["Semantic views", "Cortex Analyst", "Live connections"], "agent": "BI Repoint agent", "skills": ["/repoint-bi"], "framework": "BI Modernization"},
            {"name": "Data migration", "snowflake": ["AIM data migration", "AIM data validation", "Zero-copy clones"], "agent": "Migration Runner", "skills": ["/load-initial", "/reconcile"], "framework": "Data Harness"},
            {"name": "Cut-over", "snowflake": ["Progress + issues log", "Query + pipeline history", "Resource monitors"], "agent": "Cutover Validator", "skills": ["/parallel-run"], "framework": "Code Promotion"},
        ],
        "agents": [
            {"name": "Code Converter agent", "capability": "Code conversion", "description": "Converts DDL and stored procedures with SnowConvert AI / AIM.", "skills": ["/convert-ddl", "/convert-procs"], "tools": ["Cortex Code", "Claude Code"]},
            {"name": "Pipeline Converter", "capability": "ETL conversion", "description": "Converts ODI SQL and non-SQL mappings to Snowflake-native workflows and dbt.", "skills": ["/convert-etl"], "tools": ["dbt / schemachange"]},
            {"name": "Test Generator", "capability": "DW conversion", "description": "Generates unit tests for Bronze, Silver and Gold.", "skills": ["/gen-unit-tests"], "tools": ["Cortex Code"]},
            {"name": "Ingest Repoint agent", "capability": "Pipeline conversion", "description": "Repoints Boomi and CDC ingestion to Snowflake.", "skills": ["/repoint-ingest"], "tools": ["Snowflake CLI"]},
            {"name": "BI Repoint agent", "capability": "BI conversion", "description": "Repoints OAC and Power BI to Tableau on semantic views.", "skills": ["/repoint-bi"], "tools": ["Tableau Cloud"]},
            {"name": "Migration Runner", "capability": "Data migration", "description": "Loads history and reconciles.", "skills": ["/load-initial", "/reconcile"], "tools": ["Snowflake CLI"]},
            {"name": "Cutover Validator", "capability": "Cut-over", "description": "Runs parallel runs and the cut-over runbook.", "skills": ["/parallel-run"], "tools": ["GitHub Actions"]},
            {"name": "Converter agent", "capability": "Platform Migration (accelerator)", "description": "ODI, PL/SQL and OAC logic conversion orchestrator.", "skills": ["/convert-ddl", "/convert-etl"], "tools": ["Claude Code", "Cortex Code"]},
        ],
        "frameworks": ["Platform Migration", "Discovery and Design", "Code Promotion", "Data Harness"],
        "snowflake": ["AIM code conversion (SnowConvert AI)", "AIM ETL conversion to dbt", "AIM data migration", "Semantic Views", "AIM shared migration state"],
        "outputs": ["Converted code", "Gold models", "Reconciliation evidence per wave"],
        "metrics": [["Avg. conversion rate", "+95%"], ["Faster code migration", "+88%"], ["Lines of code converted", "2.0B+"], ["Database objects converted", "46M+"]],
        "evidence": ["Reconciliation evidence per wave", "Catalog + lineage", "Peer review gates", "Access review evidence", "Run + cost telemetry", "Change audit trail"],
        "prompts": ["What are the 8 migration steps?", "Which skill reconciles data?"],
    },
    {
        "code": "bi", "seq": 7, "name": "BI modernization", "phase": 3, "slide": 36,
        "lead_role": "BI lead", "mode": "Brownfield (Track A) + Greenfield (Track B)",
        "gate": "Signed validation evidence",
        "summary": "Rationalize, convert, validate and generate: ~400 OAC, Power BI, Klipfolio and Excel reports migrated, plus new customer, HR executive and ops dashboards.",
        "key_steps": ["Report rationalization", "Semantic layer creation", "Report conversion", "Report generation", "Report validation"],
        "steps": [
            {"name": "Report rationalization", "track": "Brownfield", "snowflake": ["Snowflake usage history", "Horizon catalog"], "agent": "Report Analyzer agent", "output": "Rationalized inventory and wave backlog",
             "detail": "Metadata pulled from OAC, Power BI and Klipfolio into one catalog; usage, duplicate, aged and unused reports flagged; keep, merge, rebuild or retire decided."},
            {"name": "Semantic layer creation", "track": "Both", "snowflake": ["Semantic Views", "Cortex Analyst"], "agent": "Logic Extractor · Metric Normalizer", "output": "32-KPI certified library",
             "detail": "DAX, OAC logical SQL and Klipfolio formulas extracted and compared; conflicts resolved into one certified definition; published as semantic views, dbt metrics and OSI."},
            {"name": "Report conversion", "track": "Brownfield", "snowflake": ["Tableau Cloud", "Live connections"], "agent": "Report Converter agent", "output": "Tableau workbooks per wave",
             "detail": "Layouts, calculations, filters and parameters mapped to Tableau; UX lifted to FlyHigh standards; published through the Tableau REST API."},
            {"name": "Report generation", "track": "Greenfield", "snowflake": ["Semantic Views", "Tableau", "Cortex"], "agent": "Report Generator agent", "output": "WMS, HR and ops dashboards",
             "detail": "New dashboards drafted from PRDs, journey maps and semantic views; wireframe to workbook scaffold; Cortex Analyst for natural-language questions."},
            {"name": "Report validation", "track": "Both", "snowflake": ["Query Insights", "Tableau metadata"], "agent": "BI Validator", "output": "Signed validation evidence",
             "detail": "Numbers, filters and visuals compared with legacy or golden queries; RLS and masking tested per persona; filters under 5 seconds."},
        ],
        "agents": [
            {"name": "Report Analyzer agent", "capability": "Report rationalization", "description": "Builds one report catalog and classifies keep, merge, rebuild or retire.", "skills": [], "tools": ["Tableau Cloud"]},
            {"name": "Logic Extractor", "capability": "Semantic layer creation", "description": "Extracts DAX, OAC logical SQL and Klipfolio formulas.", "skills": [], "tools": ["Cortex Analyst"]},
            {"name": "Metric Normalizer", "capability": "Semantic layer creation", "description": "Resolves conflicting measures into one certified definition.", "skills": [], "tools": ["Semantic views"]},
            {"name": "Report Converter agent", "capability": "Report conversion", "description": "Maps layouts and calculations to Tableau workbooks.", "skills": ["/repoint-bi"], "tools": ["Tableau Cloud"]},
            {"name": "Report Generator agent", "capability": "Report generation", "description": "Drafts new dashboards from PRDs, journeys and semantic views.", "skills": [], "tools": ["Tableau Cloud", "Cortex Analyst"]},
            {"name": "BI modernization agents", "capability": "BI Modernization (accelerator)", "description": "Rationalize, convert, generate, validate.", "skills": [], "tools": ["Tableau Cloud"]},
        ],
        "frameworks": ["BI Modernization", "Platform Assurance"],
        "snowflake": ["Semantic Views", "Cortex Analyst", "Query Insights", "Horizon catalog"],
        "outputs": ["Rationalized inventory", "32-KPI certified library", "Tableau workbooks", "New dashboards", "Signed validation evidence"],
        "references": ["Cognos → Tableau · Dow Jones", "Qlik → Tableau · Citi", "Tableau Server → Cloud · Healthfirst", "MicroStrategy → Power BI · AstraZeneca (225+ reports, 30-40% faster)"],
        "prompts": ["How are the ~400 reports rationalized?", "Which dashboards are greenfield?"],
    },
    {
        "code": "assurance", "seq": 8, "name": "Platform assurance", "phase": 4, "slide": 34,
        "lead_role": "QA lead", "mode": "QA lead-led orchestration",
        "gate": "Every result and defect reviewed before sign-off",
        "summary": "Every migrated number reconciles to legacy, or the variance is explained and signed off before cut-over.",
        "key_steps": [
            "Check converted ODI mappings against legacy output",
            "Validate Bronze, Silver and Gold keys, SCD types and history",
            "Test CDC and file loads: freshness, late data, failure and rerun",
            "Compare Tableau with OAC and Power BI incl. row-level security",
            "Run golden queries against metric definitions",
            "Prove filters under 5 s on live data; size warehouses and cost",
        ],
        "agents": [
            {"name": "ETL Test Agent", "capability": "ETL Testing", "description": "Converted ODI mappings checked against legacy output: rules, lookups and counts.", "skills": ["/gen-etl-tests", "/reconcile"], "tools": ["dbt tests", "Snowflake DMFs"]},
            {"name": "DW Validator", "capability": "DW Testing", "description": "Bronze, Silver and Gold: keys, SCD types, history and constraints.", "skills": ["/gen-unit-tests", "/check-scd"], "tools": ["Cortex Code", "schemachange"]},
            {"name": "Pipeline Monitor", "capability": "Pipeline Testing", "description": "CDC and file loads: freshness, late-arriving data, failure and rerun.", "skills": ["/test-cdc", "/replay-load"], "tools": ["Snowpipe · tasks", "Data Harness"]},
            {"name": "BI Comparator", "capability": "BI Report Testing", "description": "Tableau against OAC and Power BI: numbers, filters and row-level security.", "skills": ["/compare-reports", "/test-rls"], "tools": ["Tableau Cloud", "Platform Assurance"]},
            {"name": "Semantic Tester", "capability": "Semantic Layer Testing", "description": "Metric definitions and golden queries return the legacy results.", "skills": ["/test-metrics", "/golden-queries"], "tools": ["Semantic views", "Cortex Analyst"]},
            {"name": "Performance Agent", "capability": "Performance Testing", "description": "Filters under 5 s on live data; concurrency, warehouse sizing and cost.", "skills": ["/load-test", "/tune-warehouse"], "tools": ["Query profile", "Resource monitors"]},
            {"name": "Test Case Generator", "capability": "Test design", "description": "Generates test cases from specs.", "skills": [], "tools": ["JIRA / Xray"]},
            {"name": "Test Data Agent", "capability": "Test design", "description": "Prepares test data.", "skills": [], "tools": ["JIRA / Xray"]},
            {"name": "Self Healing agent", "capability": "Execution + analytics", "description": "Repairs brittle tests during execution.", "skills": [], "tools": ["GitHub Actions"]},
            {"name": "Defect Triage agent", "capability": "Execution + analytics", "description": "Triages and routes defects.", "skills": [], "tools": ["JIRA / Xray"]},
            {"name": "Test Reporting agent", "capability": "Reporting", "description": "Publishes test evidence per gate.", "skills": [], "tools": ["GitHub Actions"]},
            {"name": "Reconciler", "capability": "SIT + UAT (accelerator)", "description": "Reconciles every converted object against Oracle.", "skills": ["/reconcile"], "tools": ["Snowflake DMFs"]},
        ],
        "frameworks": ["Platform Assurance"],
        "snowflake": ["AIM unit test generation", "AIM data validation", "Query Insights", "Performance Explorer"],
        "test_types": ["System test · end to end, per wave", "Integration test · source → Gold → Tableau", "Functional test · business rules + metrics", "Acceptance test · UAT with ABC Retail, signed off", "Performance test · < 5 s, concurrency, cost"],
        "outputs": ["Test evidence", "Reconciliation", "UAT sign-off"],
        "prompts": ["How is BI parity tested?", "What does the Performance Agent check?"],
    },
    {
        "code": "release", "seq": 9, "name": "Build & release", "phase": 5, "slide": 37,
        "lead_role": "Release manager", "mode": "Release manager-led",
        "gate": "G3 · Verified in production",
        "summary": "Every change moves dev → stage → prod by pull request; pipelines build, check and document it, and the release manager approves each promotion.",
        "key_steps": [
            "Implement against the change specification",
            "Integrate with upstream and downstream components",
            "Test: unit, integration and reconciliation",
            "Lint and enforce the PR template on every change",
            "Promote dev → stage → prod with approval at each step",
            "Generate CHANGELOG.md and release notes on merge",
        ],
        "agents": [
            {"name": "Build Agents", "capability": "Build · delivery pod", "description": "Per component: implement, integrate, test and deploy to the acceptance criteria.", "skills": ["/convert-ddl", "/convert-etl", "/gen-unit-tests", "/reconcile"], "tools": ["Claude Code", "Cortex Code", "GitHub Actions"]},
            {"name": "Build Agent", "capability": "Build Snowflake Artifacts", "description": "Objects, pipelines and policies built as code from the repo.", "skills": ["/gen-migration", "/build-artifacts"], "tools": ["GitHub Actions", "schemachange"]},
            {"name": "Quality Gate", "capability": "Code Quality + Standards", "description": "PR templates and linting enforce one standard on every change.", "skills": ["/lint-sql", "/pr-template"], "tools": ["SQLFluff", "GitHub PR checks"]},
            {"name": "Promotion Agent", "capability": "Dev → Stage → Prod", "description": "The same artifacts promoted across environments, with approval at each step.", "skills": ["/promote", "/rollback"], "tools": ["Snowflake CLI", "Terraform"]},
            {"name": "Release Agent", "capability": "Release Management", "description": "Merge to the release branch generates CHANGELOG.md and release notes.", "skills": ["/gen-changelog", "/release-notes"], "tools": ["GitHub Releases", "Semantic versioning"]},
        ],
        "frameworks": ["Code Promotion"],
        "snowflake": ["Zero-copy clones"],
        "outputs": ["Release evidence", "CHANGELOG.md", "Release notes"],
        "evidence": ["Pull request + reviews", "Lint + test results", "CHANGELOG.md", "Release notes", "Runbook updates"],
        "prompts": ["How does a change get to prod?", "What evidence is kept per release?"],
    },
    {
        "code": "monitor", "seq": 10, "name": "Operate & monitor", "phase": 5, "slide": 30,
        "lead_role": "Platform operations", "mode": "AI-assisted operations",
        "gate": "Formal handover sign-off",
        "summary": "AI-assisted operations keep cost, quality and service levels in check after go-live. ABC Retail owns the code from day one; every release is reproducible, documented and handed over with runbooks.",
        "key_steps": [
            "Run the monitored go-live with release, rollback and runbooks",
            "Watch catalog, lineage, run and cost telemetry",
            "Tune with Search Optimization and Query Acceleration",
            "Keep ADRs and runbooks current: set up, configure, run, troubleshoot, monitor",
            "Train by role, shadow and reverse shadow",
            "Formal handover; feed learnings back to Discover",
        ],
        "agents": [
            {"name": "Deploy and monitor agent", "capability": "Cut-over + hypercare", "description": "Watches the go-live and hypercare runs.", "skills": [], "tools": ["Cortex Code", "Resource monitors"]},
            {"name": "Docs Agent", "capability": "ADRs + Runbooks", "description": "Decision records and runbooks: set up, configure, run, troubleshoot, monitor.", "skills": ["/gen-adr", "/gen-runbook"], "tools": ["Markdown in repo", "Claude Code"]},
            {"name": "Enablement Agent", "capability": "Training + Handover", "description": "Role-based training, shadow and reverse shadow, then formal handover.", "skills": ["/gen-training", "/kt-checklist"], "tools": ["Recorded sessions", "Handover sign-off"]},
        ],
        "frameworks": ["Code Promotion", "Data Harness"],
        "snowflake": ["Search Optimization, Query Acceleration", "Horizon lineage and audit", "Cortex Code for run support", "Resource monitors"],
        "outputs": ["Monitored go-live and handover", "Runbooks", "Training records"],
        "evidence": ["Catalog & lineage", "Run & cost telemetry", "Change audit trail"],
        "metrics": [["Faster time to value", "up to 50%"], ["Engineering effort", "~35%"], ["Design effort", "~25%"], ["Faster setup", "90%"]],
        "prompts": ["What happens in hypercare?", "Which agent writes runbooks?"],
    },
]

TEAM = [
    ("AI Native Engineer", "Core pod: builds the accelerator services"),
    ("AI-Assisted Engineers", "Track pods: apply them per wave"),
    ("Snowflake SE · Frontier", "AIM, Cortex and platform guidance"),
]

# ---------------------------------------------------------------------------
# Personas & journeys
# step: (stage, question, experience, metrics, doing, today)
# ---------------------------------------------------------------------------
PERSONAS = [
    {"code": "dc_ops", "segment": "Operational", "name": "Warehouse, DC & site ops", "roles": "DC GM · shift managers",
     "wants": "The shift to run to plan, with no surprises", "slide": 18, "journey": "Internal",
     "steps": [
         ("Start of shift", "Is labour planned against today's waves and dock schedule?", "Site Daily Operations", "backlog · planned vs available hours"),
         ("During shift", "Where is the bottleneck right now?", "Site Daily Operations", "live UPH by zone · wave progress · dock-to-stock"),
         ("End of shift", "Did every order ship by cut-off?", "Site Daily Operations", "on-time ship · order cycle time · pick accuracy"),
         ("Week close", "Are accuracy and labour cost on target?", "Inventory Health", "inventory accuracy · labour cost per unit · overtime %"),
     ]},
    {"code": "transport", "segment": "Operational", "name": "Transportation & fleet", "roles": "Dispatchers · fleet director",
     "wants": "Every load on time at the planned cost", "slide": 18, "journey": "Internal",
     "steps": [
         ("Plan loads", "Which carriers accept today's tenders at the best rate?", "Transportation Control Tower", "tender acceptance · rate per lane"),
         ("Dispatch & track", "Which shipments are at risk of missing the window?", "Transportation Control Tower", "ETA variance · on-time pickup and delivery"),
         ("Resolve", "What causes late deliveries on this lane?", "Carrier scorecard", "tracking events by reason code · carrier rank"),
         ("Settle", "Did we pay what we planned?", "Freight audit view", "invoice accuracy · cost per mile · empty miles"),
     ]},
    {"code": "exec", "segment": "Executive", "name": "Executive leadership", "roles": "CXO · VP supply chain · CHRO",
     "wants": "One view of service, cost and people to steer the network", "slide": 18, "journey": "Internal",
     "steps": [
         ("Monitor weekly", "Is the network on plan for OTIF and margin?", "Network Performance Scorecard", "OTIF · cost to serve · margin vs target"),
         ("Diagnose", "Which sites, customers or lanes drive the gap?", "Drill-down or Cortex Analyst", "same certified metrics at every level"),
         ("Decide", "Where do we add capacity or reprice?", "Customer Profitability & SLA", "capacity utilization · volume vs commitment"),
         ("Review monthly", "Are our customers and people healthy?", "Executive HR Pack", "SLA attainment · turnover · TRIR"),
     ]},
    {"code": "customer", "segment": "External customer", "name": "Supply-chain manager", "roles": "at a retail or CPG shipper",
     "wants": "Self-serve from inbound plan to invoice", "slide": 19, "journey": "Customer",
     "goals": "Stock where it is needed, when it is needed; fewer surprises: hear about issues first; proof that the SLA was met",
     "pains": "Status by phone and email; numbers that differ from their own systems; manual QBR and invoice checks",
     "kpis": "OTIF, Fill rate, Dock-to-stock, Inventory accuracy, Damage-free, SLA attainment",
     "note": "Served by a customer portal on Tableau Cloud, secured by a row access policy per customer. Moment that matters: the customer sees an at-risk order before the store does.",
     "steps": [
         ("Plan inbound", "Will my inbound be received in time for the promotion?", "Inventory Visibility", "ASN status · dock appointment · dock-to-stock",
          "Sends orders and ASNs by EDI or portal; books inbound with the DC.", "Emailed spreadsheets; ASN status unknown until receipt."),
         ("Track inventory", "What can I sell today, and what is aged or on hold?", "Inventory Visibility", "available vs on-hand · hold · aged stock",
          "Checks on-hand and available stock by SKU and site.", "Daily static report that differs from their own ERP."),
         ("Monitor delivery", "Which orders will miss the delivery window?", "Order & Shipment Visibility", "order status · ETA · POD · at-risk flag",
          "Follows orders from release to ship, delivery and proof of delivery.", "Calls the account team for status."),
         ("Resolve exceptions", "What went wrong, and who owns the fix?", "Exception alerts", "reason code · damage-free · claims",
          "Handles shorts, damages and late deliveries.", "Learns of the problem when the store complains."),
         ("Review and pay", "Did ABC Retail meet our SLA, and is the invoice right?", "Customer SLA Scorecard", "OTIF · fill rate · SLA trend · billing detail",
          "Runs the QBR with ABC Retail and reconciles the invoice.", "QBR deck built by hand; disputes on billable activity."),
     ]},
    {"code": "automation", "segment": "Operational", "name": "Automation, robotics and lift fleet", "roles": "Engineering and automation managers · safety leads",
     "wants": "Every robot, lift and conveyor available and safe when the volume arrives", "slide": 20, "journey": "Automation",
     "note": "Illustrative: fleet management system and labor management system are discovery only in scope.",
     "steps": [
         ("Pre-shift check", "Is every AMR, lift and conveyor ready for today's volume?", "fleet management system brief + Command Center", "fleet availability · open faults · lift impacts overnight"),
         ("Monitor live", "Which robots, lifts or merges are slowing the flow?", "Command Center, embedded in fleet management system", "AMR utilization · near misses · throughput by zone"),
         ("Act", "Rebalance charging, reroute tasks or slow a lift zone?", "WCS, fleet manager and fleet management system", "write-back: tasks rerouted, drivers alerted"),
         ("Improve weekly", "Which faults and hotspots recur, and is it paying back?", "Automation Performance Review", "MTBF and MTTR · impacts per 1,000 hours · ROI"),
     ]},
    {"code": "labor", "segment": "Operational", "name": "Labor planning and shift ops", "roles": "Labor planners · shift managers",
     "wants": "The right people in the right zone, at standard, without overtime", "slide": 20, "journey": "Automation",
     "note": "Illustrative: labor management system is discovery only in scope.",
     "steps": [
         ("Plan the shift", "Do scheduled associates match the WMS waves?", "labor management system forecast + planning system plan", "required vs scheduled hours · skills by zone"),
         ("During shift", "Who is behind standard, and where?", "labor management system with embedded Tableau", "performance to standard · idle time · absence"),
         ("Act", "Move associates or re-release the wave?", "labor management system, planning system, WMS", "write-back: reassignments, wave re-release"),
         ("Close and coach", "Who needs coaching, and is incentive pay right?", "labor management system scorecard", "performance to standard · incentive · coaching log"),
     ]},
    {"code": "site_ci", "segment": "Executive", "name": "Site leadership and continuous improvement", "roles": "DC GM · continuous improvement leaders",
     "wants": "Robots and people delivering the plan at the lowest cost per unit", "slide": 20, "journey": "Automation",
     "steps": [
         ("Daily review", "Did robots and people deliver the plan at the right cost?", "Site Daily Operations", "cost per unit · on-time ship · automation share"),
         ("Diagnose", "Are the losses from robots, people or process?", "Cortex Analyst across all four systems", "loss by cause · Pareto by zone and shift"),
         ("Decide", "Where do we add automation, slots or shifts?", "Automation ROI and 3PL billing", "payback · cost to serve · billing capture"),
         ("Sustain", "Are improvement gains holding across sites?", "Continuous Improvement Tracker", "before and after KPIs · site benchmark"),
     ]},
]

# ---------------------------------------------------------------------------
# Insight dashboards
# ---------------------------------------------------------------------------
INSIGHT_KINDS = ["What happened", "Why it happened", "What will happen", "What you can do"]
DASHBOARDS = [
    {"code": "exec", "name": "Executive dashboard", "audience": "Executive leadership", "roles": "CXO · VP supply chain",
     "surface": "Scorecard · Cortex Analyst and Agents", "headline": "From OTIF signal to decision in one view", "slide": 21, "persona": "exec",
     "qa": [("Are we on track for OTIF this quarter?", "Annotated trend: three weeks below target, now 94.2%."),
            ("What is driving the gap?", "A state tile map and driver bars trace 71% of the gap to Midwest lanes."),
            ("What will peak season do to service?", "Forecast fan: 93.5% as-is at peak vs 95.6% with actions."),
            ("Where should we act first?", "A bridge of three ranked actions lifts peak OTIF to 95.6% for +$99K.")]},
    {"code": "ops", "name": "Operations dashboard", "audience": "Warehouse, DC and site ops", "roles": "DC GM · shift managers",
     "surface": "Site Daily Operations · Cortex Agents", "headline": "Find the bottleneck and recover before cut-off", "slide": 22, "persona": "dc_ops",
     "qa": [("How is the shift running against plan?", "The zone-by-hour heatmap shows Zone C below 70% of standard since 09:00."),
            ("Where is the bottleneck right now?", "The live floor view lights up Zone C: late replenishment in 5 aisles."),
            ("Will every order ship by cut-off?", "The burn-down projects 2,100 units missing the 16:00 cut-off."),
            ("What should I move to recover?", "Three moves clear the backlog by 15:40; the shift lead is notified.")]},
    {"code": "customer", "name": "Customer dashboard", "audience": "External customer", "roles": "Supply-chain manager at a shipper",
     "surface": "Customer portal · Cortex assistant", "headline": "Self-service visibility and action for every ABC Retail shipper", "slide": 23, "persona": "customer",
     "qa": [("Where are my orders right now?", "Order pipeline and OTIF trend, secured to their own data."),
            ("Why was OTIF below SLA in W38–W39?", "Root-cause donut and store dots: carrier delay drives 48%."),
            ("Will we have stock for Friday's promotion?", "Bullet chart flags 2 SKUs that run out before the promotion."),
            ("What can I do before stores are affected?", "Three self-service requests cut at-risk orders from 23 to 8.")]},
    {"code": "automation", "name": "Automation dashboard", "audience": "Warehouse automation and labor", "roles": "Automation manager · shift manager",
     "surface": "Automation and Labor Command Center", "headline": "One view of robots, lifts and labor, embedded in labor management system, with fixes written back before the shift is lost", "slide": 24, "persona": "automation",
     "guardrail": "fleet management system and labor management system elements are illustrative: both are discovery only in scope.",
     "qa": [("Why did the floor slow at 10:00?", "AMR availability and labor productivity fell together below the 90% target."),
            ("Is it robots, people or process?", "Charging, absence and below-standard picking (labor management system) drive 68%; fleet management system flags lift congestion."),
            ("Will we make plan by end of shift?", "As-is, 4,600 units fall short; with actions, back on plan by 15:30."),
            ("What do I change, and where?", "Rebalance AMRs, reassign through labor management system, re-release in WMS.")]},
]

# ---------------------------------------------------------------------------
# Logistics industry data model
# ---------------------------------------------------------------------------
DOMAINS = [
    ("Warehouse management", "WMS + legacy WMS", [
        ("Facility & Location", "site, building, zone, aisle, bin, storage type"),
        ("Inbound & Receiving", "ASN, dock appointment, receipt, putaway"),
        ("Inventory & Cycle Count", "position, lot, status, movement, count variance"),
        ("Outbound & Fulfilment", "order, wave, pick, pack, load, ship"),
        ("Labour, Dock & Yard", "task time, engineered standard, trailer, door")]),
    ("Transportation management", "Oracle OTM / Infios TMS", [
        ("Order Base & Order Release", "customer order, release, plan-from / plan-to"),
        ("Shipment, Stop & Leg", "load, stop, leg, mode, equipment group"),
        ("Tracking Events & ETA", "status, reason code, responsible party, ETA"),
        ("Carrier, Lane & Rate", "service provider, lane, rate offering, tender"),
        ("Freight Cost & Audit", "planned vs invoiced cost, accessorials, disputes")]),
    ("Customer & commercial", "customer data · contracts · billing", [
        ("Customer Account", "client, account hierarchy, ship-to, consignee"),
        ("Contract & SLA", "service scope, SLA commitment, volume commitment"),
        ("Billing & Revenue", "billable activity, rate schedule, invoice"),
        ("Claims & OS&D", "over, short and damaged, claim, settlement"),
        ("Service Cases", "case, root cause, resolution time")]),
    ("Workforce & enterprise", "Engineering & ops apps · HR", [
        ("Workforce & HR", "employee, position, headcount, turnover, overtime"),
        ("Fleet, Driver & Equipment", "tractor, trailer, driver, hours of service"),
        ("Engineering & Maintenance", "MHE asset, work order, downtime"),
        ("Finance & Cost To Serve", "site P&L, cost pools, allocation"),
        ("Safety & Sustainability", "incident, recordable hours, CO2e")]),
]

LAYERS = [
    ("Bronze", "Raw replicas of WMS, TMS, HR and customer sources"),
    ("Silver", "Normalized, source-aligned entities in the Databricks style"),
    ("Gold", "Kimball star schemas and Snowflake semantic views"),
]

CONFORMED_DIMS = ["Date & fiscal calendar", "Customer / account", "Site & facility", "Item / SKU", "Location & geography",
                  "Carrier / service provider", "Lane & route", "Transport mode & equipment", "Employee & shift", "Status & reason code"]

# entity: (model, name, kind, fact_type/scd, grain_or_desc, subject_area, attributes[(name, role, desc)])
def _m(*names):
    return [(n, "measure", "") for n in names]

def _fk(*names):
    return [(n, "FK", "") for n in names]

ENTITIES = [
    # Warehouse schema
    ("Warehouse", "FACT_WAREHOUSE_TASK", "fact", "Transaction",
     "One row per warehouse task (receive, putaway, replenish, pick, pack, load) per item, location and employee", "Labour, Dock & Yard",
     _m("Units and lines handled", "Cases, pallets, weight, cube", "Task start, end and duration", "Engineered standard minutes",
        "Travel distance", "Short and error quantity", "Exception flag", "Billable activity units")
     + _fk("task_date_key", "site_key", "location_key", "item_key", "customer_key", "employee_key", "task_type_key", "equipment_key", "status_key")
     + [("order_number", "DD", "degenerate key")]),
    ("Warehouse", "DIM_DATE", "dim", "SCD1", "calendar, fiscal week, shift date", "Facility & Location", [("date_key", "PK", "")]),
    ("Warehouse", "DIM_SITE", "dim", "SCD2", "site, DC type, region, GM", "Facility & Location", [("site_key", "PK", "")]),
    ("Warehouse", "DIM_CUSTOMER", "dim", "SCD2", "client, account, ship-to", "Customer Account", [("customer_key", "PK", "")]),
    ("Warehouse", "DIM_STORAGE_LOCATION", "dim", "SCD1", "zone, aisle, bin, storage type", "Facility & Location", [("location_key", "PK", "")]),
    ("Warehouse", "DIM_ITEM", "dim", "SCD2", "SKU, UoM, velocity class, hazmat", "Inventory & Cycle Count", [("item_key", "PK", "")]),
    ("Warehouse", "DIM_EMPLOYEE", "dim", "SCD2", "employee, role, agency, shift", "Workforce & HR", [("employee_key", "PK", "")]),
    ("Warehouse", "DIM_TASK_TYPE", "dim", "SCD1", "process, sub-process, direct / indirect", "Labour, Dock & Yard", [("task_type_key", "PK", "")]),
    ("Warehouse", "DIM_EQUIPMENT", "dim", "SCD1", "MHE type, forklift, RF device", "Engineering & Maintenance", [("equipment_key", "PK", "")]),
    ("Warehouse", "DIM_ORDER", "dim", "Degenerate", "order, wave, ASN (degenerate keys)", "Outbound & Fulfilment", [("order_number", "PK", "")]),
    ("Warehouse", "DIM_STATUS_REASON", "dim", "SCD1", "status, exception reason", "Tracking Events & ETA", [("status_key", "PK", "")]),
    ("Warehouse", "FACT_INVENTORY_DAILY", "fact", "Snapshot", "On-hand, available, allocated, hold and damaged quantity and value by item, lot and location.", "Inventory & Cycle Count", []),
    ("Warehouse", "FACT_INBOUND_RECEIPT_LINE", "fact", "Accumulating", "ASN to arrival, receipt and putaway milestones; dock-to-stock and receipt variance.", "Inbound & Receiving", []),
    ("Warehouse", "FACT_OUTBOUND_ORDER_LINE", "fact", "Accumulating", "Order to release, pick, pack and ship milestones; fill rate and on-time ship.", "Outbound & Fulfilment", []),
    ("Warehouse", "FACT_CYCLE_COUNT", "fact", "Transaction", "System vs counted quantity, variance value and adjustment by location.", "Inventory & Cycle Count", []),
    ("Warehouse", "FACT_LABOR_ACTIVITY", "fact", "Transaction", "Direct and indirect hours against engineered standards; UPH and utilization.", "Labour, Dock & Yard", []),
    ("Warehouse", "FACT_DOCK_APPOINTMENT", "fact", "Accumulating", "Scheduled vs actual arrival, door time and yard dwell per trailer.", "Labour, Dock & Yard", []),
    ("Warehouse", "FACT_BILLABLE_ACTIVITY", "fact", "Transaction", "Storage, handling and value-added services by customer and rate for 3PL billing.", "Billing & Revenue", []),
    # Transportation schema
    ("Transportation", "FACT_SHIPMENT_LEG", "fact", "Transaction",
     "One row per shipment leg (stop-to-stop) per shipment, carrier and equipment", "Shipment, Stop & Leg",
     _m("Planned vs actual pickup", "Planned vs actual delivery", "Transit time and delay hours", "Loaded and empty miles",
        "Weight, cube, pallets", "Planned and actual freight cost", "Accessorial charges", "CO2e emissions")
     + _fk("ship_date_key", "delivery_date_key", "carrier_key", "customer_key", "lane_key", "source_location_key", "dest_location_key",
           "mode_key", "equipment_group_key", "rate_offering_key", "status_key")),
    ("Transportation", "DIM_CARRIER", "dim", "SCD2", "service provider, SCAC, carrier tier", "Carrier, Lane & Rate", [("carrier_key", "PK", "")]),
    ("Transportation", "DIM_SOURCE_LOCATION", "dim", "SCD1", "DC, plant, city, region", "Shipment, Stop & Leg", [("source_location_key", "PK", "")]),
    ("Transportation", "DIM_DEST_LOCATION", "dim", "SCD1", "store, consignee, zone", "Shipment, Stop & Leg", [("dest_location_key", "PK", "")]),
    ("Transportation", "DIM_LANE", "dim", "SCD2", "origin-destination, distance band", "Carrier, Lane & Rate", [("lane_key", "PK", "")]),
    ("Transportation", "DIM_TRANSPORT_MODE", "dim", "SCD1", "TL, LTL, intermodal, parcel", "Shipment, Stop & Leg", [("mode_key", "PK", "")]),
    ("Transportation", "DIM_EQUIPMENT_GROUP", "dim", "SCD1", "dry van, reefer, flatbed", "Shipment, Stop & Leg", [("equipment_group_key", "PK", "")]),
    ("Transportation", "DIM_RATE_OFFERING", "dim", "SCD2", "rate record, tariff, contract", "Carrier, Lane & Rate", [("rate_offering_key", "PK", "")]),
    ("Transportation", "FACT_ORDER_RELEASE", "fact", "Accumulating", "Order base to release, planned, tendered, picked up and delivered milestones.", "Order Base & Order Release", []),
    ("Transportation", "FACT_TRACKING_EVENT", "fact", "Transaction", "Shipment and order-release events with status, reason code and ETA variance.", "Tracking Events & ETA", []),
    ("Transportation", "FACT_TENDER", "fact", "Transaction", "Tenders offered, accepted and rejected by carrier, lane and response time.", "Carrier, Lane & Rate", []),
    ("Transportation", "FACT_FREIGHT_INVOICE_LINE", "fact", "Transaction", "Billed vs planned cost, accessorials, audit result and dispute value.", "Freight Cost & Audit", []),
    ("Transportation", "FACT_FLEET_TRIP", "fact", "Transaction", "Private fleet trips: loaded and empty miles, fuel, driver hours of service.", "Fleet, Driver & Equipment", []),
    ("Transportation", "FACT_LANE_MONTHLY", "fact", "Snapshot", "Monthly lane and carrier performance: volume, on-time, cost per mile.", "Carrier, Lane & Rate", []),
    # Automation and labor
    ("Automation & labor", "FACT_TASK_EXECUTION", "fact", "Transaction",
     "One row per task executed by a robot or an associate: pick, putaway, replenish, induct, move", "Labour, Dock & Yard",
     _m("Units and lines handled", "Task duration and travel time", "Idle and wait time", "Engineered standard time",
        "Performance to standard", "Robot-assisted flag", "Labor cost", "Energy and charge used")
     + _fk("task", "wave", "robot or employee", "location", "item", "shift", "date", "reason code", "source system")),
    ("Automation & labor", "DIM_DATE_SHIFT", "dim", "Conformed", "date, shift, hour, fiscal week", "Workforce & HR", []),
    ("Automation & labor", "DIM_SITE_ZONE", "dim", "Conformed", "site, building, zone, aisle, bin", "Facility & Location", []),
    ("Automation & labor", "DIM_ROBOT_ASSET", "dim", "Local", "AMR, forklift (fleet management system), AS/RS, sorter, conveyor", "Engineering & Maintenance", []),
    ("Automation & labor", "DIM_WAVE_ORDER", "dim", "Local", "WMS wave, order, priority, cut-off", "Outbound & Fulfilment", []),
    ("Automation & labor", "DIM_LABOR_STANDARD", "dim", "Local", "engineered standards by task and zone (labor management system if built)", "Labour, Dock & Yard", []),
    ("Automation & labor", "DIM_REASON_CODE", "dim", "Conformed", "fault, delay, idle, exception", "Tracking Events & ETA", []),
    ("Automation & labor", "FACT_ROBOT_STATUS", "fact", "Snapshot", "Every 1-5 minutes per AMR: working, charging, fault or idle; WCS and PLC fault events", "Engineering & Maintenance", []),
    ("Automation & labor", "FACT_LIFT_EVENT", "fact", "Transaction", "Discovery only · fleet telemetry: collisions, near misses, speeding and idle per lift", "Safety & Sustainability", []),
    ("Automation & labor", "FACT_LABOR_SHIFT", "fact", "Snapshot", "planning system WFM and UKG / Dayforce: scheduled vs clocked hours, absence, overtime", "Workforce & HR", []),
    ("Automation & labor", "FACT_LABOR_PERFORMANCE", "fact", "Accumulating", "Discovery only · labor management system: performance to standard per associate and shift", "Labour, Dock & Yard", []),
    ("Automation & labor", "FACT_WAVE_PROGRESS", "fact", "Accumulating", "WMS waves from release to ship: planned vs actual units and cut-off risk", "Outbound & Fulfilment", []),
    ("Automation & labor", "FACT_ACTION_LOG", "fact", "Transaction", "Every write-back to WMS, planning system, labor management system or the WCS, and each AiOn alert: who, what, outcome", "Service Cases", []),
]

# Dimension descriptions become attributes too
def dim_attributes(desc):
    return [(a.strip(), "attribute", "") for a in desc.split(",") if a.strip()]

# KPIs. audiences: E executive, O operational, C external customer. source_fact is a suggested mapping.
KPIS = [
    ("Warehouse operations", "Units per hour (UPH)", "units picked ÷ direct labour hours", "O", "FACT_LABOR_ACTIVITY"),
    ("Warehouse operations", "Dock-to-stock time", "putaway confirmed − trailer arrival, hours", "C,O", "FACT_INBOUND_RECEIPT_LINE"),
    ("Warehouse operations", "Order cycle time", "shipped − order released, hours", "C,O", "FACT_OUTBOUND_ORDER_LINE"),
    ("Warehouse operations", "Pick accuracy", "error-free picks ÷ total picks", "O", "FACT_WAREHOUSE_TASK"),
    ("Warehouse operations", "Inventory accuracy", "locations with no variance ÷ locations counted", "C,O", "FACT_CYCLE_COUNT"),
    ("Warehouse operations", "Order fill rate", "units shipped ÷ units ordered", "C,O,E", "FACT_OUTBOUND_ORDER_LINE"),
    ("Warehouse operations", "Capacity utilization", "occupied locations or cube ÷ available", "O,E", "FACT_INVENTORY_DAILY"),
    ("Warehouse operations", "On-time ship", "orders shipped by cut-off ÷ orders due", "C,O", "FACT_OUTBOUND_ORDER_LINE"),
    ("Transportation & fleet", "OTIF", "orders on time and in full ÷ total orders", "C,O,E", "FACT_ORDER_RELEASE"),
    ("Transportation & fleet", "On-time pickup / delivery", "stops within appointment window ÷ stops", "C,O", "FACT_SHIPMENT_LEG"),
    ("Transportation & fleet", "Transit-time variance", "actual − planned transit hours, by lane", "O", "FACT_SHIPMENT_LEG"),
    ("Transportation & fleet", "Cost per mile / ton-mile", "freight cost ÷ miles or ton-miles", "O,E", "FACT_SHIPMENT_LEG"),
    ("Transportation & fleet", "Tender acceptance", "tenders accepted ÷ tenders offered", "O", "FACT_TENDER"),
    ("Transportation & fleet", "Trailer utilization", "loaded weight or cube ÷ capacity", "O", "FACT_SHIPMENT_LEG"),
    ("Transportation & fleet", "Empty-mile ratio", "empty miles ÷ total miles", "O,E", "FACT_FLEET_TRIP"),
    ("Transportation & fleet", "Freight invoice accuracy", "invoices matching plan ÷ invoices audited", "O,E", "FACT_FREIGHT_INVOICE_LINE"),
    ("Customer & commercial", "SLA attainment", "SLA measures met ÷ measures due, by contract", "C,E", ""),
    ("Customer & commercial", "Perfect order rate", "on time × in full × damage-free × right documents", "C,E", "FACT_OUTBOUND_ORDER_LINE"),
    ("Customer & commercial", "Cost to serve", "warehouse + transport + overhead cost ÷ orders", "E", ""),
    ("Customer & commercial", "Margin per site / customer", "billed revenue − direct cost, vs target", "E", "FACT_BILLABLE_ACTIVITY"),
    ("Customer & commercial", "Billing capture", "billable activity invoiced ÷ activity recorded", "E", "FACT_BILLABLE_ACTIVITY"),
    ("Customer & commercial", "Claims ratio", "claim value ÷ shipped value", "C,E", ""),
    ("Customer & commercial", "Damage-free delivery", "shipments without OS&D ÷ shipments", "C,O", "FACT_SHIPMENT_LEG"),
    ("Customer & commercial", "Volume vs commitment", "actual volume ÷ contracted volume", "C,E", ""),
    ("Workforce & enterprise", "Headcount vs plan", "active FTE ÷ planned FTE, by site", "E", ""),
    ("Workforce & enterprise", "Voluntary turnover", "voluntary leavers ÷ average headcount, annualized", "O,E", ""),
    ("Workforce & enterprise", "Overtime %", "overtime hours ÷ total hours worked", "O,E", "FACT_LABOR_SHIFT"),
    ("Workforce & enterprise", "Labour cost per unit", "labour cost ÷ units handled", "O,E", "FACT_LABOR_ACTIVITY"),
    ("Workforce & enterprise", "Absenteeism", "unplanned absence hours ÷ scheduled hours", "O", "FACT_LABOR_SHIFT"),
    ("Workforce & enterprise", "Safety: TRIR", "recordable incidents × 200,000 ÷ hours worked", "O,E", ""),
    ("Workforce & enterprise", "MHE uptime", "available equipment hours ÷ scheduled hours", "O", "FACT_ROBOT_STATUS"),
    ("Workforce & enterprise", "CO2e per shipment", "kg CO2e ÷ shipments", "C,E", "FACT_SHIPMENT_LEG"),
]
