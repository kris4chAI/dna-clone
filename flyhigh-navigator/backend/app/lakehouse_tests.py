"""Lakehouse test catalogue: the tests a Snowflake open-lakehouse platform needs, by layer.

Six platform layers in three bands (data foundation, context/AI/agents, experience and action) plus
three cross-cutting disciplines (governance and security, observability and FinOps, test automation
and DevOps). Each test type lists what it proves, the checks that make it testable, the Snowflake
features and tools involved, the skills that generate or run it, the owner and the gate it evidences.
"""
import re

BANDS = [
    {"code": "foundation", "name": "Data foundation · open lakehouse", "layers": [1, 2, 3]},
    {"code": "context", "name": "Context, AI and agents", "layers": [4, 5]},
    {"code": "experience", "name": "Experience and action", "layers": [6]},
]
LAYERS = {
    1: "Source systems", 2: "Ingestion and access", 3: "Lakehouse core", 4: "Context and semantics",
    5: "Intelligence and agents", 6: "Applications and delivery",
    7: "Governance and security", 8: "Observability and FinOps", 9: "Test automation and DevOps",
}
CROSS = [7, 8, 9]

# code, layer, name, what it proves, checks, Snowflake features and tools, skills, owner, gate, automation
CATALOG = [
    # 1 Source systems
    ("L1.1", 1, "Source profiling and discovery", "Every source is profiled before design: volumes, keys, nulls, change capture and formats.",
     ["Row counts and growth are profiled for every source table", "Primary keys are unique and non-null in every source", "Change-capture columns and full-reload tables are identified"],
     ["Snowflake AIM assessment", "Estate Analyzer", "Profiling queries"], ["/discover", "/plan-waves"], "Solution architect", "G1", "Agentic"),
    ("L1.2", 1, "Data requirements and SLA definition", "Every data need is testable: grain, freshness SLA, quality thresholds and an owner.",
     ["Every PRD data need states grain, freshness and owner", "Freshness SLAs are numeric and agreed per feed", "Quality thresholds exist for each critical attribute"],
     ["PRD template", "Jira"], ["/pi-define-requirements"], "Product owner", "G1", "AI-assisted"),
    ("L1.3", 1, "Source-to-target mapping review", "The mapping from source columns to Bronze, Silver, Gold and report fields is complete and reviewed.",
     ["Every target column traces to a source column or a derivation", "Transformation rules are written down and reviewed", "Unmapped source columns are explained"],
     ["Mapping specification", "Horizon lineage"], ["/map-zones"], "BI analyst", "G2", "AI-assisted"),
    ("L1.4", 1, "Test data management: masking, synthetic", "Test data covers every scenario without exposing production personal data.",
     ["Synthetic data covers valid, boundary and invalid scenarios", "Personal data is masked or synthetic outside production", "Test data sets are versioned and reproducible"],
     ["Zero-copy clones", "Masking policies", "Test data generator"], ["aw-test-data-generator", "/gen-masking"], "Test data engineer", "G2", "Agentic"),
    # 2 Ingestion and access
    ("L2.1", 2, "Schema and ingestion validation", "Loads accept the expected schema and handle drift safely.",
     ["Files and tables land with the expected schema and types", "Schema drift is detected and quarantined, not silently loaded", "Rejected records are captured with a reason"],
     ["Snowpipe", "COPY validation mode", "Schema evolution"], ["/repoint-ingest", "/load-initial"], "Senior data engineer", "G3", "Agentic"),
    ("L2.2", 2, "CDC completeness and ordering", "Every source change arrives exactly once and in order.",
     ["Inserts, updates and deletes from the source all arrive", "Changes apply in source commit order", "Replays are idempotent with no duplicates"],
     ["Streams", "Dynamic tables", "Connectors"], ["/test-cdc", "/replay-load"], "Senior data engineer", "G3", "Agentic"),
    ("L2.3", 2, "Streaming latency and loss checks", "Streaming paths meet their latency target and lose nothing.",
     ["End-to-end latency stays within the streaming SLA", "Event counts match between producer and Snowflake", "Late and out-of-order events are handled"],
     ["Snowpipe Streaming", "Kafka connector"], ["/test-cdc"], "Senior data engineer", "G3", "Agentic"),
    ("L2.4", 2, "Row counts, checksums, file formats", "The basic integrity of every load is proven.",
     ["Row counts match the source extract for every load", "Column checksums match the source for numeric measures", "File formats, encodings and compression are as agreed"],
     ["COPY history", "Hash aggregates"], ["/reconcile", "/gen-etl-tests"], "QA engineer", "G3", "Agentic"),
    # 3 Lakehouse core
    ("L3.1", 3, "Bronze, silver and gold reconciliation", "Each layer reconciles to the one below it.",
     ["Row counts reconcile Bronze to Silver to Gold with explained filters", "Measures sum the same across layers", "Quarantined rows are accounted for"],
     ["dbt tests", "Reconciliation ledger"], ["/reconcile", "/gen-etl-tests"], "Testing lead", "G3", "Agentic"),
    ("L3.2", 3, "Transformation and business rules", "Derivations implement the agreed business rules.",
     ["Each business rule has a unit test with an expected output", "Lookups and joins neither drop nor duplicate rows", "Nulls, zeros and negatives behave as specified"],
     ["dbt unit tests"], ["/gen-unit-tests"], "Senior data engineer", "G3", "Agentic"),
    ("L3.3", 3, "SCD and golden-dataset regression", "History and known answers stay correct after every change.",
     ["SCD2 dimensions keep one current row per key with correct effective dates", "Golden datasets reproduce known outputs after every change", "Late-arriving dimension rows are handled"],
     ["dbt snapshots", "Golden datasets"], ["/check-scd", "/golden-queries"], "QA engineer", "G3", "Agentic"),
    ("L3.4", 3, "Data contracts: completeness, freshness", "Producers meet the contracts consumers depend on.",
     ["Required columns are populated above the agreed threshold", "Each table refreshes within its contract", "Contract breaches alert the producing team"],
     ["Data metric functions", "dbt contracts"], ["/test-metrics"], "Data governance lead", "G3", "Agentic"),
    # 4 Context and semantics
    ("L4.1", 4, "Metric parity with legacy", "Certified metrics match the legacy reports.",
     ["Every certified KPI matches the legacy report within tolerance", "Variances are signed off by the KPI arbiter", "Parity holds at every grain: day, site and customer"],
     ["Golden queries", "Legacy BI exports"], ["/golden-queries", "/compare-reports"], "BI analyst", "G3", "Agentic"),
    ("L4.2", 4, "Semantic-layer definition tests", "Semantic views define every metric correctly.",
     ["Each metric in the semantic view returns the golden-query value", "Dimensions, joins and filters resolve without fan-out", "Synonyms and verified queries exist for each metric"],
     ["Semantic views", "Cortex Analyst verified queries"], ["/test-metrics"], "BI analyst", "G2", "Agentic"),
    ("L4.3", 4, "Ontology and glossary consistency", "Every business term means one thing everywhere.",
     ["Each business term has one definition and one owner", "Glossary terms map to semantic-view entities", "No conflicting synonyms exist across domains"],
     ["Horizon catalog", "Business glossary"], ["aw-test-case-generator"], "KPI arbiter", "G2", "AI-assisted"),
    ("L4.4", 4, "Knowledge and vector corpus validation", "The documents agents search are complete, current and retrievable.",
     ["Every approved document is indexed with its metadata", "Stale or superseded documents are excluded", "Retrieval returns the right passage for each test question"],
     ["Cortex Search", "Document AI"], ["aw-test-case-generator"], "AI-native engineer", "G3", "AI-assisted"),
    # 5 Intelligence and agents
    ("L5.1", 5, "ML model validation and drift", "Models meet their thresholds and stay fair and stable in production.",
     ["Model metrics meet the release threshold on a holdout set", "Feature and prediction drift are monitored with alerts", "Fairness checks pass on protected segments"],
     ["Snowflake ML", "Model Registry", "ML observability"], ["aw-test-case-generator"], "AI-native engineer", "G3", "AI-assisted"),
    ("L5.2", 5, "Agent evaluation, tool-call safety", "Agents pick the right tools and never act beyond the user's rights.",
     ["Agents choose the right tool for each evaluation task", "Tool calls run with the user's role and never wider", "Actions that change data wait for human approval"],
     ["Cortex Agents", "MCP", "RBAC"], ["aw-test-case-generator"], "AI-native engineer", "G3", "AI-assisted"),
    ("L5.3", 5, "LLM output accuracy, groundedness", "Answers are correct, cited and grounded in governed data.",
     ["Golden questions answer within tolerance of the certified KPI", "Answers cite their source rows or documents", "Ungrounded answers are flagged and withheld"],
     ["Cortex evaluations", "AI observability"], ["/golden-queries"], "QA / evaluation", "G3", "Agentic"),
    ("L5.4", 5, "Guardrail red-teaming, prompt evals", "Agents resist misuse and stay inside the governed scope.",
     ["Prompt-injection attempts in source data are ignored", "Questions outside the semantic model are declined", "Sensitive data is never returned to unauthorised users"],
     ["Cortex Guard", "Prompt evaluation sets"], ["aw-test-case-generator"], "QA / evaluation", "G3", "AI-assisted"),
    # 6 Applications and delivery
    ("L6.1", 6, "BI and dashboard validation", "Dashboards answer each persona's questions with certified numbers.",
     ["Dashboard numbers match the certified metrics", "Layouts, filters and drill paths work as designed", "Like-for-like reports match the legacy visuals"],
     ["Tableau Cloud", "BI comparator"], ["/compare-reports", "aw-test-script-generator"], "BI engineer", "G3", "Agentic"),
    ("L6.2", 6, "Row-level security tests", "Every persona sees only the rows they may see, everywhere.",
     ["Each persona sees only permitted rows", "Customers see only their own data", "Row access holds in extracts, exports and agent answers"],
     ["Row access policies", "BI user filters"], ["/test-rls", "/gen-rls"], "QA engineer", "G3", "Agentic"),
    ("L6.3", 6, "Data app, API and sharing tests", "Apps, APIs and shares return the right data to the right parties.",
     ["APIs return correct data and status codes", "Data apps run under the right roles", "Data shares expose only the agreed objects"],
     ["Streamlit in Snowflake", "Secure data sharing", "SQL API"], ["aw-test-case-generator"], "BI engineer", "G3", "Agentic"),
    ("L6.4", 6, "UAT and parallel-run sign-off", "The business accepts the release with evidence.",
     ["Business users sign UAT against the acceptance criteria", "The parallel run shows parity for the agreed period", "Go / no-go evidence is complete"],
     ["Parallel run", "UAT evidence pack"], ["/parallel-run"], "UAT lead", "G3", "Human-led"),
    # 7 Governance and security
    ("X7.1", 7, "Catalog and lineage checks", "Every governed object is catalogued and traceable end to end.",
     ["Every Gold object is catalogued with an owner and description", "Lineage is complete from source to dashboard", "Classification tags are applied to sensitive columns"],
     ["Horizon catalog", "Lineage", "Object tags"], ["/map-zones"], "Data governance lead", "G2", "Agentic"),
    ("X7.2", 7, "Access-policy and masking tests", "Policies protect sensitive data for every role.",
     ["Masking applies per role to every sensitive column", "Roles follow least privilege with no direct grants to users", "Users without access are refused and the attempt is logged"],
     ["Masking policies", "Database roles"], ["/gen-masking", "/design-rbac", "/test-rls"], "Data governance lead", "G2", "Agentic"),
    ("X7.3", 7, "Residency checks", "Data stays where contracts and regulation say it must.",
     ["Data stays in the agreed region and account", "Replication and shares respect residency rules", "Agents and AI functions process data in-region"],
     ["Account and region", "Replication groups"], ["aw-test-case-generator"], "Enterprise architect", "G2", "AI-assisted"),
    ("X7.4", 7, "Audit trails and traceability", "Every access and change can be traced.",
     ["Access history records every query on sensitive data", "Every change traces to a pull request, story and approval", "Gate decisions are recorded with a named approver"],
     ["Access history", "Query history", "Git"], ["/gen-changelog", "/release-notes"], "Data governance lead", "G3", "Agentic"),
    ("X7.5", 7, "Master data validation", "Shared masters are unique, complete and consistent.",
     ["Customer, site and product masters are unique and complete", "Golden records match across source systems", "Survivorship rules are applied consistently"],
     ["Conformed dimensions", "Data metric functions"], ["/check-scd"], "Data governance lead", "G3", "Agentic"),
    # 8 Observability and FinOps
    ("X8.1", 8, "Pipeline and data observability", "Failures and anomalies are seen before users see them.",
     ["Failed tasks and pipelines alert their owner", "Volume and schema anomalies are detected", "Every pipeline has a named owner and a runbook"],
     ["Alerts", "Event tables", "Task history"], ["/test-metrics", "/gen-runbook"], "Platform operations", "G3", "Agentic"),
    ("X8.2", 8, "ML-based DQ scoring and alerts", "Data quality is scored and anomalies are flagged automatically.",
     ["Anomaly detection flags unusual volumes and distributions", "A data-quality score is published per table", "Alerts route to the owning team"],
     ["Data metric functions", "Anomaly detection"], ["/test-metrics"], "Platform operations", "G3", "Agentic"),
    ("X8.3", 8, "SLA and incident triage", "Feeds meet their SLAs; when they don't, someone acts.",
     ["Every feed lands within its SLA", "Late feeds raise an incident with an owner", "Root cause is recorded for every incident"],
     ["Alerts", "Incident runbooks"], ["/gen-runbook"], "Platform operations", "G3", "AI-assisted"),
    ("X8.4", 8, "Performance and stress tests", "The platform is fast at production volume and peak concurrency.",
     ["Dashboard filters respond in under 5 s at production volume", "Peak concurrency holds without queuing", "Warehouse scaling behaves as configured"],
     ["Query Insights", "Multi-cluster warehouses"], ["/load-test", "/tune-warehouse"], "Performance engineer", "G3", "Agentic"),
    ("X8.5", 8, "Cost per query, job and run", "Every workload stays inside its budget.",
     ["Credits per workload stay within budget", "Expensive queries are flagged with an owner", "Resource monitors suspend at the threshold"],
     ["Resource monitors", "Budgets", "Metering views"], ["/tune-warehouse"], "FinOps lead", "G3", "Agentic"),
    # 9 Test automation and DevOps
    ("X9.1", 9, "Tests as code in CI/CD", "Every change is tested automatically before merge.",
     ["Unit, data-quality and reconciliation tests run on every pull request", "Failing tests block the merge", "Test results are stored with the build"],
     ["GitHub Actions", "dbt", "SQLFluff"], ["/lint-sql", "/pr-template", "/build-artifacts"], "Test automation engineer", "G3", "Agentic"),
    ("X9.2", 9, "Automated promotion gates", "Only tested, approved changes reach production.",
     ["Promotion from dev to stage to prod needs passing tests and an approval", "No direct production writes are possible", "Rollback is rehearsed for every release"],
     ["schemachange", "Time Travel"], ["/promote", "/rollback"], "Release manager", "G3", "Agentic"),
    ("X9.3", 9, "Impact-based test selection", "Each change runs the tests that matter most.",
     ["Changed files select the impacted test cases", "High-risk tests always run", "Unmapped changes are flagged for new tests"],
     ["Test-to-code mappings"], ["aw-impact-analyzer"], "Test automation engineer", "G3", "Agentic"),
    ("X9.4", 9, "Self-healing test scripts", "UI changes don't break the suite, and every heal is reviewed.",
     ["Locator changes heal automatically during runs", "Every heal is logged for review", "Healed scripts are committed back by pull request"],
     ["Execution engines"], ["aw-test-script-generator"], "Test automation engineer", "G3", "Agentic"),
    ("X9.5", 9, "Niche Accelerate-generated tests and data", "Tests, data and scripts are generated, then reviewed by people.",
     ["Test cases are generated from stories and documents", "Synthetic data is generated per scenario", "Generated assets are reviewed before use"],
     ["Assurance workbench"], ["aw-test-case-generator", "aw-test-data-generator", "aw-test-script-generator"], "QA lead", "G2", "Agentic"),
]

