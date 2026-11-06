"""Discover and design skills: PRD, pull request, estate discovery, wave planning, solution design."""
import re
from collections import defaultdict
from datetime import date

from . import Field, header, ident, lit, skill, to_yaml


@skill(name="pi-define-requirements", stage="discover", agent="PRD Agent", title="Define requirements (PRD)",
       description="Turn one prompt plus clarifying answers into a product requirements document, check the persona and map every data need to a Snowflake object or a logged gap.",
       snowflake=["SNOWFLAKE.ACCOUNT_USAGE.TABLES / COLUMNS (catalog probe)", "Horizon catalog search"],
       fields=[Field("need", "The need in one prompt", "textarea", "Give DC general managers a live view of wave progress and labour against plan so every order ships by cut-off."),
               Field("persona", "Persona", "text", "Warehouse, DC & site ops (DC GM · shift managers)"),
               Field("pain_points", "Pain points (one per line)", "lines", "Bottlenecks found after the shift\nLabour planned in spreadsheets\nNumbers differ between WMS and BI"),
               Field("outcomes", "Outcomes with numeric targets (outcome | metric | target)", "lines", "Ship on time | On-time ship % | 98%\nRecover backlog before cut-off | Units at risk at 14:00 | < 500\nLabour to standard | UPH | +8%"),
               Field("data_needs", "Data needs (one concept per line)", "lines", "warehouse task\nwave\nlabor activity\ndock appointment\nengineered standard"),
               Field("scope_out", "Out of scope", "lines", "Robot telemetry (discovery only)\nPayroll"),
               Field("database", "Snowflake database to probe", "text", "FLYHIGH_PRD_GOLD")],
       steps=["Read the need and persona; ask only for missing outcomes or data needs.",
              "Confirm the persona against the persona catalogue; log a gap if it is new.",
              "Run catalog_probe.sql in Snowflake to map each data need to existing objects; anything without a match becomes a data gap.",
              "Confirm numeric targets with the business owner before raising the PR."],
       gate="G1 · product owner approves the PRD in a pull request")
def define_requirements(p, sk):
    outcomes = [[x.strip() for x in l.split("|")] + ["", "", ""] for l in p.lines("outcomes")]
    needs = p.lines("data_needs")
    prd = [f"# PRD: {p.s('need')[:80]}", "", f"*Status: draft · {date.today()} · gate G1 pending*", "",
           "## Problem", p.s("need"), "", "## Persona", f"- {p.s('persona')}", "",
           "## Pain points", *[f"- {x}" for x in p.lines("pain_points")], "",
           "## Outcomes and targets", "| Outcome | Metric | Target | Confirmed by |", "|---|---|---|---|",
           *[f"| {o[0]} | {o[1]} | {o[2]} | [business owner] |" for o in outcomes], "",
           "## Data needs", "| Concept | Snowflake object | Status |", "|---|---|---|",
           *[f"| {n} | [from catalog_probe.sql] | To confirm |" for n in needs], "",
           "## Out of scope", *[f"- {x}" for x in p.lines("scope_out")], "",
           "## Non-functional", "- Freshness: [minutes]", "- Filter response under 5 s on production volumes", "- Row access per site and customer", "",
           "## Open questions", "- [question] · owner · due", ""]
    db = ident(p.s("database"))
    probe = header(sk, "map data needs to existing Snowflake objects")
    probe += "-- Requires a role with IMPORTED PRIVILEGES on the SNOWFLAKE database\n"
    probe += "WITH needs(concept) AS (SELECT column1 FROM VALUES " + ", ".join(f"({lit(n)})" for n in needs) + ")\n"
    probe += ("SELECT n.concept, t.table_catalog, t.table_schema, t.table_name, t.row_count, t.comment\n"
              "FROM needs n\nLEFT JOIN SNOWFLAKE.ACCOUNT_USAGE.TABLES t\n"
              f"  ON t.deleted IS NULL AND t.table_catalog = {lit(db)}\n"
              " AND (t.table_name ILIKE '%' || REPLACE(n.concept, ' ', '_') || '%' OR t.comment ILIKE '%' || n.concept || '%')\n"
              "ORDER BY n.concept, t.row_count DESC NULLS LAST;\n")
    return {"files": {"prd.md": "\n".join(prd), "catalog_probe.sql": probe},
            "summary": f"PRD drafted with {len(outcomes)} targets and {len(needs)} data needs to map.",
            "notes": ["Targets stay [business owner] until confirmed; G1 cannot pass without them."]}


