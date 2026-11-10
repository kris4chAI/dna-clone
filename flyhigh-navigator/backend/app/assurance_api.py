"""Assurance lens: the assurance workbench (design, execution, analytics, maintenance).

Modelled on an AI test-assurance workbench: generate test cases from user stories or documents, synthetic
test data from the data model, keyword-driven scripts; manage engines, devices, releases, test plans and
executions (with self-healing and failure analysis); summarize results, defects and hotspots; and map test
cases to code for impact-based regression.

Every engine here is deterministic, so the workbench runs without an LLM. Executions run on the built-in
simulator unless a real engine is connected; the UI says so.
"""
import csv
import hashlib
import io
import json
import re
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from . import llm
from .access import screen
from .db import conn

router = APIRouter(prefix="/api/assurance")


# ---------------------------------------------------------------------------
# DB executor that works inside the seeding transaction and at runtime
# ---------------------------------------------------------------------------
class X:
    def __init__(self, c=None):
        self.c = c

    def q(self, sql, p=()):
        if self.c is not None:
            return self.c.execute(sql, p).fetchall()
        with conn() as c:
            return c.execute(sql, p).fetchall()

    def one(self, sql, p=()):
        r = self.q(sql, p) if sql.lstrip().upper().startswith("SELECT") else None
        if r is not None:
            return r[0] if r else None
        if self.c is not None:
            cur = self.c.execute(sql, p)
        else:
            with conn() as c:
                cur = c.execute(sql, p)
                return cur.fetchone() if cur.description else None
        return cur.fetchone() if cur.description else None


DB = X()