KEYS = ["code", "layer", "name", "what", "checks", "tools", "skills", "owner", "gate", "automation"]


def catalog():
    out = []
    for i, row in enumerate(CATALOG):
        d = dict(zip(KEYS, row))
        d["seq"] = i
        d["layer_name"] = LAYERS[d["layer"]]
        d["cross"] = d["layer"] in CROSS
        out.append(d)
    return out


RULES = [  # (regex on title, case type or None) -> code; first match wins
    (r"tool|agents? .*inherit|agents and cortex", None, "L5.2"),
    (r"declin|outside the semantic|injection", None, "L5.4"),
    (r"golden question|cortex analyst|natural-language|ground", None, "L5.3"),
    (r"mask", None, "X7.2"),
    (r"row access|only (see|sees|data)|own (data|shipments|rows)|customer user only", None, "L6.2"),
    (r"refuses|without access|denied", "negative", "X7.2"),
    (r"scd|history is preserved|scd2", None, "L3.3"),
    (r"history load|backfill|idempot|repeatab", None, "L2.4"),
    (r"row counts? match|reconcil|ledger", None, "L3.1"),
    (r"certified kpi|match the certified|matches legacy|within tolerance|legacy", None, "L4.1"),
    (r"freshness|land within|late feeds|sla", None, "X8.3"),
    (r"under \d+ ?s|respond|latency|warehouse size|budget", None, "X8.4"),
    (r"\b(get|post|put|delete)\s+/", None, "L6.3"),
]
BY_TYPE = {"api": "L6.3", "ui": "L6.1", "performance": "X8.4", "security": "X7.2", "data": "L3.1", "negative": "X7.2"}


def classify_test_type(title: str, ctype: str) -> str:
    t = (title or "").lower()
    for rx, typ, code in RULES:
        if (typ is None or typ == ctype) and re.search(rx, t):
            return code
    return BY_TYPE.get(ctype, "L6.1")