@skill(name="pi-commit-and-raise-pull-request", stage="discover", agent="PRD Agent", title="Commit and raise pull request",
       description="Create the branch, conventional commit and pull request (with reviewers and the gate checklist) for a PRD or design artefact.",
       snowflake=["Artefacts versioned next to Snowflake code"],
       fields=[Field("artefact", "Artefact path", "text", "docs/prd/site-daily-operations.md"),
               Field("kind", "Kind", "choice", "prd", options=["prd", "design", "adr", "code"]),
               Field("title", "Short title", "text", "Site daily operations PRD"),
               Field("reviewers", "Reviewers (GitHub handles, one per line)", "lines", "product-owner\narchitecture-lead"),
               Field("ticket", "Ticket key", "text", "FH-101")],
       steps=["Check the artefact passes its own checklist.", "Run raise_pr.sh from the repository root.", "Paste the PR link into the gate log."],
       gate="The named approver reviews the PR; merging records the gate")
def raise_pr(p, sk):
    slug = re.sub(r"[^a-z0-9]+", "-", p.s("title").lower()).strip("-")
    branch = f"{p.s('kind')}/{p.s('ticket').lower()}-{slug}"
    typ = {"prd": "docs", "design": "docs", "adr": "docs", "code": "feat"}[p.s("kind")]
    msg = f"{typ}({p.s('kind')}): {p.s('title')} [{p.s('ticket')}]"
    gate = {"prd": "G1 · PRD approved", "design": "G2 · Solution design approved", "adr": "Architecture decision", "code": "Peer review"}[p.s("kind")]
    body = [f"## {p.s('title')}", "", f"Ticket: {p.s('ticket')} · Gate: **{gate}**", "", "### Checklist",
            "- [ ] Persona confirmed against the catalogue", "- [ ] Every data need mapped or logged as a gap",
            "- [ ] Numeric targets confirmed by the business", "- [ ] Unvalidated items stamped", "- [ ] Links to standards and ADRs"]
    sh = ["#!/usr/bin/env bash", "set -euo pipefail", f"git checkout -b {branch}", f"git add {p.s('artefact')!r}",
          f"git commit -m {msg!r}", f"git push -u origin {branch}",
          "gh pr create --title " + repr(msg) + " --body-file pr_body.md " + " ".join(f"--reviewer {r}" for r in p.lines("reviewers"))]
    return {"files": {"raise_pr.sh": "\n".join(sh) + "\n", "pr_body.md": "\n".join(body) + "\n"}, "summary": f"Branch {branch} ready."}


@skill(name="discover", stage="discover", agent="Estate Analyzer agent", title="Estate discovery",
       description="Profile the legacy Oracle estate and the Snowflake account: objects, sizes, usage, lineage and report consumers, ready for wave planning.",
       snowflake=["ACCOUNT_USAGE.TABLES", "ACCOUNT_USAGE.ACCESS_HISTORY (lineage)", "ACCOUNT_USAGE.QUERY_HISTORY"],
       fields=[Field("schemas", "Legacy Oracle schemas (one per line)", "lines", "WMS_DW\nOTM_DW\nBI_STAGE"),
               Field("days", "Usage window (days)", "number", "90"),
               Field("database", "Snowflake database to profile", "text", "FLYHIGH_DEV_BRONZE")],
       steps=["Run oracle_inventory.sql on the legacy database and export the result to inventory.csv.",
              "Run snowflake_profile.sql to see what has landed and who reads it.", "Feed inventory.csv to /plan-waves."],
       gate="Migration lead reviews the inventory before waves are planned")