def h01(*parts) -> float:
    return int(hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


TOK = re.compile(r"[a-z0-9]+")
STOP = set("a an the of to in on for and or is are be as by with i we my our it this that so from at when only can see shows show user users".split())


def toks(s):
    return {t for t in TOK.findall((s or "").lower()) if t not in STOP and len(t) > 2}


# ---------------------------------------------------------------------------
# Seed content
# ---------------------------------------------------------------------------
PLATFORM_STORIES = [
    ("Reconciliation to legacy", "Platform migration", "Testing lead",
     "As a testing lead, I want every migrated measure reconciled to Oracle ADW so that business users trust the new numbers.",
     ["Row counts match legacy per table and load date", "Every certified measure matches legacy within tolerance or the variance is signed off",
      "The reconciliation ledger records each run"], "High"),
    ("Customer row access", "Security", "Data governance lead",
     "As a data governance lead, I want customers to see only their own shipments so that we meet contractual confidentiality.",
     ["A customer user only sees rows for their customer", "Sensitive carrier rates are masked for non-finance roles",
      "Agents and Cortex inherit the same row access"], "High"),
    ("Feed freshness", "Data products", "Platform operations",
     "As platform operations, I want every feed to land within its SLA so that dashboards show current data.",
     ["WMS feeds land within 15 minutes", "Late feeds raise an alert to the owner", "Freshness is visible on each dashboard"], "Medium"),
    ("History load", "Platform migration", "Migration lead",
     "As the migration lead, I want 22 TB of history loaded and verified so that trend reports keep working after cut-over.",
     ["History loads for every fact table complete", "SCD2 history is preserved for dimensions", "Load is repeatable and idempotent"], "High"),
    ("Dashboard performance", "BI modernization", "BI lead",
     "As the BI lead, I want dashboard filters to respond in under 5 s at production volume so that users adopt the new dashboards.",
     ["Filters respond in under 5 s on live data", "Warehouse size is within the agreed budget"], "Medium"),
    ("Natural-language questions", "Cortex AI", "Product owner",
     "As a product owner, I want Cortex Analyst to answer the golden questions correctly so that self-service is trustworthy.",
     ["Golden questions answer within tolerance of the certified KPI", "Questions outside the semantic model are declined"], "Medium"),
]

FRAMEWORK = [
    ("app", "Tableau Cloud dashboards", "Warehouse, transportation and executive dashboards on live Snowflake connections"),
    ("app", "Customer portal", "External customer dashboards with per-customer row access"),
    ("app", "Snowflake data platform", "Bronze, Silver and Gold zones, dbt models, procedures and tasks"),
    ("app", "Cortex Analyst", "Natural-language questions over certified semantic views"),
    ("component", "Login", "Sign in through SSO as a given role"),
    ("component", "NavigateTo", "Open a dashboard, page or view"),
    ("component", "ApplyFilter", "Set a dashboard filter or parameter"),
    ("component", "ReadKpiTile", "Read the value shown on a KPI tile"),
    ("component", "RunSql", "Run a SQL query on Snowflake as the test role"),
    ("component", "CompareToLegacy", "Run the golden query on legacy and Snowflake and compare"),
    ("component", "AssertRowAccess", "Check that only permitted rows are returned"),
    ("component", "AssertMasked", "Check that a sensitive column is masked for the role"),
    ("component", "MeasureLatency", "Time an interaction against a threshold"),
    ("component", "AskCortex", "Ask Cortex Analyst a question and read the answer"),
    ("component", "AssertDenied", "Check that access is refused"),
    ("suite", "Smoke", "Fast checks run on every deployment"),
    ("suite", "Regression", "Full functional regression per wave"),
    ("suite", "Reconciliation", "Measures and row counts against legacy"),
    ("suite", "Security", "Masking, row access and role tests"),
    ("suite", "Performance", "Latency and load at production volume"),
    ("service", "Snowflake SQL API", "Key-pair authenticated SQL execution"),
    ("service", "Tableau REST API", "Sites, workbooks and permissions"),
    ("service", "Jira", "User stories and defects"),
    ("service", "GitHub Actions", "CI/CD triggers and results"),
]

MODULES = [  # path, module, kind, keywords, lines, covered
    ("models/gold/fct_shipment.sql", "Shipment fact", "dbt model", "shipment otif delivery carrier transport late on time", 420, 360),
    ("models/gold/fct_order_line.sql", "Order line fact", "dbt model", "order line fill rate customer pick", 380, 290),
    ("models/gold/fct_inventory_snapshot.sql", "Inventory snapshot", "dbt model", "inventory stock accuracy dwell warehouse", 310, 180),
    ("models/gold/fct_labour.sql", "Labour fact", "dbt model", "labour productivity hours units shift workforce", 260, 120),
    ("models/silver/dim_customer_scd2.sql", "Customer dimension (SCD2)", "dbt model", "customer history scd2 dimension account", 190, 170),
    ("procs/sp_load_wms_incremental.sql", "WMS incremental load", "stored procedure", "wms feed freshness load incremental sla late", 540, 300),
    ("procs/sp_history_backfill.sql", "History backfill", "stored procedure", "history load backfill idempotent repeatable", 300, 150),
    ("policies/rap_customer.sql", "Customer row access policy", "policy", "row access customer confidentiality security role", 80, 80),
    ("policies/mask_carrier_rate.sql", "Carrier rate masking", "policy", "masked sensitive carrier rate finance masking", 60, 60),
    ("semantic/sv_kpi_certified.yaml", "Certified KPI semantic view", "semantic view", "kpi certified measure golden question cortex analyst otif fill rate", 240, 200),
    ("tableau/warehouse_ops.twb", "Warehouse operations workbook", "dashboard", "warehouse dashboard dwell inventory pick productivity filter", 0, 0),
    ("tableau/transport_control_tower.twb", "Transport control tower", "dashboard", "transport dispatcher otif late shipment carrier dashboard filter", 0, 0),
    ("tableau/customer_portal.twb", "Customer portal workbook", "dashboard", "customer portal external shipment status own", 0, 0),
    ("tableau/executive_scorecard.twb", "Executive scorecard", "dashboard", "executive kpi scorecard cost revenue margin", 0, 0),
    ("recon/ledger_reconcile.py", "Reconciliation harness", "test harness", "reconcile legacy oracle row count measure tolerance ledger variance", 210, 190),
    ("cortex/agent_config.yaml", "Cortex agent configuration", "agent", "cortex analyst question golden decline semantic", 90, 40),
]

RELEASES = [("R1 · Pilot wave", "Track A and B pilots: 5 + 7 dashboards, HR pages", -60, -10),
            ("R2 · Wave 1", "15 warehouse dashboards, 11 customer dashboards", -5, 40),
            ("R3 · Wave 2", "15 dashboards, transport reports, HR pack", 35, 85)]
ENGINES = [("Local runner", "Local", 365, "Ready"), ("Snowflake DEV cluster", "Cluster", 180, "Ready"), ("Nightly cluster (CI)", "Cluster", 90, "Ready")]
DEVICES = [("Chrome desktop", "Browser", "Windows 11", "UAT"), ("Safari iPad", "Tablet", "iPadOS 18", "UAT"),
           ("Edge desktop", "Browser", "Windows 11", "SIT"), ("Headless Chromium", "Browser", "Linux", "CI")]


def seed_assurance(c):
    x = X(c)
    for kind, name, desc in FRAMEWORK:
        c.execute("INSERT INTO aw_component(kind,name,description) VALUES (%s,%s,%s)", (kind, name, desc))
    n = 100
    for r in x.q("""SELECT p.name AS persona, p.segment, j.name, j.question, j.experience, j.metrics
                    FROM journey_step j JOIN persona p ON p.id=j.persona_id ORDER BY p.id, j.seq"""):
        n += 1
        crit = [f"Answers “{r['question']}”" if r["question"] else None,
                f"Shows {r['metrics']}" if r["metrics"] else None,
                "Numbers match the certified KPI definition",
                "Only data the user may see is shown",
                "Filters respond in under 5 s"]
        feature = {"Internal": "BI modernization", "External": "Customer portal"}.get((r["segment"] or "").split()[0], "BI modernization")
        c.execute("""INSERT INTO aw_story(key,title,feature,persona,narrative,acceptance,source,priority)
                     VALUES (%s,%s,%s,%s,%s,%s,'Persona journeys',%s)""",
                  (f"FLY-{n}", r["name"], feature, r["persona"],
                   f"As {r['persona']}, I want to answer “{r['question'] or r['name']}” so that {r['experience'] or 'I can act on it'}.",
                   json.dumps([x_ for x_ in crit if x_]), "High" if n % 3 == 1 else "Medium"))
    for title, feature, persona, narrative, acc, pri in PLATFORM_STORIES:
        n += 1
        c.execute("""INSERT INTO aw_story(key,title,feature,persona,narrative,acceptance,source,priority)
                     VALUES (%s,%s,%s,%s,%s,%s,'Jira · FLY',%s)""", (f"FLY-{n}", title, feature, persona, narrative, json.dumps(acc), pri))
    for path, mod, kind, kw, lines, cov in MODULES:
        c.execute("INSERT INTO aw_module(path,module,kind,keywords,lines,covered) VALUES (%s,%s,%s,%s,%s,%s)", (path, mod, kind, kw, lines, cov))
    today = date.today()
    for name, desc, s, e in RELEASES:
        c.execute("INSERT INTO aw_release(name,description,start_date,release_date) VALUES (%s,%s,%s,%s)",
                  (name, desc, today + timedelta(days=s), today + timedelta(days=e)))
    for name, typ, days, st in ENGINES:
        c.execute("INSERT INTO aw_engine(name,type,status,expires) VALUES (%s,%s,%s,%s)", (name, typ, st, today + timedelta(days=days)))
    for d in DEVICES:
        c.execute("INSERT INTO aw_device(name,type,platform,environment) VALUES (%s,%s,%s,%s)", d)

    # A first suite from every story, a dataset, scripts, plans and three cycles, so every screen has data.
    stories = [r["id"] for r in x.q("SELECT id FROM aw_story ORDER BY id")]
    suite = generate_cases(x, "stories", story_ids=stories, name="FlyHigh regression · v1", who="seed")
    ent = x.one("SELECT id FROM data_entity WHERE kind='fact' ORDER BY id LIMIT 1")
    if ent:
        generate_data(x, entity_id=ent["id"], rows=25, scenarios=["valid", "boundary", "invalid", "masked"], who="seed")
    cases = x.q("SELECT id, type, key FROM aw_case WHERE suite_id=%s ORDER BY id", (suite["id"],))
    for cs in cases[:6]:
        generate_script(x, cs["id"], "Keyword driven", who="seed")
    remap(x)
    rel = {r["name"]: r["id"] for r in x.q("SELECT id, name FROM aw_release")}
    ids = [cs["id"] for cs in cases]
    smoke = [cs["id"] for cs in cases if cs["type"] in ("functional", "data")][:14]
    secrec = [cs["id"] for cs in cases if cs["type"] in ("data", "security")]
    p1 = x.one("INSERT INTO aw_plan(name,release_id,case_ids,suite) VALUES (%s,%s,%s,'Smoke') RETURNING id", ("Pilot smoke", rel["R1 · Pilot wave"], smoke))["id"]
    p2 = x.one("INSERT INTO aw_plan(name,release_id,case_ids,suite) VALUES (%s,%s,%s,'Regression') RETURNING id", ("Pilot regression", rel["R1 · Pilot wave"], ids))["id"]
    p3 = x.one("INSERT INTO aw_plan(name,release_id,case_ids,suite) VALUES (%s,%s,%s,'Reconciliation') RETURNING id", ("Reconciliation and security", rel["R2 · Wave 1"], secrec))["id"]
    c.execute("""INSERT INTO aw_cicd(name,pipeline,release_id,failure_analysis,self_healing,config,schedule)
                 VALUES ('Nightly regression','GitHub Actions · flyhigh-dbt / nightly',%s,TRUE,TRUE,'on: schedule (02:00 UTC) · engine Nightly cluster (CI)','Daily 02:00 UTC'),
                        ('Merge smoke','GitHub Actions · flyhigh-dbt / pr-merge',%s,TRUE,FALSE,'on: push to main · engine Local runner','On merge')""",
              (rel["R2 · Wave 1"], rel["R2 · Wave 1"]))
    run_plan(x, p1, "Snowflake DEV cluster", "Chrome desktop", True, True, who="seed", trigger="Manual")
    run_plan(x, p2, "Snowflake DEV cluster", "Chrome desktop", True, True, who="seed", trigger="Manual")
    run_plan(x, p2, "Nightly cluster (CI)", "Headless Chromium", True, True, who="seed", trigger="CI/CD")
    run_plan(x, p3, "Snowflake DEV cluster", "Edge desktop", False, True, who="seed", trigger="Manual")
    c.execute("UPDATE aw_module SET changed=TRUE WHERE path IN ('procs/sp_load_wms_incremental.sql','policies/rap_customer.sql')")


# ---------------------------------------------------------------------------
# Design: test cases, test data, scripts
# ---------------------------------------------------------------------------
def classify(text):
    t = text.lower()
    if re.search(r"reconcil|legacy|match|row count|history|scd|idempot|repeatab|load", t):
        return "data"
    if re.search(r"only|row access|mask|role|confidential|inherit|denied|declin", t):
        return "security"
    if re.search(r"under \d+ ?s|latency|perform|respond|within \d+ minutes|budget", t):
        return "performance"
    if re.search(r"\b(get|post|put|delete)\s+/", t):
        return "api"
    return "functional"


STEPS = {
    "functional": ["Sign in as {persona}", "Open the {feature} view for “{title}”", "Apply the default filters", "Read the values shown", "Check: {crit}"],
    "data": ["Run the golden query on legacy and on Snowflake", "Compare row counts and measures for the same load date", "Check: {crit}", "Record the result in the reconciliation ledger"],
    "security": ["Sign in as a restricted role ({persona} without elevated rights)", "Open “{title}”", "Query or view the protected data", "Check: {crit}"],
    "performance": ["Sign in as {persona}", "Open “{title}” at production volume", "Change each filter and time the response", "Check: {crit}"],
    "api": ["Call {crit} with a valid token", "Check status 200 and the response schema", "Call it without a token", "Check status 401 or 403"],
    "negative": ["Sign in as a user without access to “{title}”", "Try to open it", "Check that access is refused and nothing leaks", "Check the attempt is logged"],
    "ui": ["Open the screen “{crit}”", "Check every control renders and is labelled", "Navigate every link and back", "Check layout at desktop and tablet widths"],
}
EXPECT = {"functional": "The view answers the question with the certified values.", "data": "Counts and measures match legacy, or the variance is recorded for sign-off.",
          "security": "Only permitted rows and unmasked columns are visible.", "performance": "Every interaction completes inside the threshold.",
          "api": "Authorised calls succeed with a valid schema; others are refused.", "negative": "Access is refused and logged.",
          "ui": "The screen renders and navigates as designed."}


def _case_rows(items):
    """items: [{story_key, title, feature, persona, priority, criteria:[...] , kind}] → case dicts"""
    out = []
    for it in items:
        for crit in it["criteria"]:
            typ = "ui" if it.get("kind") == "ui" else ("api" if it.get("kind") == "api" else classify(crit))
            out.append({**it, "type": typ, "crit": crit, "title_c": f"{it['title']}: {crit}"})
        if it.get("kind") not in ("ui", "api"):
            out.append({**it, "type": "negative", "crit": "access refused", "title_c": f"{it['title']}: refuses users without access"})
    return out


def generate_cases(x, source, story_ids=None, doc_type=None, doc_text=None, name=None, who="app", feature=None):
    if source == "stories":
        if story_ids:
            st = x.q("SELECT * FROM aw_story WHERE id = ANY(%s) ORDER BY id", (list(story_ids),))
        else:
            st = x.q("SELECT * FROM aw_story WHERE (%s::text IS NULL OR feature=%s) ORDER BY id", (feature, feature))
        items = [{"story_key": s["key"], "title": s["title"], "feature": s["feature"], "persona": s["persona"], "priority": s["priority"],
                  "criteria": s["acceptance"]} for s in st]
        ref = f"{len(st)} user stories"
    else:
        lines = [l.strip(" -*•\t") for l in (doc_text or "").splitlines() if l.strip(" -*•\t")]
        if not lines:
            raise HTTPException(400, "Paste the document content: one requirement, screen or endpoint per line.")
        kind = {"UI/UX": "ui", "API DOCS": "api"}.get(doc_type or "", "req")
        if kind == "req":
            items = [{"story_key": f"REQ-{i + 1}", "title": l[:70], "feature": "Requirements", "persona": "Business user", "priority": "Medium",
                      "criteria": [l]} for i, l in enumerate(lines)]
        else:
            items = [{"story_key": f"{'UI' if kind == 'ui' else 'API'}-{i + 1}", "title": l[:70], "feature": doc_type, "persona": "User",
                      "priority": "Medium", "criteria": [l], "kind": kind} for i, l in enumerate(lines)]
        ref = f"{doc_type or 'FSD/BRD'} · {len(lines)} lines"
    if not items:
        raise HTTPException(400, "No user stories matched.")
    ver = (x.one("SELECT COALESCE(MAX(version),0)+1 AS v FROM aw_suite")["v"])
    suite = x.one("""INSERT INTO aw_suite(name,source_kind,source_ref,llm,version,created_by) VALUES (%s,%s,%s,%s,%s,%s) RETURNING *""",
                  (name or f"Test suite v{ver}", source if source == "stories" else (doc_type or "FSD/BRD"), ref,
                   (llm.status().get("model") if llm.available() else "Deterministic engine"), ver, who))
    rows = _case_rows(items)
    for i, r in enumerate(rows, 1):
        steps = [s.format(persona=r["persona"], feature=r["feature"], title=r["title"], crit=r["crit"]) for s in STEPS[r["type"]]]
        pri = "High" if r["type"] in ("security", "data") or r["priority"] == "High" else r["priority"]
        x.one("""INSERT INTO aw_case(suite_id,key,title,story_key,feature,type,priority,steps,expected,automation)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
              (suite["id"], f"TC-{suite['version']:02d}-{i:03d}", r["title_c"][:200], r["story_key"], r["feature"], r["type"], pri,
               json.dumps(steps), EXPECT[r["type"]], "Automated" if r["type"] in ("data", "security", "performance", "api") else "Automatable"))
    return suite


def import_cases(x, text, who):
    rd = list(csv.DictReader(io.StringIO(text.strip())))
    if not rd:
        raise HTTPException(400, "Paste CSV with a header: title, story, feature, type, priority, steps, expected.")
    ver = x.one("SELECT COALESCE(MAX(version),0)+1 AS v FROM aw_suite")["v"]
    s = x.one("INSERT INTO aw_suite(name,source_kind,source_ref,llm,version,created_by) VALUES (%s,'import',%s,'Imported',%s,%s) RETURNING *",
              (f"Imported suite v{ver}", f"{len(rd)} rows", ver, who))
    for i, r in enumerate(rd, 1):
        g = {k.lower().strip(): (v or "").strip() for k, v in r.items()}
        typ = g.get("type") or classify(g.get("title", ""))
        x.one("""INSERT INTO aw_case(suite_id,key,title,story_key,feature,type,priority,steps,expected,automation,origin)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'Manual','curated') RETURNING id""",
              (s["id"], f"TC-{ver:02d}-{i:03d}", g.get("title") or f"Imported case {i}", g.get("story"), g.get("feature") or "Imported",
               typ if typ in STEPS else "functional", g.get("priority") or "Medium", json.dumps([t.strip() for t in (g.get("steps") or "").split(";") if t.strip()]),
               g.get("expected")))
    return s


def _val(attr, role, i, scen, seed):
    a = attr.lower()
    u = h01(seed, attr, i)
    if scen == "invalid" and i % 3 == 0:
        return "" if "id" not in a else None
    if "email" in a:
        return "***MASKED***" if scen == "masked" else f"user{i}@example.com"
    if "rate" in a or "cost" in a or "price" in a or "amount" in a or "revenue" in a:
        v = round(10 + u * 990, 2)
        return "***MASKED***" if scen == "masked" and ("rate" in a or "cost" in a) else (-v if scen == "invalid" else (0 if scen == "boundary" and i % 2 else v))
    if "date" in a or a.endswith("_ts") or "time" in a:
        d = date(2026, 1, 1) + timedelta(days=int(u * 300))
        return "2027-02-30" if scen == "invalid" and i % 2 else (str(date(2026, 12, 31)) if scen == "boundary" and i % 2 else str(d))
    if "pct" in a or "percent" in a or "ratio" in a:
        return 100 if scen == "boundary" else (120 if scen == "invalid" else round(u * 100, 1))
    if "qty" in a or "quantity" in a or "count" in a or "units" in a or "hours" in a:
        return 0 if scen == "boundary" else (-1 if scen == "invalid" else int(1 + u * 500))
    if a.endswith("_key") or a.endswith("_id") or a == "id" or "key" in (role or "").lower():
        return 1000 + i
    if "flag" in a or a.startswith("is_"):
        return u > 0.5
    if "name" in a:
        return ["Northgate DC", "Riverside DC", "Harbor Point", "Summit Retail", "Lakeside Stores"][int(u * 5)]
    if "code" in a or "status" in a or "type" in a:
        return ["A", "B", "C", "OPEN", "CLOSED"][int(u * 5)]
    return f"{attr}_{i}"


def generate_data(x, entity_id=None, ddl=None, rows=20, scenarios=None, who="app"):
    scenarios = scenarios or ["valid"]
    if ddl:
        m = re.search(r"create\s+(?:or\s+replace\s+)?table\s+([\w.\"]+)\s*\((.*)\)", ddl, re.I | re.S)
        if m:
            name = m.group(1).strip('"')
            cols = [re.split(r"\s+", c.strip())[0].strip('"') for c in re.split(r",(?![^()]*\))", m.group(2)) if c.strip() and not re.match(r"(?i)\s*(primary|constraint|foreign|unique)", c)]
        else:  # CSV header
            name, cols = "uploaded_schema", [c.strip() for c in ddl.splitlines()[0].split(",") if c.strip()]
        attrs = [{"name": c, "role": ""} for c in cols]
        src = "Schema file"
    else:
        e = x.one("SELECT * FROM data_entity WHERE id=%s", (entity_id,))
        if not e:
            raise HTTPException(404, "Pick an entity from the data model.")
        name = e["name"]
        attrs = [a for a in x.q("SELECT name, role FROM attribute WHERE entity_id=%s ORDER BY id", (entity_id,)) if a["role"] != "placeholder"]
        if not attrs:
            attrs = [{"name": f"{name}_key", "role": "key"}, {"name": "load_date", "role": ""}, {"name": "amount", "role": "measure"}]
        src = f"Data model · {e['model']}"
    if not attrs:
        raise HTTPException(400, "No columns found. Paste CREATE TABLE DDL or a CSV header.")
    rows = max(1, min(int(rows or 20), 200))
    data, n = [], 0
    for scen in scenarios:
        per = max(1, rows // len(scenarios))
        for i in range(per):
            n += 1
            data.append({"_scenario": scen, **{a["name"]: _val(a["name"], a.get("role"), n, scen, name) for a in attrs}})
    cols = [a["name"] for a in attrs]
    lit = lambda v: "NULL" if v is None else ("TRUE" if v is True else "FALSE" if v is False else str(v) if isinstance(v, (int, float)) else "'" + str(v).replace("'", "''") + "'")
    sql = [f"-- Synthetic test data for {name} ({', '.join(scenarios)}). Load into a TEST schema only.",
           f"INSERT INTO TEST_DATA.{name.upper()} ({', '.join(c.upper() for c in cols)}) VALUES"]
    sql.append(",\n".join("  (" + ", ".join(lit(r[c]) for c in cols) + ")" for r in data) + ";")
    expect = [f"-- Expected data-quality outcomes", f"-- valid rows pass every rule; boundary rows sit on the limits; invalid rows must be quarantined"]
    expect += [f"SELECT COUNT(*) AS rejected FROM TEST_DATA.{name.upper()} WHERE {c.upper()} IS NULL;" for c in cols if c.lower().endswith(("_id", "_key"))][:2]
    return x.one("""INSERT INTO aw_dataset(name,schema_source,entity,scenarios,rows,sql,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id, name""",
                 (f"{name} · {'/'.join(scenarios)}", src, name, scenarios, json.dumps(data, default=str), "\n".join(sql) + "\n\n" + "\n".join(expect), who))


KEYWORDS = {
    "functional": [("Login", "{persona}"), ("NavigateTo", "{feature} · {story}"), ("ApplyFilter", "default"), ("ReadKpiTile", "{crit}"), ("AssertEquals", "certified value")],
    "data": [("RunSql", "golden query · {story}"), ("CompareToLegacy", "row counts and measures"), ("AssertWithinTolerance", "0.01%")],
    "security": [("Login", "restricted role"), ("NavigateTo", "{story}"), ("AssertRowAccess", "own rows only"), ("AssertMasked", "sensitive columns")],
    "performance": [("Login", "{persona}"), ("NavigateTo", "{story}"), ("MeasureLatency", "each filter < 5 s")],
    "api": [("CallApi", "{crit} · valid token"), ("AssertStatus", "200 + schema"), ("CallApi", "{crit} · no token"), ("AssertStatus", "401/403")],
    "negative": [("Login", "user without access"), ("NavigateTo", "{story}"), ("AssertDenied", "refused and logged")],
    "ui": [("NavigateTo", "{crit}"), ("AssertRendered", "all controls"), ("AssertLayout", "desktop, tablet")],
}


def generate_script(x, case_id, framework="Keyword driven", who="app"):
    cs = x.one("SELECT * FROM aw_case WHERE id=%s", (case_id,))
    if not cs:
        raise HTTPException(404, "Pick a test case.")
    crit = cs["title"].split(": ", 1)[-1]
    kws = [{"step": i + 1, "keyword": k, "args": a.format(persona="test user", feature=cs["feature"], story=cs["story_key"] or cs["feature"], crit=crit)}
           for i, (k, a) in enumerate(KEYWORDS.get(cs["type"], KEYWORDS["functional"]))]
    fn = re.sub(r"\W+", "_", cs["key"].lower())
    if framework == "BDD":
        code = [f"Feature: {cs['feature']}", f"  Scenario: {cs['title']}"] + \
               [f"    {'Given' if i == 0 else 'When' if i < len(kws) - 1 else 'Then'} {k['keyword']} \"{k['args']}\"" for i, k in enumerate(kws)]
        fname = f"{fn}.feature"
    else:
        code = ["# Generated keyword-driven test. Keywords live in keywords.py (reusable components).", "import pytest", "from keywords import *", "",
                f"@pytest.mark.{(cs['type'])}", f"def test_{fn}(ctx):", f'    """{cs["title"]}\n\n    Expected: {cs["expected"]}\n    """']
        code += [f"    {k['keyword'].lower()}(ctx, {json.dumps(k['args'])})" for k in kws]
        fname = f"test_{fn}.py"
    app = {"data": "Snowflake data platform", "security": "Customer portal" if "customer" in cs["title"].lower() else "Snowflake data platform",
           "api": "Snowflake data platform"}.get(cs["type"], "Cortex Analyst" if "cortex" in cs["title"].lower() else "Tableau Cloud dashboards")
    return x.one("""INSERT INTO aw_script(case_id,framework,app,file,keywords,code,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                 (case_id, framework, app, fname, json.dumps(kws), "\n".join(code), who))


# ---------------------------------------------------------------------------
# Execution (built-in simulator)
# ---------------------------------------------------------------------------
FAIL_P = {"functional": .14, "data": .12, "security": .06, "performance": .2, "api": .08, "negative": .05, "ui": .18}
CAUSES = [("Locator changed", "UI element moved or renamed", "Self-healing updated the locator; review the change"),
          ("Data mismatch", "Measure differs from legacy beyond tolerance", "Trace the conversion of the measure; fix or sign off the variance"),
          ("Environment", "Engine or warehouse unavailable during the run", "Re-run; check engine expiry and warehouse resume"),
          ("Product defect", "Behaviour differs from the acceptance criterion", "Raise a defect with the evidence and fix in the next build"),
          ("Slow query", "Response above the threshold at production volume", "Check the query profile; tune clustering, search optimization or warehouse size")]


def run_plan(x, plan_id, engine, device, self_heal=True, analysis=True, who="app", trigger="Manual"):
    pl = x.one("SELECT * FROM aw_plan WHERE id=%s", (plan_id,))
    if not pl or not pl["case_ids"]:
        raise HTTPException(400, "The test plan has no test cases.")
    seq = x.one("SELECT COUNT(*)+1 AS n FROM aw_cycle")["n"]
    start = datetime.now() - timedelta(days=max(0, 12 - seq * 3), minutes=17)
    cyc = x.one("""INSERT INTO aw_cycle(name,plan_id,release_id,engine,device,started,trigger,self_healing,failure_analysis,created_by)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (f"Cycle {seq} · {pl['name']}", plan_id, pl["release_id"], engine, device, start, trigger, self_heal, analysis, who))["id"]
    cases = x.q("SELECT * FROM aw_case WHERE id = ANY(%s) ORDER BY id", (pl["case_ids"],))
    tot = {"passed": 0, "failed": 0, "skipped": 0, "healed": 0}
    dur = 0
    for cs in cases:
        u = h01(cs["key"], seq, "run")
        ms = int(800 + h01(cs["key"], "d") * 9000)
        dur += ms
        status, cause, healed = "passed", None, False
        if u < 0.03:
            status, cause = "skipped", CAUSES[2]
        elif u < 0.03 + FAIL_P.get(cs["type"], .1) * (0.6 if seq > 2 else 1):
            k = int(h01(cs["key"], seq, "cause") * 4)
            if cs["type"] == "data":
                k = 1 if k in (0, 3) else k
            elif cs["type"] == "performance":
                k = 4 if k in (0, 1) else k
            elif cs["type"] in ("security", "negative", "api"):
                k = 3 if k in (0, 1) else k
            cause = CAUSES[k]
            if k == 0 and self_heal and cs["type"] not in ("data", "api"):
                status, healed = "passed", True
            else:
                status = "failed"
        tot[status] += 1
        tot["healed"] += healed
        x.one("""INSERT INTO aw_result(cycle_id,case_id,status,duration_ms,root_cause,detail,resolution,self_healed) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING 1""",
              (cyc, cs["id"], status, ms, cause[0] if cause and analysis else (cause and "Not analysed"), cause[1] if cause else None,
               cause[2] if cause and analysis else None, healed))
        if status == "failed" and cause and cause[0] in ("Data mismatch", "Product defect", "Slow query"):
            if not x.one("SELECT 1 AS ok FROM aw_defect WHERE case_id=%s AND status<>'Closed'", (cs["id"],)):
                n = x.one("SELECT COUNT(*)+1 AS n FROM aw_defect")["n"]
                sev = "Critical" if cs["priority"] == "High" and cs["type"] in ("security", "data") else "Major" if cs["priority"] == "High" else "Minor"
                mod = x.one("""SELECT m.module FROM aw_mapping mp JOIN aw_module m ON m.id=mp.module_id WHERE mp.case_id=%s ORDER BY mp.score DESC LIMIT 1""", (cs["id"],))
                st = "Closed" if h01(cs["key"], "close") < 0.35 and seq < 3 else "Open"
                x.one("""INSERT INTO aw_defect(key,title,severity,status,case_id,feature,component,cycle_id,cause) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING 1""",
                      (f"DEF-{n:03d}", f"{cause[0]}: {cs['title'][:120]}", sev, st, cs["id"], cs["feature"], mod["module"] if mod else None, cyc, cause[1]))
    x.one("""UPDATE aw_cycle SET ended=%s, status='Completed', total=%s, passed=%s, failed=%s, skipped=%s, self_healed=%s WHERE id=%s RETURNING 1""",
          (start + timedelta(milliseconds=dur), len(cases), tot["passed"], tot["failed"], tot["skipped"], tot["healed"], cyc))
    x.one("UPDATE aw_plan SET last_execution=%s WHERE id=%s RETURNING 1", (start + timedelta(milliseconds=dur), plan_id))
    return cyc


# ---------------------------------------------------------------------------
# Maintenance: test case ↔ code mapping and impact
# ---------------------------------------------------------------------------
def remap(x):
    mods = x.q("SELECT id, path, module, keywords FROM aw_module")
    mt = {m["id"]: toks(m["keywords"] + " " + m["module"] + " " + m["path"].replace("_", " ").replace("/", " ")) for m in mods}
    x.one("DELETE FROM aw_mapping WHERE TRUE RETURNING 1")
    n = 0
    for cs in x.q("SELECT c.id, c.title, c.feature, c.type, s.narrative FROM aw_case c LEFT JOIN aw_story s ON s.key=c.story_key"):
        ct = toks(f"{cs['title']} {cs['feature']} {cs['narrative'] or ''}") | ({"reconcile", "legacy"} if cs["type"] == "data" else set()) | \
            ({"security", "role", "masking"} if cs["type"] == "security" else set()) | ({"filter", "dashboard"} if cs["type"] == "performance" else set())
        sc = sorted(((len(ct & kw) / max(4, len(kw)) * 1.0, mid) for mid, kw in mt.items() if ct & kw), reverse=True)[:3]
        for s, mid in sc:
            if s >= 0.12:
                x.one("INSERT INTO aw_mapping(case_id,module_id,score) VALUES (%s,%s,%s) RETURNING 1", (cs["id"], mid, round(min(1, s * 2.2), 2)))
                n += 1
    return n


PRI_W = {"High": 3, "Medium": 2, "Low": 1}


def impact(x, module_ids):
    rows = x.q("""SELECT c.id, c.key, c.title, c.type, c.priority, c.feature, m.module, m.path, mp.score,
                  (SELECT COUNT(*) FROM aw_result r WHERE r.case_id=c.id AND r.status='failed') AS fails,
                  (SELECT COUNT(*) FROM aw_result r WHERE r.case_id=c.id) AS runs
                  FROM aw_mapping mp JOIN aw_case c ON c.id=mp.case_id JOIN aw_module m ON m.id=mp.module_id
                  WHERE mp.module_id = ANY(%s)""", (list(module_ids),))
    best = {}
    for r in rows:
        r["risk"] = round(float(r["score"]) * PRI_W.get(r["priority"], 2) * (1 + (r["fails"] / r["runs"] if r["runs"] else 0.2)), 2)
        if r["id"] not in best or r["risk"] > best[r["id"]]["risk"]:
            best[r["id"]] = r
    return sorted(best.values(), key=lambda r: -r["risk"])


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
def summary(x, release_id=None):
    rf = "AND cy.release_id=%s" if release_id else ""
    rp = (release_id,) if release_id else ()
    latest = x.q(f"""SELECT DISTINCT ON (r.case_id) r.*, c.key, c.title, c.feature, c.type, c.priority, c.story_key
                     FROM aw_result r JOIN aw_cycle cy ON cy.id=r.cycle_id JOIN aw_case c ON c.id=r.case_id
                     WHERE TRUE {rf} ORDER BY r.case_id, r.cycle_id DESC""", rp)
    allr = x.q(f"""SELECT r.case_id, r.status, r.self_healed, r.root_cause, r.resolution, c.key, c.title, c.priority, c.type
                   FROM aw_result r JOIN aw_cycle cy ON cy.id=r.cycle_id JOIN aw_case c ON c.id=r.case_id WHERE TRUE {rf}""", rp)
    planned = x.one(f"""SELECT COALESCE(SUM(cardinality(case_ids)),0) AS n FROM aw_plan p WHERE {'p.release_id=%s' if release_id else 'TRUE'}""", rp)["n"]
    stories = x.q("SELECT key, title, feature FROM aw_story")
    covered = {r["story_key"] for r in x.q("SELECT DISTINCT story_key FROM aw_case")}
    tested = {r["story_key"] for r in latest}
    feats = {}
    for r in latest:
        f = feats.setdefault(r["feature"], {"feature": r["feature"], "passed": 0, "failed": 0, "skipped": 0})
        f[r["status"]] += 1
    per = {}
    for r in allr:
        d = per.setdefault(r["case_id"], {"key": r["key"], "title": r["title"], "priority": r["priority"], "type": r["type"], "runs": 0, "fails": 0, "healed": 0,
                                         "root_cause": None, "resolution": None})
        d["runs"] += 1
        d["fails"] += r["status"] == "failed"
        d["healed"] += bool(r["self_healed"])
        if r["status"] == "failed":
            d["root_cause"], d["resolution"] = r["root_cause"], r["resolution"]
    hot = {"critical": [], "flaky": [], "stable": []}
    for d in per.values():
        d["failure_rate"] = round(100 * d["fails"] / d["runs"])
        if d["fails"] and (d["failure_rate"] >= 50 or d["priority"] == "High") and d["fails"] == d["runs"]:
            hot["critical"].append(d)
        elif d["fails"] or d["healed"]:
            hot["flaky"].append(d)
        else:
            hot["stable"].append(d)
    dq = "WHERE cy.release_id=%s" if release_id else ""
    defects = x.q(f"""SELECT d.*, c.key AS case_key, c.priority FROM aw_defect d LEFT JOIN aw_case c ON c.id=d.case_id
                      LEFT JOIN aw_cycle cy ON cy.id=d.cycle_id {dq} ORDER BY d.id""", rp)
    sev = {}
    for d in defects:
        sev[d["severity"]] = sev.get(d["severity"], 0) + 1
    by_suite = {}
    for d in defects:
        by_suite.setdefault(d["feature"] or "Other", {}).setdefault(d["severity"], 0)
        by_suite[d["feature"] or "Other"][d["severity"]] += 1
    # impact x likelihood grid
    grid = {f"{i}-{l}": [] for i in ("High", "Medium", "Low") for l in ("High", "Medium", "Low")}
    changed = {r["case_id"] for r in x.q("SELECT DISTINCT mp.case_id FROM aw_mapping mp JOIN aw_module m ON m.id=mp.module_id WHERE m.changed")}
    for cid, d in per.items():
        like = "High" if d["failure_rate"] >= 50 or (cid in changed and d["fails"]) else "Medium" if d["fails"] or d["healed"] or cid in changed else "Low"
        grid[f"{d['priority']}-{like}"].append({"key": d["key"], "title": d["title"]})
    counts = {s: sum(1 for r in latest if r["status"] == s) for s in ("passed", "failed", "skipped")}
    feat_ready = [f for f in feats.values() if not f["failed"]]
    return {"stories": len(stories), "covered": len(covered & {s["key"] for s in stories}), "tested": len(tested & {s["key"] for s in stories}),
            "planned": planned, "actual": len(latest), **counts, "features": sorted(feats.values(), key=lambda f: -f["failed"]),
            "features_ready": len(feat_ready), "features_total": len(feats),
            "hotspots": {k: sorted(v, key=lambda d: -d["failure_rate"]) for k, v in hot.items()},
            "defects": defects, "severity": sev, "by_suite": by_suite, "grid": grid,
            "most_failed": sorted([d for d in per.values() if d["fails"]], key=lambda d: (-d["failure_rate"], -d["fails"]))[:15],
            "self_healed": sum(d["healed"] for d in per.values())}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
PILLARS = [
    {"code": "design", "name": "Design", "tools": [
        ["Test Case Generator", "Generates test cases from user stories (Jira, Rally, Azure DevOps, PDF, XLSX, DOCX, S3) or product documents (FSD, BRD, UI/UX designs, API docs)."],
        ["Test Data Generator", "Generates synthetic test data from a schema file (SQL, CSV, XLSX) or a live database, aligned to valid, boundary, invalid and masked scenarios."],
        ["Test Script Generator", "Generates keyword-driven, BDD or data-driven scripts from test cases, over reusable components, applications, standard suites and services."]]},
    {"code": "execution", "name": "Execution", "tools": [
        ["Execution engines and devices", "Local or cluster engines with expiry, plus the browsers, tablets and CI runners tests run on."],
        ["Releases and test plans", "Plan which cases run in each release; run them manually, from CI/CD or on a schedule."],
        ["Self-healing and failure analysis", "Locator changes heal automatically; every failure is classified with a root cause and a resolution."],
        ["Test execution report", "Latest execution, result summary and every execution cycle by release and engine."]]},
    {"code": "analytics", "name": "Analytics", "tools": [
        ["Test report summarizer", "Feature-level status, user-story coverage, feature readiness and hotspots (critical, flaky, stable)."],
        ["Defect impact analysis", "Defects by status and severity, overall and by suite, with the full defect list."],
        ["Impact-based test suggestion", "Impact × likelihood grid that tells you which tests to run first."],
        ["Test case performance", "Most-failed tests with root cause and resolution."]]},
    {"code": "maintenance", "name": "Maintenance", "tools": [
        ["Test case – code mappings", "Maps every test case to the code modules it exercises, with code coverage and recommendations."],
        ["Impact analysis", "From the modules a change touches, finds the high-impact test cases and builds the regression plan."]]},
]


@router.get("/overview")
def overview(p: dict = Depends(screen("aw_overview"))):
    s = summary(DB)
    return {"pillars": PILLARS, "llm": llm.available(), "llm_status": llm.status(),
            "counts": {"stories": s["stories"], "covered": s["covered"], "cases": DB.one("SELECT COUNT(*) AS n FROM aw_case")["n"],
                       "suites": DB.one("SELECT COUNT(*) AS n FROM aw_suite")["n"], "datasets": DB.one("SELECT COUNT(*) AS n FROM aw_dataset")["n"],
                       "scripts": DB.one("SELECT COUNT(*) AS n FROM aw_script")["n"], "cycles": DB.one("SELECT COUNT(*) AS n FROM aw_cycle")["n"],
                       "passed": s["passed"], "failed": s["failed"], "skipped": s["skipped"], "self_healed": s["self_healed"],
                       "open_defects": sum(1 for d in s["defects"] if d["status"] != "Closed"),
                       "modules": DB.one("SELECT COUNT(*) AS n FROM aw_module")["n"], "changed": DB.one("SELECT COUNT(*) AS n FROM aw_module WHERE changed")["n"]}}


@router.get("/design")
def design(suite_id: int | None = None, p: dict = Depends(screen("aw_design"))):
    suites = DB.q("""SELECT s.*, (SELECT COUNT(*) FROM aw_case c WHERE c.suite_id=s.id) AS cases FROM aw_suite s ORDER BY s.id DESC""")
    sid = suite_id or (suites[0]["id"] if suites else None)
    return {"stories": DB.q("SELECT * FROM aw_story ORDER BY id"), "suites": suites, "suite_id": sid,
            "cases": DB.q("SELECT * FROM aw_case WHERE suite_id=%s ORDER BY id", (sid,)) if sid else [],
            "datasets": DB.q("SELECT id, name, schema_source, entity, scenarios, jsonb_array_length(rows) AS n, created_by, created_at FROM aw_dataset ORDER BY id DESC"),
            "scripts": DB.q("SELECT s.id, s.framework, s.app, s.file, c.key, c.title, s.created_at FROM aw_script s JOIN aw_case c ON c.id=s.case_id ORDER BY s.id DESC"),
            "framework": DB.q("SELECT * FROM aw_component ORDER BY id"),
            "entities": DB.q("SELECT id, model, name, kind FROM data_entity ORDER BY model, kind DESC, name"),
            "llm": llm.available(), "llm_status": llm.status()}


class GenIn(BaseModel):
    source: str = "stories"
    story_ids: list[int] | None = None
    doc_type: str | None = None
    doc_text: str | None = None
    name: str | None = None


@router.post("/design/cases/generate")
def gen_cases(body: GenIn, p: dict = Depends(screen("aw_design"))):
    s = generate_cases(DB, body.source, body.story_ids, body.doc_type, body.doc_text, body.name, p["code"])
    remap(DB)
    return s


class TextIn(BaseModel):
    text: str


@router.post("/design/cases/import")
def imp_cases(body: TextIn, p: dict = Depends(screen("aw_design"))):
    s = import_cases(DB, body.text, p["code"])
    remap(DB)
    return s


@router.delete("/design/suites/{sid}")
def del_suite(sid: int, p: dict = Depends(screen("aw_design"))):
    if DB.one("SELECT 1 AS ok FROM aw_result r JOIN aw_case c ON c.id=r.case_id WHERE c.suite_id=%s LIMIT 1", (sid,)):
        raise HTTPException(400, "This suite has execution results; keep it for the audit trail.")
    DB.one("DELETE FROM aw_suite WHERE id=%s RETURNING 1", (sid,))
    return {"ok": True}


class DataIn(BaseModel):
    entity_id: int | None = None
    ddl: str | None = None
    rows: int = 20
    scenarios: list[str] = ["valid", "boundary", "invalid"]


@router.post("/design/data/generate")
def gen_data(body: DataIn, p: dict = Depends(screen("aw_design"))):
    return generate_data(DB, body.entity_id, body.ddl, body.rows, body.scenarios, p["code"])


@router.get("/design/data/{did}")
def get_data(did: int, p: dict = Depends(screen("aw_design"))):
    return DB.one("SELECT * FROM aw_dataset WHERE id=%s", (did,))


class ScriptIn(BaseModel):
    case_id: int
    framework: str = "Keyword driven"


@router.post("/design/scripts/generate")
def gen_script(body: ScriptIn, p: dict = Depends(screen("aw_design"))):
    return generate_script(DB, body.case_id, body.framework, p["code"])


@router.get("/design/scripts/{sid}")
def get_script(sid: int, p: dict = Depends(screen("aw_design"))):
    return DB.one("SELECT s.*, c.key, c.title FROM aw_script s JOIN aw_case c ON c.id=s.case_id WHERE s.id=%s", (sid,))


@router.get("/execution")
def execution(p: dict = Depends(screen("aw_execution"))):
    cycles = DB.q("""SELECT cy.*, r.name AS release, p.name AS plan FROM aw_cycle cy LEFT JOIN aw_release r ON r.id=cy.release_id
                     LEFT JOIN aw_plan p ON p.id=cy.plan_id ORDER BY cy.id DESC""")
    return {"engines": DB.q("SELECT * FROM aw_engine ORDER BY id"), "devices": DB.q("SELECT * FROM aw_device ORDER BY id"),
            "releases": DB.q("SELECT * FROM aw_release ORDER BY start_date"),
            "plans": DB.q("""SELECT p.*, cardinality(p.case_ids) AS n, r.name AS release FROM aw_plan p LEFT JOIN aw_release r ON r.id=p.release_id ORDER BY p.id"""),
            "cicd": DB.q("SELECT c.*, r.name AS release FROM aw_cicd c LEFT JOIN aw_release r ON r.id=c.release_id ORDER BY c.id"),
            "cycles": cycles, "cases": DB.q("SELECT id, key, title, type, priority, feature FROM aw_case ORDER BY suite_id DESC, id"),
            "latest": cycle(cycles[0]["id"], p) if cycles else None}


@router.get("/execution/cycles/{cid}")
def cycle(cid: int, p: dict = Depends(screen("aw_execution"))):
    c = DB.one("SELECT cy.*, r.name AS release FROM aw_cycle cy LEFT JOIN aw_release r ON r.id=cy.release_id WHERE cy.id=%s", (cid,))
    if not c:
        raise HTTPException(404)
    c["results"] = DB.q("""SELECT r.*, c.key, c.title, c.type FROM aw_result r JOIN aw_case c ON c.id=r.case_id WHERE r.cycle_id=%s
                           ORDER BY CASE r.status WHEN 'failed' THEN 0 WHEN 'skipped' THEN 1 ELSE 2 END, r.self_healed DESC, c.key""", (cid,))
    return c


TABLES = {"engines": ("aw_engine", ["name", "type", "status", "expires"]), "devices": ("aw_device", ["name", "type", "platform", "environment"]),
          "releases": ("aw_release", ["name", "description", "start_date", "release_date"]),
          "plans": ("aw_plan", ["name", "release_id", "case_ids", "suite"]),
          "cicd": ("aw_cicd", ["name", "pipeline", "release_id", "failure_analysis", "self_healing", "config", "schedule"])}


@router.post("/execution/{kind}")
def add_item(kind: str, body: dict, p: dict = Depends(screen("aw_execution"))):
    if kind not in TABLES:
        raise HTTPException(404)
    t, cols = TABLES[kind]
    data = {k: (v if v != "" else None) for k, v in body.items() if k in cols}
    if not data.get("name"):
        raise HTTPException(400, "Give it a name.")
    if kind == "engines":
        data.setdefault("status", "Ready")
    try:
        return DB.one(f"INSERT INTO {t}({','.join(data)}) VALUES ({','.join(['%s'] * len(data))}) RETURNING *", tuple(data.values()))
    except Exception as e:
        raise HTTPException(400, str(e).splitlines()[0])


@router.delete("/execution/{kind}/{iid}")
def del_item(kind: str, iid: int, p: dict = Depends(screen("aw_execution"))):
    if kind not in TABLES:
        raise HTTPException(404)
    try:
        DB.one(f"DELETE FROM {TABLES[kind][0]} WHERE id=%s RETURNING 1", (iid,))
    except Exception:
        raise HTTPException(400, "It is used by executions; keep it for the audit trail.")
    return {"ok": True}


class RunIn(BaseModel):
    engine: str = "Snowflake DEV cluster"
    device: str = "Chrome desktop"
    self_healing: bool = True
    failure_analysis: bool = True


@router.post("/execution/plans/{pid}/run")
def run(pid: int, body: RunIn, p: dict = Depends(screen("aw_execution"))):
    e = DB.one("SELECT * FROM aw_engine WHERE name=%s", (body.engine,))
    if e and e["expires"] and e["expires"] < date.today():
        raise HTTPException(400, f"Engine '{body.engine}' expired on {e['expires']}. Reclaim or extend it first.")
    cid = run_plan(DB, pid, body.engine, body.device, body.self_healing, body.failure_analysis, p["code"])
    return cycle(cid, p)


@router.get("/analytics")
def analytics(release_id: int | None = None, p: dict = Depends(screen("aw_analytics"))):
    return {**summary(DB, release_id), "releases": DB.q("SELECT id, name FROM aw_release ORDER BY start_date"), "release_id": release_id}


class DefIn(BaseModel):
    status: str


@router.put("/analytics/defects/{did}")
def put_defect(did: int, body: DefIn, p: dict = Depends(screen("aw_execution"))):
    if body.status not in ("Open", "In progress", "Closed"):
        raise HTTPException(400, "Status is Open, In progress or Closed.")
    return DB.one("UPDATE aw_defect SET status=%s WHERE id=%s RETURNING *", (body.status, did))


@router.get("/maintenance")
def maintenance(p: dict = Depends(screen("aw_maintenance"))):
    mods = DB.q("""SELECT m.*, COUNT(mp.case_id) AS cases, ROUND(AVG(mp.score)::numeric, 2) AS avg_score
                   FROM aw_module m LEFT JOIN aw_mapping mp ON mp.module_id=m.id GROUP BY m.id ORDER BY m.id""")
    maps = DB.q("""SELECT c.key, c.title, c.type, c.priority, m.path, m.module, mp.score FROM aw_mapping mp JOIN aw_case c ON c.id=mp.case_id
                   JOIN aw_module m ON m.id=mp.module_id ORDER BY c.key, mp.score DESC""")
    total_cases = DB.one("SELECT COUNT(*) AS n FROM aw_case")["n"]
    mapped = DB.one("SELECT COUNT(DISTINCT case_id) AS n FROM aw_mapping")["n"]
    recs = []
    for m in mods:
        if m["cases"] < 2:
            kw = ", ".join(m["keywords"].split()[:4])
            recs.append({"module": m["module"], "path": m["path"], "cases": m["cases"],
                         "suggest": f"Add {'reconciliation' if m['kind'] in ('dbt model', 'stored procedure') else 'security' if m['kind'] == 'policy' else 'functional and performance'} cases for {m['module']} ({kw})"})
    changed = [m["id"] for m in mods if m["changed"]]
    return {"modules": mods, "mappings": maps, "recommendations": recs, "total_cases": total_cases, "mapped_cases": mapped,
            "impacted": impact(DB, changed) if changed else [], "releases": DB.q("SELECT id, name FROM aw_release ORDER BY start_date")}


@router.post("/maintenance/remap")
def do_remap(p: dict = Depends(screen("aw_maintenance"))):
    return {"mappings": remap(DB)}


class ModIn(BaseModel):
    changed: bool


@router.put("/maintenance/modules/{mid}")
def put_module(mid: int, body: ModIn, p: dict = Depends(screen("aw_maintenance"))):
    DB.one("UPDATE aw_module SET changed=%s WHERE id=%s RETURNING 1", (body.changed, mid))
    return maintenance(p)


class DiffIn(BaseModel):
    paths: str


@router.post("/maintenance/diff")
def diff(body: DiffIn, p: dict = Depends(screen("aw_maintenance"))):
    """Mark modules changed from a pasted list of changed file paths (e.g. `git diff --name-only`)."""
    paths = [l.strip() for l in body.paths.splitlines() if l.strip()]
    DB.one("UPDATE aw_module SET changed = path = ANY(%s) WHERE TRUE RETURNING 1", (paths,))
    return maintenance(p)


class ImpactPlanIn(BaseModel):
    release_id: int | None = None
    top: int = 25


@router.post("/maintenance/plan")
def impact_plan(body: ImpactPlanIn, p: dict = Depends(screen("aw_maintenance"))):
    changed = [m["id"] for m in DB.q("SELECT id FROM aw_module WHERE changed")]
    rows = impact(DB, changed)[: body.top]
    if not rows:
        raise HTTPException(400, "Mark the changed modules first.")
    return DB.one("INSERT INTO aw_plan(name,release_id,case_ids,suite) VALUES (%s,%s,%s,'Impact regression') RETURNING *",
                  (f"Impact regression · {date.today()}", body.release_id, [r["id"] for r in rows]))


# ---------------------------------------------------------------------------
# Assurance skills (engines for the skills studio)
# ---------------------------------------------------------------------------
FEATURES = ["", "BI modernization", "Customer portal", "Platform migration", "Security", "Data products", "Cortex AI"]
AW_SKILLS = {
    "aw-test-case-generator": {"title": "Test case generator", "screens": ["aw_design"],
        "engine": "Turns user stories (by feature) or pasted requirements, screens or API endpoints into a versioned suite of functional, negative, data, security, performance, UI and API test cases.",
        "fields": [{"key": "feature", "label": "Stories for feature (blank = all)", "kind": "choice", "default": "", "options": FEATURES},
                   {"key": "doc_type", "label": "Or generate from a document", "kind": "choice", "default": "", "options": ["", "FSD/BRD", "UI/UX", "API DOCS"]},
                   {"key": "doc_text", "label": "Document content (one requirement, screen or endpoint per line)", "kind": "lines", "default": ""}]},
    "aw-test-data-generator": {"title": "Test data generator", "screens": ["aw_design"],
        "engine": "Generates synthetic rows for valid, boundary, invalid and masked scenarios from pasted DDL or a CSV header, with Snowflake INSERT SQL and data-quality checks.",
        "fields": [{"key": "ddl", "label": "CREATE TABLE DDL or CSV header", "kind": "textarea",
                    "default": "CREATE TABLE fct_shipment (shipment_id NUMBER, customer_key NUMBER, ship_date DATE, delivered_date DATE, carrier_rate NUMBER(12,2), on_time_flag BOOLEAN, units NUMBER)"},
                   {"key": "rows", "label": "Rows", "kind": "text", "default": "24"}]},
    "aw-test-script-generator": {"title": "Test script generator", "screens": ["aw_design"],
        "engine": "Generates a keyword-driven pytest (or BDD feature) for a test case over the reusable components: login, navigation, filters, KPI tiles, SQL, legacy comparison, row access and masking.",
        "fields": [{"key": "case_key", "label": "Test case key (blank = first high-priority case)", "kind": "text", "default": ""},
                   {"key": "framework", "label": "Framework", "kind": "choice", "default": "Keyword driven", "options": ["Keyword driven", "BDD"]}]},
    "aw-test-report-summarizer": {"title": "Test report summarizer", "screens": ["aw_analytics"],
        "engine": "Summarizes coverage, results, feature readiness, hotspots, defects by severity and the impact × likelihood grid for a release.",
        "fields": [{"key": "release", "label": "Release (blank = all)", "kind": "text", "default": ""}]},
    "aw-impact-analyzer": {"title": "Impact analyzer", "screens": ["aw_maintenance"],
        "engine": "From a list of changed files, finds the impacted test cases through the test-to-code mappings and ranks the regression suite by risk.",
        "fields": [{"key": "paths", "label": "Changed files (git diff --name-only)", "kind": "lines", "default": "procs/sp_load_wms_incremental.sql\npolicies/rap_customer.sql"}]},
}


def _md_table(cols, rows):
    return ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


def sk_cases(params, p, session):
    if params.get("doc_type") and params.get("doc_text", "").strip():
        s = generate_cases(DB, "document", doc_type=params["doc_type"], doc_text=params["doc_text"], who=p["code"])
    else:
        s = generate_cases(DB, "stories", feature=params.get("feature") or None, who=p["code"])
    remap(DB)
    cases = DB.q("SELECT * FROM aw_case WHERE suite_id=%s ORDER BY id", (s["id"],))
    by = {}
    for c in cases:
        by[c["type"]] = by.get(c["type"], 0) + 1
    md = [f"# {s['name']}", "", f"Source: {s['source_ref']} · {len(cases)} cases · " + ", ".join(f"{k} {v}" for k, v in by.items()), ""]
    md += _md_table(["Key", "Story", "Type", "Priority", "Title", "Expected"], [[c["key"], c["story_key"], c["type"], c["priority"], c["title"], c["expected"]] for c in cases])
    out = io.StringIO(); w = csv.writer(out); w.writerow(["key", "story", "feature", "type", "priority", "title", "steps", "expected"])
    for c in cases:
        w.writerow([c["key"], c["story_key"], c["feature"], c["type"], c["priority"], c["title"], "; ".join(c["steps"]), c["expected"]])
    return {"summary": f"{s['name']}: {len(cases)} test cases from {s['source_ref']}", "files": {"test_cases.md": "\n".join(md), "test_cases.csv": out.getvalue()}, "notes": []}


def sk_data(params, p, session):
    d = generate_data(DB, ddl=params.get("ddl"), rows=int(params.get("rows") or 24), scenarios=["valid", "boundary", "invalid", "masked"], who=p["code"])
    full = DB.one("SELECT * FROM aw_dataset WHERE id=%s", (d["id"],))
    rows = full["rows"]
    cols = [k for k in rows[0].keys()]
    out = io.StringIO(); w = csv.DictWriter(out, fieldnames=cols); w.writeheader(); w.writerows(rows)
    return {"summary": f"{d['name']}: {len(rows)} rows", "files": {"test_data.csv": out.getvalue(), "load_test_data.sql": full["sql"]}, "notes": []}


def sk_script(params, p, session):
    key = (params.get("case_key") or "").strip()
    cs = DB.one("SELECT id FROM aw_case WHERE key=%s", (key,)) if key else DB.one("SELECT id FROM aw_case WHERE priority='High' ORDER BY suite_id DESC, id LIMIT 1")
    if not cs:
        raise HTTPException(404, f"Test case '{key}' not found.")
    s = generate_script(DB, cs["id"], params.get("framework") or "Keyword driven", p["code"])
    kw = ["# keywords.py · reusable components (implement once per application)", "import time", "",
          *[f"def {k['keyword'].lower()}(ctx, arg):\n    \"\"\"{k['keyword']}: {k['args']}\"\"\"\n    ctx.log('{k['keyword']}', arg)\n" for k in s["keywords"]]]
    return {"summary": f"{s['file']} · {len(s['keywords'])} keyword steps · {s['framework']}",
            "files": {s["file"]: s["code"], "keywords.py": "\n".join(kw)}, "notes": []}


def sk_summary(params, p, session):
    rel = (params.get("release") or "").strip()
    r = DB.one("SELECT id, name FROM aw_release WHERE name ILIKE %s", (f"%{rel}%",)) if rel else None
    s = summary(DB, r["id"] if r else None)
    cov = round(100 * s["covered"] / s["stories"]) if s["stories"] else 0
    md = [f"# Test report · {r['name'] if r else 'all releases'}", "",
          f"- User stories: {s['stories']} · covered by test cases {s['covered']} ({cov}%) · tested {s['tested']}",
          f"- Results: planned {s['planned']} · executed {s['actual']} · passed {s['passed']} · failed {s['failed']} · skipped {s['skipped']} · self-healed {s['self_healed']}",
          f"- Feature readiness: {s['features_ready']} of {s['features_total']} features with no failures",
          f"- Hotspots: critical {len(s['hotspots']['critical'])} · flaky {len(s['hotspots']['flaky'])} · stable {len(s['hotspots']['stable'])}",
          f"- Defects: {len(s['defects'])} ({', '.join(f'{k} {v}' for k, v in s['severity'].items())}); open {sum(1 for d in s['defects'] if d['status'] != 'Closed')}", "",
          "## Features", ""] + _md_table(["Feature", "Passed", "Failed", "Skipped"], [[f["feature"], f["passed"], f["failed"], f["skipped"]] for f in s["features"]])
    md += ["", "## Most failed", ""] + _md_table(["Test case", "Failure rate", "Root cause", "Resolution"], [[f"{d['key']} {d['title'][:60]}", f"{d['failure_rate']}%", d["root_cause"], d["resolution"]] for d in s["most_failed"][:10]])
    md += ["", "## Run first (high impact, high likelihood)", ""] + [f"- {x['key']} {x['title']}" for x in s["grid"]["High-High"][:10]]
    return {"summary": f"{s['passed']} passed · {s['failed']} failed · {len(s['defects'])} defects · coverage {cov}%", "files": {"test_report.md": "\n".join(md)}, "notes": []}


def sk_impact(params, p, session):
    paths = [l.strip() for l in (params.get("paths") or "").splitlines() if l.strip()]
    mods = DB.q("SELECT id, path, module FROM aw_module WHERE path = ANY(%s)", (paths,))
    unknown = sorted(set(paths) - {m["path"] for m in mods})
    rows = impact(DB, [m["id"] for m in mods])
    md = ["# Impact analysis", "", "Changed modules: " + (", ".join(f"`{m['path']}`" for m in mods) or "none recognised"), ""]
    if unknown:
        md += ["Not mapped yet (add them in maintenance): " + ", ".join(f"`{u}`" for u in unknown), ""]
    md += _md_table(["Risk", "Test case", "Type", "Priority", "Via module", "Mapping score", "Failures / runs"],
                    [[r["risk"], f"{r['key']} {r['title'][:60]}", r["type"], r["priority"], r["module"], r["score"], f"{r['fails']}/{r['runs']}"] for r in rows])
    return {"summary": f"{len(rows)} impacted test cases from {len(mods)} changed module(s)", "files": {"impact_analysis.md": "\n".join(md)},
            "notes": [f"Unmapped paths: {', '.join(unknown)}"] if unknown else []}


AW_ENGINES = {"aw-test-case-generator": sk_cases, "aw-test-data-generator": sk_data, "aw-test-script-generator": sk_script,
              "aw-test-report-summarizer": sk_summary, "aw-impact-analyzer": sk_impact}
