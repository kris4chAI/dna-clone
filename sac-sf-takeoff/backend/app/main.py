import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import chat
from .db import one, pool, q


@asynccontextmanager
async def lifespan(_):
    pool.open()
    yield
    pool.close()


app = FastAPI(title="Keystone Navigator API", version="1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health():
    return {"ok": one("SELECT 1 AS ok")["ok"] == 1}


@app.get("/api/overview")
def overview():
    return one("""SELECT (SELECT count(*) FROM stage) stages,
        (SELECT count(*) FROM component WHERE kind='agent') agents,
        (SELECT count(*) FROM component WHERE kind='skill') skills,
        (SELECT count(*) FROM component WHERE kind='tool') tools,
        (SELECT count(*) FROM component WHERE kind='framework') frameworks,
        (SELECT count(*) FROM component WHERE kind='snowflake') snowflake,
        (SELECT count(*) FROM persona) personas, (SELECT count(*) FROM insight_dashboard) dashboards,
        (SELECT count(*) FROM subject_area) subject_areas, (SELECT count(*) FROM data_entity) entities,
        (SELECT count(*) FROM kpi) kpis""")


# ---------------- Workflow ----------------
@app.get("/api/phases")
def phases():
    return q("SELECT * FROM phase ORDER BY num")


@app.get("/api/stages")
def stages():
    return q("""SELECT s.*, (SELECT count(DISTINCT component_id) FROM stage_component sc JOIN component c ON c.id=sc.component_id
                              WHERE sc.stage_id=s.id AND c.kind='agent') AS agent_count,
                           (SELECT count(DISTINCT component_id) FROM stage_component sc JOIN component c ON c.id=sc.component_id
                              WHERE sc.stage_id=s.id AND c.kind='skill') AS skill_count
                FROM stage s ORDER BY seq""")


@app.get("/api/stages/{code}")
def stage(code: str):
    s = one("SELECT * FROM stage WHERE code=%s", (code,))
    if not s:
        raise HTTPException(404)
    rows = q("""SELECT sc.parent_id, c.* FROM stage_component sc JOIN component c ON c.id=sc.component_id
                WHERE sc.stage_id=%s ORDER BY sc.seq""", (s["id"],))
    agents = {r["id"]: {**r, "skills": [], "tools": []} for r in rows if r["kind"] == "agent"}
    for r in rows:
        if r["parent_id"] in agents:
            agents[r["parent_id"]][r["kind"] + "s"].append({"id": r["id"], "name": r["name"], "category": r["category"]})
    uniq = lambda k: list({r["name"]: r for r in rows if r["kind"] == k}.values())
    s["agents"] = list(agents.values())
    s["frameworks"] = uniq("framework")
    s["snowflake"] = uniq("snowflake")
    s["skills"] = uniq("skill")
    s["tools"] = uniq("tool")
    return s


@app.get("/api/components")
def components(kind: str | None = None):
    rows = q("""SELECT c.*, COALESCE(json_agg(DISTINCT jsonb_build_object('code', s.code, 'name', s.name, 'seq', s.seq))
                       FILTER (WHERE s.id IS NOT NULL), '[]') AS stages,
                       COALESCE(json_agg(DISTINCT p.name) FILTER (WHERE p.name IS NOT NULL), '[]') AS used_by
                FROM component c LEFT JOIN stage_component sc ON sc.component_id=c.id
                LEFT JOIN stage s ON s.id=sc.stage_id LEFT JOIN component p ON p.id=sc.parent_id
                WHERE (%s::text IS NULL OR c.kind=%s) GROUP BY c.id ORDER BY c.kind, c.name""", (kind, kind))
    return rows


# ---------------- Guided progress ----------------
class Progress(BaseModel):
    session_id: str
    stage_code: str
    step_index: int
    done: bool


@app.get("/api/progress/{session_id}")
def get_progress(session_id: str):
    return q("SELECT stage_code, step_index FROM guide_progress WHERE session_id=%s AND done", (session_id,))


@app.post("/api/progress")
def set_progress(p: Progress):
    one("""INSERT INTO guide_progress(session_id,stage_code,step_index,done) VALUES (%s,%s,%s,%s)
           ON CONFLICT (session_id,stage_code,step_index) DO UPDATE SET done=EXCLUDED.done, updated_at=now() RETURNING 1""",
        (p.session_id, p.stage_code, p.step_index, p.done))
    return get_progress(p.session_id)


# ---------------- Curated content ----------------
@app.get("/api/personas")
def personas():
    ps = q("SELECT * FROM persona ORDER BY id")
    steps = q("SELECT * FROM journey_step ORDER BY persona_id, seq, id")
    for p in ps:
        p["steps"] = [s for s in steps if s["persona_id"] == p["id"]]
    return ps


@app.get("/api/insights")
def insights():
    ds = q("SELECT * FROM insight_dashboard ORDER BY id")
    qs = q("SELECT * FROM insight_question ORDER BY dashboard_id, seq, id")
    for d in ds:
        d["questions"] = [x for x in qs if x["dashboard_id"] == d["id"]]
    return ds


@app.get("/api/datamodel")
def datamodel():
    domains = q("SELECT * FROM domain ORDER BY id")
    areas = q("SELECT * FROM subject_area ORDER BY num, id")
    for d in domains:
        d["areas"] = [a for a in areas if a["domain_id"] == d["id"]]
    ents = q("SELECT e.*, sa.name AS subject_area FROM data_entity e LEFT JOIN subject_area sa ON sa.id=e.subject_area_id ORDER BY e.model, e.kind DESC, e.id")
    attrs = q("SELECT * FROM attribute ORDER BY entity_id, id")
    for e in ents:
        e["attributes"] = [a for a in attrs if a["entity_id"] == e["id"]]
    return {"domains": domains, "layers": q("SELECT * FROM data_layer ORDER BY seq"),
            "conformed": q("SELECT * FROM conformed_dim ORDER BY id"), "entities": ents,
            "kpis": q("SELECT * FROM kpi ORDER BY id")}


# Generic CRUD for curation. Whitelisted tables and columns only.
CURATABLE = {
    "persona": ["code", "segment", "name", "roles", "wants", "journey", "goals", "pains", "kpis", "note", "slide"],
    "journey_step": ["persona_id", "seq", "name", "question", "experience", "metrics", "doing", "today"],
    "insight_dashboard": ["code", "name", "audience", "roles", "surface", "headline", "guardrail", "persona_code", "slide"],
    "insight_question": ["dashboard_id", "seq", "kind", "question", "answer"],
    "domain": ["name", "source"],
    "subject_area": ["domain_id", "num", "name", "entities"],
    "data_entity": ["model", "name", "kind", "type", "description", "subject_area_id"],
    "attribute": ["entity_id", "name", "role", "description"],
    "kpi": ["domain", "name", "formula", "audiences", "source_fact", "owner", "grain", "certified"],
    "conformed_dim": ["name"],
    "component": ["kind", "name", "category", "description"],
}


def _check(table):
    if table not in CURATABLE:
        raise HTTPException(404, "Not curatable")
    return CURATABLE[table]


@app.post("/api/curate/{table}")
def create(table: str, data: dict[str, Any] = Body(...)):
    cols = [c for c in _check(table) if c in data]
    if not cols:
        raise HTTPException(400, "No fields")
    sql = f"INSERT INTO {table}({','.join(cols)}, origin) VALUES ({','.join(['%s'] * len(cols))}, 'curated') RETURNING *"
    return one(sql, [data[c] for c in cols])


@app.put("/api/curate/{table}/{row_id}")
def update(table: str, row_id: int, data: dict[str, Any] = Body(...)):
    cols = [c for c in _check(table) if c in data]
    if not cols:
        raise HTTPException(400, "No fields")
    sets = ",".join(f"{c}=%s" for c in cols)
    row = one(f"UPDATE {table} SET {sets}, origin='curated' WHERE id=%s RETURNING *", [data[c] for c in cols] + [row_id])
    if not row:
        raise HTTPException(404)
    return row


@app.delete("/api/curate/{table}/{row_id}")
def delete(table: str, row_id: int):
    _check(table)
    row = one(f"DELETE FROM {table} WHERE id=%s RETURNING id", (row_id,))
    if not row:
        raise HTTPException(404)
    return {"deleted": row_id}


# ---------------- Conversational guide ----------------
class ChatIn(BaseModel):
    message: str
    session_id: str = "anon"
    context: dict[str, Any] | None = None


@app.post("/api/chat")
def post_chat(body: ChatIn):
    return chat.handle(body.message, body.session_id, body.context)


@app.get("/api/chat/{session_id}")
def chat_history(session_id: str):
    return q("SELECT role, content, payload, created_at FROM chat_message WHERE session_id=%s ORDER BY id", (session_id,))


# ---------------- Serve the built React app (single-container mode) ----------------
DIST = Path(os.getenv("FRONTEND_DIST", Path(__file__).resolve().parents[2] / "frontend" / "dist"))
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = DIST / path
        return FileResponse(f if path and f.is_file() else DIST / "index.html")