def discover(p, sk):
    sch = ", ".join(lit(ident(s)) for s in p.lines("schemas"))
    ora = ("-- Oracle legacy inventory: objects, sizes and dependencies (run as a DBA or with SELECT_CATALOG_ROLE)\n"
           f"SELECT o.owner, o.object_name, o.object_type, NVL(s.bytes,0)/1024/1024 AS size_mb, o.last_ddl_time,\n"
           "       (SELECT LISTAGG(d.referenced_name, ';') WITHIN GROUP (ORDER BY d.referenced_name)\n"
           "          FROM all_dependencies d WHERE d.owner = o.owner AND d.name = o.object_name) AS depends_on\n"
           "FROM all_objects o\nLEFT JOIN dba_segments s ON s.owner = o.owner AND s.segment_name = o.object_name\n"
           f"WHERE o.owner IN ({sch}) AND o.object_type IN ('TABLE','VIEW','MATERIALIZED VIEW','PROCEDURE','PACKAGE','FUNCTION','SEQUENCE')\n"
           "ORDER BY o.owner, o.object_type, o.object_name;\n")
    days = int(p.n("days", 90))
    db = lit(ident(p.s("database")))
    sf = header(sk, "profile landed objects, usage and lineage")
    sf += (f"-- 1. Objects and sizes\nSELECT table_schema, table_name, row_count, bytes/POWER(1024,3) AS gb, last_altered\n"
           f"FROM SNOWFLAKE.ACCOUNT_USAGE.TABLES WHERE table_catalog = {db} AND deleted IS NULL ORDER BY bytes DESC;\n\n"
           f"-- 2. Who reads what (last {days} days)\n"
           "SELECT f.value:\"objectName\"::STRING AS object_name, COUNT(DISTINCT ah.user_name) AS users, COUNT(*) AS reads\n"
           "FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY ah, LATERAL FLATTEN(ah.base_objects_accessed) f\n"
           f"WHERE ah.query_start_time > DATEADD(day, -{days}, CURRENT_TIMESTAMP())\n"
           f"  AND f.value:\"objectName\"::STRING ILIKE {lit(ident(p.s('database')) + '.%')}\nGROUP BY 1 ORDER BY reads DESC;\n\n"
           "-- 3. Column-level lineage written by DML\n"
           "SELECT ah.query_start_time, w.value:\"objectName\"::STRING AS target, s.value:\"objectName\"::STRING AS source\n"
           "FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY ah, LATERAL FLATTEN(ah.objects_modified) w,\n"
           "     LATERAL FLATTEN(w.value:\"columns\") c, LATERAL FLATTEN(c.value:\"directSources\", OUTER => TRUE) s\n"
           f"WHERE ah.query_start_time > DATEADD(day, -{days}, CURRENT_TIMESTAMP()) LIMIT 1000;\n")
    csvh = "object,type,schema,size_mb,depends_on,complexity,usage\nFACT_WAREHOUSE_TASK,TABLE,WMS_DW,5120,DIM_SITE;DIM_ITEM,medium,high\n"
    return {"files": {"oracle_inventory.sql": ora, "snowflake_profile.sql": sf, "inventory_template.csv": csvh},
            "summary": f"Discovery queries for {len(p.lines('schemas'))} Oracle schemas and the {p.s('database')} database."}


@skill(name="plan-waves", stage="discover", agent="Estate Analyzer agent", title="Plan migration waves",
       description="Order objects into dependency-safe migration waves (topological sort) with a size cap per wave and complexity scoring.",
       snowflake=["Wave plan drives Snowflake AIM and schemachange folders"],
       fields=[Field("inventory", "Inventory CSV (object,type,depends_on,complexity,usage)", "table",
                     "object,type,depends_on,complexity,usage\nDIM_DATE,TABLE,,low,high\nDIM_SITE,TABLE,,low,high\nDIM_ITEM,TABLE,,low,high\nDIM_CUSTOMER,TABLE,,medium,high\n"
                     "FACT_WAREHOUSE_TASK,TABLE,DIM_DATE;DIM_SITE;DIM_ITEM;DIM_CUSTOMER,medium,high\nFACT_INVENTORY_DAILY,TABLE,DIM_ITEM;DIM_SITE,medium,high\n"
                     "PKG_LABOR_CALC,PACKAGE,FACT_WAREHOUSE_TASK,high,medium\nDIM_CARRIER,TABLE,,low,high\nFACT_SHIPMENT_LEG,TABLE,DIM_CARRIER;DIM_DATE;DIM_CUSTOMER,high,high\nV_OTIF,VIEW,FACT_SHIPMENT_LEG,medium,high"),
               Field("max_per_wave", "Max objects per wave", "number", "4")],
       steps=["Load the inventory from /discover.", "Run the skill; review cycles and high-complexity objects.", "Agree the wave plan with the migration lead."],
       gate="Migration lead signs the wave plan")
