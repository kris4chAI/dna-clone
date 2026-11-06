"""Create schema and load the proposal content. Usage: python -m app.seed [--if-empty]"""
import json
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from . import seed_data as S
from .db import DATABASE_URL
from .pmo_api import seed_pmo
from .seed_pursuit import seed_pursuit


def seed(c):
    c.execute((Path(__file__).parent / "schema.sql").read_text())

    for p in S.PHASES:
        c.execute("INSERT INTO phase VALUES (%s,%s,%s,%s)", (p["num"], p["name"], p["months"], p["output"]))

    comp_ids = {}

    def comp(kind, name, category=None, description=None):
        key = (kind, name)
        if key not in comp_ids:
            row = c.execute(
                """INSERT INTO component(kind,name,category,description) VALUES (%s,%s,%s,%s)
                   ON CONFLICT (kind,name) DO UPDATE SET description=COALESCE(component.description, EXCLUDED.description)
                   RETURNING id""",
                (kind, name, category, description)).fetchone()
            comp_ids[key] = row["id"]
        return comp_ids[key]

    for name, desc in S.FRAMEWORKS:
        comp("framework", name, "Niche Consulting accelerator", desc)

    for st in S.STAGES:
        extra = {k: st[k] for k in ("steps", "metrics", "evidence", "harnesses", "test_types", "references", "prompts") if k in st}
        sid = c.execute(
            """INSERT INTO stage(code,seq,name,phase,slide,lead_role,mode,gate,summary,key_steps,outputs,extra)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (st["code"], st["seq"], st["name"], st["phase"], st["slide"], st["lead_role"], st["mode"], st["gate"],
             st["summary"], json.dumps(st["key_steps"]), json.dumps(st["outputs"]), json.dumps(extra))).fetchone()["id"]
        seq = 0
        link = "INSERT INTO stage_component(stage_id,component_id,parent_id,seq) VALUES (%s,%s,%s,%s)"
        for a in st["agents"]:
            aid = comp("agent", a["name"], a["capability"], a["description"])
            c.execute(link, (sid, aid, None, seq)); seq += 1
            for sk in a["skills"]:
                c.execute(link, (sid, comp("skill", sk, "Skill"), aid, seq)); seq += 1
            for t in a["tools"]:
                c.execute(link, (sid, comp("tool", t, S.TOOL_CATEGORY.get(t, "Other")), aid, seq)); seq += 1
        for f in st["frameworks"]:
            c.execute(link, (sid, comp("framework", f), None, seq)); seq += 1
        for sf in st["snowflake"]:
            c.execute(link, (sid, comp("snowflake", sf, "Snowflake component"), None, seq)); seq += 1
        for step in st.get("steps", []):
            for sf in step.get("snowflake", []):
                c.execute(link, (sid, comp("snowflake", sf, "Snowflake component"), None, seq)); seq += 1

    # interchangeable AI tool options not already linked
    for t in ["Cursor", "Cortex Agents", "OPA / Checkov", "dbt / schemachange", "PR templates", "Zero-copy clones"]:
        comp("tool", t, S.TOOL_CATEGORY.get(t, "Other"))

    for p in S.PERSONAS:
        pid = c.execute(
            """INSERT INTO persona(code,segment,name,roles,wants,journey,goals,pains,kpis,note,slide)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (p["code"], p["segment"], p["name"], p["roles"], p["wants"], p["journey"], p.get("goals"),
             p.get("pains"), p.get("kpis"), p.get("note"), p["slide"])).fetchone()["id"]
        for i, s in enumerate(p["steps"], 1):
            s = list(s) + [None] * (6 - len(s))
            c.execute("""INSERT INTO journey_step(persona_id,seq,name,question,experience,metrics,doing,today)
                         VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""", (pid, i, *s))

    for d in S.DASHBOARDS:
        did = c.execute(
            """INSERT INTO insight_dashboard(code,name,audience,roles,surface,headline,guardrail,persona_code,slide)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (d["code"], d["name"], d["audience"], d["roles"], d["surface"], d["headline"], d.get("guardrail"),
             d["persona"], d["slide"])).fetchone()["id"]
        for i, (qn, ans) in enumerate(d["qa"]):
            c.execute("INSERT INTO insight_question(dashboard_id,seq,kind,question,answer) VALUES (%s,%s,%s,%s,%s)",
                      (did, i + 1, S.INSIGHT_KINDS[i], qn, ans))

    sa_ids, n = {}, 0
    for dname, src, areas in S.DOMAINS:
        did = c.execute("INSERT INTO domain(name,source) VALUES (%s,%s) RETURNING id", (dname, src)).fetchone()["id"]
        for aname, ents in areas:
            n += 1
            sa_ids[aname] = c.execute("INSERT INTO subject_area(domain_id,num,name,entities) VALUES (%s,%s,%s,%s) RETURNING id",
                                      (did, n, aname, ents)).fetchone()["id"]
    for i, (name, desc) in enumerate(S.LAYERS):
        c.execute("INSERT INTO data_layer VALUES (%s,%s,%s)", (name, i, desc))
    for d in S.CONFORMED_DIMS:
        c.execute("INSERT INTO conformed_dim(name) VALUES (%s)", (d,))

    for model, name, kind, typ, desc, sa, attrs in S.ENTITIES:
        eid = c.execute("""INSERT INTO data_entity(model,name,kind,type,description,subject_area_id)
                           VALUES (%s,%s,%s,%s,%s,%s) RETURNING id""",
                        (model, name, kind, typ, desc, sa_ids.get(sa))).fetchone()["id"]
        all_attrs = list(attrs) + (S.dim_attributes(desc) if kind == "dim" else [])
        if kind == "fact" and not attrs:
            all_attrs = [("grain / measures — curate in discovery", "placeholder", desc)]
        for an, role, ad in all_attrs:
            c.execute("INSERT INTO attribute(entity_id,name,role,description) VALUES (%s,%s,%s,%s)", (eid, an, role, ad))

    for dom, name, formula, aud, fact in S.KPIS:
        c.execute("INSERT INTO kpi(domain,name,formula,audiences,source_fact) VALUES (%s,%s,%s,%s,%s)",
                  (dom, name, formula, aud, fact))

    seed_pursuit(c)
    seed_pmo(c)


SCHEMA_VERSION = "4.0"


def main():
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as c:
        if "--if-empty" in sys.argv:
            exists = c.execute("SELECT to_regclass('public.app_meta') AS t").fetchone()["t"]
            ver = c.execute("SELECT value FROM app_meta WHERE key='schema_version'").fetchone() if exists else None
            if ver and ver["value"] == SCHEMA_VERSION:
                print(f"Database already seeded (schema {SCHEMA_VERSION}); skipping. Set RESET_DB=true to reload.")
                return
            print("Empty database or older schema: loading FlyHigh content.")
        seed(c)
        c.execute("CREATE TABLE IF NOT EXISTS app_meta (key TEXT PRIMARY KEY, value TEXT)")
        c.execute("INSERT INTO app_meta VALUES ('schema_version', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (SCHEMA_VERSION,))
        c.commit()
        counts = c.execute("""SELECT (SELECT count(*) FROM stage) stages,
            (SELECT count(*) FROM component WHERE kind='agent') agents,
            (SELECT count(*) FROM component WHERE kind='skill') skills,
            (SELECT count(*) FROM component WHERE kind='tool') tools,
            (SELECT count(*) FROM component WHERE kind='framework') frameworks,
            (SELECT count(*) FROM component WHERE kind='snowflake') snowflake,
            (SELECT count(*) FROM persona) personas, (SELECT count(*) FROM journey_step) steps,
            (SELECT count(*) FROM insight_dashboard) dashboards, (SELECT count(*) FROM subject_area) subject_areas,
            (SELECT count(*) FROM data_entity) entities, (SELECT count(*) FROM attribute) attributes,
            (SELECT count(*) FROM kpi) kpis, (SELECT count(*) FROM pursuit_stage) pursuit_stages,
            (SELECT count(*) FROM kit_template) templates, (SELECT count(*) FROM kit_sheet) sheets, (SELECT count(*) FROM kit_row) kit_rows,
            (SELECT count(*) FROM response_section) sections, (SELECT count(*) FROM lens_role) roles,
            (SELECT count(*) FROM pmo_kpi) pmo_kpis, (SELECT count(*) FROM pmo_usecase) pmo_usecases, (SELECT count(*) FROM pmo_raid) raid""").fetchone()
        print("Seeded:", counts)


if __name__ == "__main__":
    main()
