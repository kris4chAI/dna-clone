---
name: aw-lakehouse-test-strategy
description: "Write the test strategy for a Snowflake open-lakehouse platform layer by layer: every test type with what it proves, its checks, Snowflake features, skills, owner and gate, current coverage and the gaps to close."
---

# Lakehouse test strategy (assurance)

## The reference architecture

| Band | Layer | Test types |
|---|---|---|
| Data foundation · open lakehouse | 1 Source systems | Source profiling and discovery · Data requirements and SLA definition · Source-to-target mapping review · Test data management: masking, synthetic |
| | 2 Ingestion and access | Schema and ingestion validation · CDC completeness and ordering · Streaming latency and loss checks · Row counts, checksums, file formats |
| | 3 Lakehouse core | Bronze, silver and gold reconciliation · Transformation and business rules · SCD and golden-dataset regression · Data contracts: completeness, freshness |
| Context, AI and agents | 4 Context and semantics | Metric parity with legacy · Semantic-layer definition tests · Ontology and glossary consistency · Knowledge and vector corpus validation |
| | 5 Intelligence and agents | ML model validation and drift · Agent evaluation, tool-call safety · LLM output accuracy, groundedness · Guardrail red-teaming, prompt evals |
| Experience and action | 6 Applications and delivery | BI and dashboard validation · Row-level security tests · Data app, API and sharing tests · UAT and parallel-run sign-off |
| Cross-cutting | 7 Governance and security | Catalog and lineage checks · Access-policy and masking tests · Residency checks · Audit trails and traceability · Master data validation |
| | 8 Observability and FinOps | Pipeline and data observability · ML-based DQ scoring and alerts · SLA and incident triage · Performance and stress tests · Cost per query, job and run |
| | 9 Test automation and DevOps | Tests as code in CI/CD · Automated promotion gates · Impact-based test selection · Self-healing test scripts · Niche Accelerate-generated tests and data |

## Method

1. For each test type, state what it proves and three testable checks.
2. Name the Snowflake features and tools, the skills that generate or run it, the owner and the gate it evidences (G1 PRD, G2 design, G3 verified in production).
3. Measure coverage from the workbench: Covered (cases exist and the latest runs pass), At risk (a latest run failed), Planned (cases not yet run), Gap (no cases).
4. Close gaps by generating cases for the test type (one case per check), then plan and run them.
5. Re-run the strategy each wave; the map is the evidence for the gate review and the PMO steering pack.

## Output

`lakehouse_test_strategy.md`: status counts, every test type by layer with coverage, and the list to close next.