def plan_waves(p, sk):
    rows = p.table("inventory")
    objs = {r["object"]: r for r in rows}
    deps = {o: [d for d in (r.get("depends_on") or "").split(";") if d and d in objs] for o, r in objs.items()}
    level, notes = {}, []

    def lvl(o, seen=()):
        if o in level:
            return level[o]
        if o in seen:
            notes.append(f"Dependency cycle at {o}; placed in its own wave."); return 0
        level[o] = 0 if not deps[o] else 1 + max(lvl(d, seen + (o,)) for d in deps[o])
        return level[o]
    for o in objs:
        lvl(o)
    cap = max(1, int(p.n("max_per_wave", 4)))
    waves, by_level = [], defaultdict(list)
    for o, l in level.items():
        by_level[l].append(o)
    weight = {"low": 1, "medium": 2, "high": 3}
    for l in sorted(by_level):
        items = sorted(by_level[l], key=lambda o: (-weight.get(objs[o].get("complexity", "medium"), 2), o))
        for i in range(0, len(items), cap):
            waves.append(items[i:i + cap])
    plan = {"waves": [{"wave": i + 1, "objects": [{"name": o, "type": objs[o]["type"], "complexity": objs[o].get("complexity", "")} for o in w]} for i, w in enumerate(waves)]}
    md = ["# Wave plan", "", "| Wave | Objects | Complexity points |", "|---|---|---|"]
    for i, w in enumerate(waves):
        md.append(f"| {i+1} | {', '.join(w)} | {sum(weight.get(objs[o].get('complexity','medium'),2) for o in w)} |")
    return {"files": {"waves.yaml": to_yaml(plan) + "\n", "wave_plan.md": "\n".join(md) + "\n"},
            "summary": f"{len(objs)} objects in {len(waves)} waves.", "notes": notes}


@skill(name="pi-design-solution", stage="design", agent="Solution Design Agent", title="Design the solution",
       description="Draft the solution design from an approved PRD: Snowflake architecture (databases, warehouses, roles), interfaces, NFRs and a scope.yaml traceability map to Jira.",
       snowflake=["Database per layer and environment", "Warehouses per workload", "Database roles", "Semantic views"],
       fields=[Field("prd_title", "PRD title", "text", "Site daily operations"),
               Field("requirements", "Requirements (id | text)", "lines", "R1 | Live UPH by zone every 15 minutes\nR2 | Burn-down of units at risk against cut-off\nR3 | Row access per site"),
               Field("components", "Components (name | type | requirements)", "lines",
                     "FACT_WAVE_PROGRESS | gold table | R1,R2\nSV_SITE_OPS | semantic view | R1,R2\nRAP_SITE | row access policy | R3\nSite Daily Operations | tableau workbook | R1,R2,R3"),
               Field("project_key", "Jira project key", "text", "FH")],
       steps=["Start from the merged PRD.", "Generate the design and scope.yaml; add ADRs for each decision.", "Accept, edit or skip the proposed reviewers; run the checklist."],
       gate="G2 · architecture lead approves the design")
def design_solution(p, sk):
    reqs = [[x.strip() for x in l.split("|", 1)] for l in p.lines("requirements")]
    comps = [[x.strip() for x in l.split("|")] for l in p.lines("components")]
    scope = {"prd": p.s("prd_title"), "requirements": [{"id": r[0], "text": r[1] if len(r) > 1 else ""} for r in reqs],
             "components": [{"name": c[0], "type": c[1] if len(c) > 1 else "", "satisfies": (c[2] if len(c) > 2 else "").split(","),
                             "jira": f"{p.s('project_key')}-[auto]"} for c in comps]}
    uncovered = [r[0] for r in reqs if not any(r[0] in (c[2] if len(c) > 2 else "") for c in comps)]
    md = [f"# Solution design: {p.s('prd_title')}", "", "## Target behaviour", "[from PRD]", "",
          "## Snowflake architecture",
          "| Layer | Database (per env) | Notes |", "|---|---|---|",
          "| Bronze | FLYHIGH_<ENV>_BRONZE | Raw replicas; transient where reloadable |",
          "| Silver | FLYHIGH_<ENV>_SILVER | Normalized, source-aligned |",
          "| Gold | FLYHIGH_<ENV>_GOLD | Star schemas + semantic views |", "",
          "Warehouses: WH_INGEST (XS, auto-suspend 60), WH_TRANSFORM (S), WH_BI (M, multi-cluster 1–3).", "",
          "## Components", "| Component | Type | Satisfies |", "|---|---|---|",
          *[f"| {c[0]} | {c[1] if len(c)>1 else ''} | {c[2] if len(c)>2 else ''} |" for c in comps], "",
          "## Non-functional requirements", "- Availability: [x]% · Freshness: [minutes] · Filters < 5 s · RPO/RTO via Time Travel + replication [values]", "",
          "## Decisions", "- ADR-001: [decision] (see docs/adr)", "", "## Checklist",
          "- [ ] PRD linked", "- [ ] Standards and ADRs linked", "- [ ] Every requirement traced in scope.yaml"]
    notes = [f"Requirements without a component: {', '.join(uncovered)}"] if uncovered else []
    return {"files": {"solution_design.md": "\n".join(md) + "\n", "scope.yaml": to_yaml(scope) + "\n"},
            "summary": f"{len(comps)} components tracing {len(reqs)} requirements.", "notes": notes}
