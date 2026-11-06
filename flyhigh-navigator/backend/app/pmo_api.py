"""PMO lens: the Snowflake AI Native Delivery Playbook as a working program office.

Content is seeded from assets/seed/delivery_playbook.json (primer, archetypes, readiness model,
plan / setup / execute / optimize, estimator, measurement, Responsible AI, team and RACI).
Working data (readiness answers, stage checklists, KPI actuals, use-case ratings, RAID, estimate
scenarios) lives in the pmo_* tables. Four PMO skills run as engines over that data.
"""
import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .access import screen
from .db import one, q
from .paths import SEED

router = APIRouter(prefix="/api/pmo")
TRACKS = ["Track A · Migration + BI", "Track B · Data products"]


def doc(key):
    r = one("SELECT data FROM pb_doc WHERE key=%s", (key,))
    return r["data"] if r else None


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------
SEED_READINESS = {  # FlyHigh example: conditional qualification (KPIs and platform lag)
    TRACKS[0]: [3, 3, 2, 2, 3, 2, 2, 3, 1, 1, 2, 1, 2, 1, 2, 1, 2],
    TRACKS[1]: [2, 2, 2, 3, 2, 2, 3, 2, 1, 2, 2, 1, 2, 2, 2, 1, 1],
}
SEED_KPI = {  # name -> (actual, status, note): pilot-month snapshot
    "Story acceptance": ("92%", "green", "Sprint 6 show-and-tell"),
    "Conversion rate": ("71%", "amber", "Pilot: PL/SQL residue higher than assessed"),
    "Plan confidence": ("On track", "green", "Burndown to Jul 2027 cut-over"),
    "Reconciliation parity": ("97%", "amber", "3 variances awaiting sign-off"),
    "First-pass acceptance": ("78%", "amber", "dbt models from ODI mappings need review"),
    "AI contribution rate": ("44%", "green", "Skill runs + work items"),
    "Report performance": ("4.1 s", "green", "Pilot dashboards at production volume"),
    "Credits per workload": ("Within budget", "green", ""),
    "Data freshness": ("98.6%", "amber", "Boomi WMS feed late twice"),
    "Guardrail adherence": ("100%", "green", "No blocked prod writes in hook logs"),
    "Certified KPI coverage": ("18 of 32", "amber", "Certification sprint running"),
}
SEED_RAID = [
    ("Risk", "Code conversion rate below plan", "Profile ODI in discovery, prove in the pilot; reset wave unit effort from evidence.", "Solution architect", "Pilot exit", "High", "Open"),
    ("Risk", "Late gate sign-offs", "5-business-day review SLA with named approvers for G1, G2, G3 and variances.", "Program manager", "Ongoing", "Medium", "Mitigating"),
    ("Risk", "SME availability", "8 hours a week from key SMEs, booked a sprint ahead.", "Client program head", "Ongoing", "Medium", "Open"),
    ("Issue", "KPI definitions conflict across 7 BI tools", "Certification sprint with a named KPI arbiter.", "Product owner", "Month 2", "High", "Open"),
    ("Risk", "Data trust gap", "Reconcile every measure; 3–5 month parallel run.", "Testing lead", "Month 5", "High", "Open"),
    ("Dependency", "Snowflake edition decision for SOX", "Business Critical assessed with Snowflake before build.", "Enterprise architect", "Month 1", "High", "Open"),
    ("Dependency", "Written approval for AI coding tools on client code", "Claude Code, Cortex Code and Copilot boundaries documented.", "Client program head", "Sprint 0", "High", "Open"),
    ("Dependency", "Service accounts for ADW, ODI and OAC", "Legacy read access for the Estate Analyzer and AIM.", "Client IT", "Week 2", "Medium", "Open"),
    ("Assumption", "Boomi covers the 94 WMS tables for incremental loads", "Confirm coverage; fall back to Snowpipe for gaps.", "Integration vendor", "Month 1", "Medium", "Open"),
    ("Decision", "AWS DMS for terabyte history into S3", "Keep the integration platform for incremental loads only.", "Solution architect", "", "Low", "Closed"),
    ("Decision", "Keep the Tableau UI like for like", "Users compare numbers, not designs; redesign after trust.", "Product owner", "", "Low", "Closed"),
    ("Decision", "Dynamic masking replaces duplicate copies that hid sensitive rates", "Approved by the data governance lead.", "Data governance lead", "", "Low", "Closed"),
]


def seed_pmo(c):
    pb = json.loads((SEED / "delivery_playbook.json").read_text())
    for k, v in pb.items():
        c.execute("INSERT INTO pb_doc VALUES (%s,%s)", (k, json.dumps(v)))
    for track, scores in SEED_READINESS.items():
        for i, s in enumerate(scores):
            c.execute("INSERT INTO pmo_readiness(track,qid,score,updated_by) VALUES (%s,%s,%s,'seed')", (track, i, s))
    for i, m in enumerate(pb["measurement"]["metrics"]):
        a, st, note = SEED_KPI.get(m["name"], (None, "na", None))
        c.execute("""INSERT INTO pmo_kpi(seq,category,name,what,source,target,cadence,capture,actual,status,note)
                     VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                  (i, m["category"], m["name"], m["what"], m["source"], m["target"], m["cadence"], m["capture"], a, st, note))
    for i, u in enumerate(pb["usecases"]["items"]):
        c.execute("""INSERT INTO pmo_usecase(seq,archetype,stage,activity,value,rep,comp,risk,automation,prereq)
                     VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                  (i, u["archetype"], u["stage"], u["activity"], u["value"], u["rep"], u["comp"], u["risk"], u["automation"], u["prereq"]))
    for r in SEED_RAID:
        c.execute("INSERT INTO pmo_raid(kind,title,detail,owner,due,severity,status) VALUES (%s,%s,%s,%s,%s,%s,%s)", r)
    for idx in range(2):  # primer is done; readiness half done
        c.execute("INSERT INTO pmo_check(stage,archetype,idx,done,updated_by) VALUES ('primer','all',%s,TRUE,'seed')", (idx,))


# ---------------------------------------------------------------------------
# Readiness
# ---------------------------------------------------------------------------
def tracks():
    have = [r["track"] for r in q("SELECT DISTINCT track FROM pmo_readiness ORDER BY track")]
    return have or TRACKS


def readiness_score(track: str) -> dict:
    model = doc("readiness")
    ans = {r["qid"]: r for r in q("SELECT qid, score, note FROM pmo_readiness WHERE track=%s", (track,))}
    dims, qs = {}, []
    for i, x in enumerate(model["questions"]):
        a = ans.get(i, {})
        qs.append({"id": i, **x, "score": a.get("score"), "note": a.get("note")})
        d = dims.setdefault(x["dim"], {"dim": x["dim"], "weight": model["weights"][x["dim"]], "sum": 0, "answered": 0, "count": 0})
        d["count"] += 1
        if a.get("score") is not None:
            d["sum"] += a["score"]; d["answered"] += 1
    total = answered = 0
    for d in dims.values():
        d["pct"] = round(100 * d["sum"] / (d["answered"] * 3)) if d["answered"] else 0
        total += d["pct"] * d["weight"] / 100
        answered += d["answered"]
        d["lagging"] = bool(d["answered"]) and d["pct"] < 67
        d["remedy"] = model["remedy"][d["dim"]] if d["lagging"] else []
    pct = round(total)
    band = "Not scored yet" if not answered else "Ready" if pct >= 75 else "Ready with remediation" if pct >= 50 else "Not ready yet"
    return {"track": track, "questions": qs, "dims": list(dims.values()), "overall": pct, "band": band,
            "answered": answered, "total": len(qs), "qualification": model["qualification"]}


@router.get("/readiness")
def get_readiness(track: str | None = None, p: dict = Depends(screen("readiness"))):
    ts = tracks()
    t = track if track in ts else ts[0]
    return {**readiness_score(t), "tracks": [{"track": x, "overall": readiness_score(x)["overall"]} for x in ts]}


class Answer(BaseModel):
    score: int | None = None
    note: str | None = None


@router.put("/readiness/{track}/{qid}")
def put_answer(track: str, qid: int, body: Answer, p: dict = Depends(screen("readiness"))):
    if body.score is not None and not 0 <= body.score <= 3:
        raise HTTPException(400, "Score is 0 to 3.")
    one("""INSERT INTO pmo_readiness(track,qid,score,note,updated_by) VALUES (%s,%s,%s,%s,%s)
           ON CONFLICT (track,qid) DO UPDATE SET score=EXCLUDED.score, note=COALESCE(EXCLUDED.note, pmo_readiness.note),
           updated_by=EXCLUDED.updated_by, updated_at=now() RETURNING 1""", (track, qid, body.score, body.note, p["code"]))
    return readiness_score(track)


class TrackIn(BaseModel):
    name: str


@router.post("/readiness/tracks")
def add_track(body: TrackIn, p: dict = Depends(screen("readiness"))):
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Name the track.")
    for i in range(len(doc("readiness")["questions"])):
        one("INSERT INTO pmo_readiness(track,qid,score,updated_by) VALUES (%s,%s,NULL,%s) ON CONFLICT DO NOTHING RETURNING 1", (name, i, p["code"]))
    return get_readiness(name, p)


# ---------------------------------------------------------------------------
# Playbook, roadmap, team
# ---------------------------------------------------------------------------
@router.get("/playbook")
def playbook(p: dict = Depends(screen("playbook"))):
    keys = ("primer", "accelerators", "archetypes", "practices", "artefacts", "cases", "worked", "harness")
    out = {k: doc(k) for k in keys}
    for a in out["archetypes"]:
        a.pop("phases", None)
    return out


def checks(archetype: str):
    done = {(r["stage"], r["idx"]) for r in q("SELECT stage, idx FROM pmo_check WHERE done AND archetype IN (%s,'all')", (archetype,))}
    sc = doc("stage_checks")
    return {st: [{"text": t, "done": (st, i) in done} for i, t in enumerate(items)] for st, items in sc.items()}


@router.get("/roadmap")
def roadmap(archetype: str = "migrate", p: dict = Depends(screen("roadmap"))):
    arch = doc("archetypes")
    a = next((x for x in arch if x["key"] == archetype), arch[0])
    return {"stages": doc("stages"), "checks": checks(a["key"]), "plan": doc("plan"), "setup": doc("setup"),
            "onboarding": doc("onboarding"), "program": doc("program"), "autonomy": doc("autonomy"), "context": doc("context"),
            "ways": doc("ways"), "optimize": doc("optimize"),
            "archetypes": [{"key": x["key"], "lc": x["lc"], "title": x["title"], "tag": x["tag"]} for x in arch],
            "archetype": a, "harness": {k: doc("harness")[k] for k in ("flow", "dataFlow", "skills", "readiness")}}


class CheckIn(BaseModel):
    stage: str
    archetype: str = "all"
    idx: int
    done: bool


@router.put("/roadmap/check")
def put_check(body: CheckIn, p: dict = Depends(screen("roadmap"))):
    arch = "all" if body.stage in ("primer", "readiness", "plan", "setup") else body.archetype
    one("""INSERT INTO pmo_check(stage,archetype,idx,done,updated_by) VALUES (%s,%s,%s,%s,%s)
           ON CONFLICT (stage,archetype,idx) DO UPDATE SET done=EXCLUDED.done, updated_by=EXCLUDED.updated_by, updated_at=now() RETURNING 1""",
        (body.stage, arch, body.idx, body.done, p["code"]))
    return checks(body.archetype)


@router.get("/team")
def team(p: dict = Depends(screen("team"))):
    return doc("team")


# ---------------------------------------------------------------------------
# Estimator (unit-effort model)
# ---------------------------------------------------------------------------
def estimate(params: dict) -> dict:
    cfg = doc("estimator")
    e = json.loads(json.dumps(cfg["defaults"]))
    for k, v in (params or {}).items():
        if isinstance(v, dict) and isinstance(e.get(k), dict):
            e[k].update({kk: max(0, float(vv or 0)) for kk, vv in v.items() if kk in e[k]})
        elif k in e and v not in (None, ""):
            e[k] = float(v)
    e["pilot"] = min(100, max(0, e["pilot"])); e["months"] = max(1, e["months"]); e["speed"] = e["speed"] or 1
    p = e["pilot"] / 100
    comp, obj = {}, 0
    for c in ("ETL", "DW", "BI"):
        full = sum(e[c][x] * cfg["base"][c] * cfg["mult"][x] for x in "SMC")
        v = full * p + full * (1 - p) / e["speed"]
        comp[c] = {"objects": sum(e[c][x] for x in "SMC"), "full": round(full), "with_speedup": round(v)}
        obj += v
    fw = sum(e["fw"][x] * sum(cfg["fw"][x]) for x in "SMC")
    disc = sum(e["disc"][x] * cfg["disc"][x] for x in "SMC")
    total = obj + fw + disc
    no_ai = sum(c["full"] for c in comp.values()) + fw + disc
    fs = e["fs"]
    pts = fs["a"] * 2 + fs["sa"] * 1.5 + fs["sk"] + fs["t"] * .5 + fs["f"] * .5
    return {"inputs": e, "components": comp, "frameworks_pd": round(fw), "discovery_pd": round(disc),
            "total_pd": round(total), "person_months": round(total / 22, 1), "avg_fte": round(total / 22 / e["months"], 1),
            "without_speedup_pd": round(no_ai), "saving_pd": round(no_ai - total),
            "by_activity": {k: round(obj * v) for k, v in cfg["share"].items()},
            "framework_score": {"points": pts, "class": "Simple" if pts <= 20 else "Medium" if pts <= 36 else "Complex"},
            "note": cfg["note"]}


@router.get("/estimator")
def get_estimator(p: dict = Depends(screen("estimator"))):
    cfg = doc("estimator")
    return {"config": cfg, "result": estimate({}),
            "scenarios": q("SELECT id, name, result->'total_pd' AS total_pd, result->'avg_fte' AS avg_fte, created_by, created_at FROM pmo_estimate ORDER BY id DESC LIMIT 20")}


class EstIn(BaseModel):
    params: dict = {}
    save_as: str | None = None


@router.post("/estimator")
def post_estimator(body: EstIn, p: dict = Depends(screen("estimator"))):
    r = estimate(body.params)
    if body.save_as and body.save_as.strip():
        one("INSERT INTO pmo_estimate(name,params,result,created_by) VALUES (%s,%s,%s,%s) RETURNING 1",
            (body.save_as.strip(), json.dumps(body.params), json.dumps(r), p["code"]))
    return r


@router.get("/estimator/{eid}")
def get_scenario(eid: int, p: dict = Depends(screen("estimator"))):
    r = one("SELECT * FROM pmo_estimate WHERE id=%s", (eid,))
    if not r:
        raise HTTPException(404)
    return r


# ---------------------------------------------------------------------------
# AI use-case matrix
# ---------------------------------------------------------------------------
LVL = {"High": 3, "Med": 2, "Medium": 2, "Low": 1}
AUTO = {"Execute": 3, "Orchestrate": 3, "Recommend": 2}


def uc_score(u: dict) -> dict:
    val, rep = LVL.get(u["value"], 2), LVL.get(u["rep"], 2)
    feas, safe = 4 - LVL.get(u["comp"], 2), 4 - LVL.get(u["risk"], 2)
    auto = next((v for k, v in AUTO.items() if k in (u["automation"] or "")), 0)
    score = round(100 * (val * .30 + rep * .20 + feas * .20 + safe * .15 + auto * .15) / 3)
    if auto == 0 or u["risk"] == "High":
        lane = "Human gate"
    elif score >= 80:
        lane = "Pilot wave"
    elif score >= 65:
        lane = "Next wave"
    else:
        lane = "Assist only"
    return {**u, "score": score, "lane": lane}


@router.get("/usecases")
def usecases(p: dict = Depends(screen("usecases"))):
    d = doc("usecases")
    items = [uc_score(u) for u in q("SELECT * FROM pmo_usecase ORDER BY seq, id")]
    return {"criteria": d["criteria"], "impact": d["impact"], "items": items,
            "archetypes": [{"key": a["key"], "title": a["title"], "lc": a["lc"]} for a in doc("archetypes")],
            "weights": {"Value": 30, "Repeatability": 20, "Feasibility (low complexity)": 20, "Trust and safety (low risk)": 15, "Automation": 15}}


class UcIn(BaseModel):
    value: str | None = None
    rep: str | None = None
    comp: str | None = None
    risk: str | None = None
    automation: str | None = None


@router.put("/usecases/{uid}")
def put_usecase(uid: int, body: UcIn, p: dict = Depends(screen("usecases"))):
    sets = {k: v for k, v in body.model_dump().items() if v is not None}
    if not sets:
        raise HTTPException(400, "Nothing to change.")
    one(f"UPDATE pmo_usecase SET {', '.join(f'{k}=%s' for k in sets)}, origin='curated' WHERE id=%s RETURNING 1", (*sets.values(), uid))
    return uc_score(one("SELECT * FROM pmo_usecase WHERE id=%s", (uid,)))


# ---------------------------------------------------------------------------
# KPI scorecard
# ---------------------------------------------------------------------------
@router.get("/kpis")
def kpis(p: dict = Depends(screen("kpis"))):
    m = doc("measurement")
    rows = q("SELECT * FROM pmo_kpi ORDER BY seq, id")
    cats = []
    for r in rows:
        if not cats or cats[-1]["category"] != r["category"]:
            cats.append({"category": r["category"], "metrics": []})
        cats[-1]["metrics"].append(r)
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in ("green", "amber", "red", "na")}
    return {"dims": m["dims"], "principle": m["principle"], "method": m["method"], "categories": cats, "counts": counts}


class KpiIn(BaseModel):
    actual: str | None = None
    status: str | None = None
    note: str | None = None


@router.put("/kpis/{kid}")
def put_kpi(kid: int, body: KpiIn, p: dict = Depends(screen("kpis"))):
    if body.status and body.status not in ("green", "amber", "red", "na"):
        raise HTTPException(400, "Status is green, amber, red or na.")
    sets = {k: v for k, v in body.model_dump().items() if v is not None}
    one(f"UPDATE pmo_kpi SET {', '.join(f'{k}=%s' for k in sets)}, updated_by=%s, updated_at=now() WHERE id=%s RETURNING 1",
        (*sets.values(), p["code"], kid))
    return one("SELECT * FROM pmo_kpi WHERE id=%s", (kid,))


# ---------------------------------------------------------------------------
# Governance, RAI and RAID
# ---------------------------------------------------------------------------
@router.get("/governance")
def governance(p: dict = Depends(screen("governance"))):
    h = doc("harness")
    return {"governance": doc("governance"), "rai": doc("rai"), "guardrails": h["guardrails"], "harness_readiness": h["readiness"],
            "raid": q("SELECT * FROM pmo_raid ORDER BY CASE status WHEN 'Closed' THEN 1 ELSE 0 END, CASE severity WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END, id"),
            "gates": q("""SELECT g.*, ps.name AS stage_name FROM gate_decision g LEFT JOIN pursuit_stage ps ON ps.code=g.stage_code
                          ORDER BY g.id DESC LIMIT 20""")}


class RaidIn(BaseModel):
    kind: str = "Risk"
    title: str
    detail: str | None = None
    owner: str | None = None
    due: str | None = None
    severity: str = "Medium"
    status: str = "Open"


@router.post("/raid")
def add_raid(body: RaidIn, p: dict = Depends(screen("governance"))):
    if not body.title.strip():
        raise HTTPException(400, "Give the item a title.")
    try:
        return one("""INSERT INTO pmo_raid(kind,title,detail,owner,due,severity,status,origin,created_by)
                      VALUES (%s,%s,%s,%s,%s,%s,%s,'curated',%s) RETURNING *""",
                   (body.kind, body.title.strip(), body.detail, body.owner, body.due, body.severity, body.status, p["code"]))
    except Exception as e:
        raise HTTPException(400, f"Invalid RAID item: {str(e).splitlines()[0]}")


@router.put("/raid/{rid}")
def edit_raid(rid: int, body: RaidIn, p: dict = Depends(screen("governance"))):
    r = one("""UPDATE pmo_raid SET kind=%s,title=%s,detail=%s,owner=%s,due=%s,severity=%s,status=%s,origin='curated'
               WHERE id=%s RETURNING *""", (body.kind, body.title, body.detail, body.owner, body.due, body.severity, body.status, rid))
    if not r:
        raise HTTPException(404)
    return r


@router.delete("/raid/{rid}")
def delete_raid(rid: int, p: dict = Depends(screen("governance"))):
    one("DELETE FROM pmo_raid WHERE id=%s RETURNING 1", (rid,))
    return {"ok": True}


# ---------------------------------------------------------------------------
# PMO skills (engines for the skills studio)
# ---------------------------------------------------------------------------
PMO_SKILLS = {
    "pmo-readiness-scorecard": {"title": "Readiness scorecard", "screens": ["readiness"],
        "engine": "Scores a track on the 17 weighted readiness questions, sets the qualification band and turns lagging dimensions into owned remediation actions (optionally raised in the RAID log).",
        "fields": [{"key": "track", "label": "Track", "kind": "choice", "default": TRACKS[0], "options": TRACKS},
                   {"key": "raise", "label": "Raise remediation actions in the RAID log", "kind": "choice", "default": "no", "options": ["no", "yes"]}]},
    "pmo-unit-effort-estimator": {"title": "Unit-effort estimator", "screens": ["estimator"],
        "engine": "Prices ETL, warehouse and BI objects by complexity, frameworks and discovery with the unit-effort model, applies the pilot share and wave speed-up, and returns person-days, person-months and average FTE.",
        "fields": [{"key": "ETL", "label": "ETL pipelines or mappings (simple, medium, complex)", "kind": "text", "default": "40, 30, 12"},
                   {"key": "DW", "label": "Facts, dims or semantic views (simple, medium, complex)", "kind": "text", "default": "30, 20, 10"},
                   {"key": "BI", "label": "Dashboards or reports (simple, medium, complex)", "kind": "text", "default": "20, 20, 10"},
                   {"key": "pilot", "label": "Share in the pilot wave (%)", "kind": "text", "default": "10"},
                   {"key": "speed", "label": "Wave speed-up after the pilot", "kind": "choice", "default": "3", "options": ["3", "1.5", "1"]},
                   {"key": "months", "label": "Delivery months", "kind": "text", "default": "9"},
                   {"key": "save_as", "label": "Save as scenario (optional)", "kind": "text", "default": ""}]},
    "pmo-usecase-prioritizer": {"title": "AI use-case prioritizer", "screens": ["usecases"],
        "engine": "Ranks lifecycle activities on value, repeatability, feasibility, trust and automation, and assigns each a lane: pilot wave, next wave, assist only or human gate.",
        "fields": [{"key": "archetype", "label": "Archetype", "kind": "choice", "default": "all", "options": ["all", "migrate", "product", "bi", "ai"]}]},
    "pmo-steering-pack": {"title": "Steering pack", "screens": ["kpis", "governance", "readiness"],
        "engine": "Compiles the monthly steering pack: readiness per track, KPI scorecard by RAG, top risks and issues, decisions needed, playbook progress and recent gate decisions.",
        "fields": [{"key": "period", "label": "Reporting period", "kind": "text", "default": date.today().strftime("%B %Y")},
                   {"key": "audience", "label": "Audience", "kind": "choice", "default": "Steering committee", "options": ["Steering committee", "Weekly RAID review", "Show-and-tell"]}]},
}


def _triple(v, default):
    try:
        a = [float(x) for x in str(v).replace(";", ",").split(",")]
        return dict(zip("SMC", (a + [0, 0, 0])[:3]))
    except ValueError:
        return dict(zip("SMC", default))


def eng_readiness(params, p, session):
    t = params.get("track") or TRACKS[0]
    r = readiness_score(t)
    md = [f"# Readiness scorecard · {t}", "", f"**Overall {r['overall']}% · {r['band']}** ({r['answered']} of {r['total']} answered)", "",
          "| Dimension | Weight | Score |", "|---|---|---|"] + [f"| {d['dim']} | {d['weight']}% | {d['pct']}%{' · lagging' if d['lagging'] else ''} |" for d in r["dims"]]
    low = [x for x in r["questions"] if x["score"] is not None and x["score"] <= 1]
    if low:
        md += ["", "## Questions scored 0 or 1", ""] + [f"- **{x['dim']}**: {x['question']} ({x['levels'][x['score']]})" for x in low]
    raised = 0
    lag = [d for d in r["dims"] if d["lagging"]]
    if lag:
        md += ["", "## Remediation before Sprint 0 ends", ""]
        for d in lag:
            md += [f"### {d['dim']} ({d['pct']}%)"] + [f"- {x}" for x in d["remedy"]]
            if params.get("raise") == "yes":
                for x in d["remedy"]:
                    if not one("SELECT 1 FROM pmo_raid WHERE title=%s", (x[:200],)):
                        one("""INSERT INTO pmo_raid(kind,title,detail,owner,due,severity,status,origin,created_by)
                               VALUES ('Issue',%s,%s,'AI Champion','Sprint 0','Medium','Open','skill',%s) RETURNING 1""",
                            (x[:200], f"Readiness remediation · {t} · {d['dim']}", p["code"]))
                        raised += 1
    md += ["", "## Qualification (FlyHigh baseline)", ""] + [f"- **{k.title()}:** {v}" for k, v in r["qualification"].items()]
    return {"summary": f"{t}: {r['overall']}% · {r['band']} · {len(lag)} lagging dimension(s)" + (f" · {raised} RAID actions raised" if raised else ""),
            "files": {"readiness_scorecard.md": "\n".join(md), "readiness.json": json.dumps(r, indent=2, default=str)}, "notes": []}


def eng_estimate(params, p, session):
    d = doc("estimator")["defaults"]
    prm = {c: _triple(params.get(c, ""), [d[c][x] for x in "SMC"]) for c in ("ETL", "DW", "BI")}
    for k in ("pilot", "speed", "months"):
        try:
            prm[k] = float(params.get(k) or d[k])
        except ValueError:
            prm[k] = d[k]
    r = estimate(prm)
    if params.get("save_as", "").strip():
        one("INSERT INTO pmo_estimate(name,params,result,created_by) VALUES (%s,%s,%s,%s) RETURNING 1",
            (params["save_as"].strip(), json.dumps(prm), json.dumps(r), p["code"]))
    md = ["# Unit-effort estimate", "", f"**{r['total_pd']:,} person-days · {r['person_months']} person-months · {r['avg_fte']} average FTE over {int(r['inputs']['months'])} months**", "",
          "| Component | Objects | At pilot effort (PD) | With wave speed-up (PD) |", "|---|---|---|---|"]
    md += [f"| {c} | {int(v['objects'])} | {v['full']:,} | {v['with_speedup']:,} |" for c, v in r["components"].items()]
    md += [f"| AI frameworks | | {r['frameworks_pd']:,} | {r['frameworks_pd']:,} |", f"| Discovery and design | | {r['discovery_pd']:,} | {r['discovery_pd']:,} |",
           f"| **Total** | | **{r['without_speedup_pd']:,}** | **{r['total_pd']:,}** |", "",
           "Object effort by activity: " + " · ".join(f"{k} {v:,} PD" for k, v in r["by_activity"].items()), "", f"_{r['note']}_"]
    return {"summary": f"{r['total_pd']:,} PD · {r['avg_fte']} avg FTE · saves {r['saving_pd']:,} PD vs pilot effort",
            "files": {"estimate.md": "\n".join(md), "estimate.json": json.dumps(r, indent=2)}, "notes": []}


def eng_usecases(params, p, session):
    a = params.get("archetype") or "all"
    items = [uc_score(u) for u in q("SELECT * FROM pmo_usecase ORDER BY seq")]
    items = [u for u in items if a == "all" or u["archetype"] == a]
    items.sort(key=lambda u: -u["score"])
    lanes = {}
    for u in items:
        lanes.setdefault(u["lane"], []).append(u)
    md = [f"# AI use-case priorities · {a}", ""]
    for lane in ("Pilot wave", "Next wave", "Assist only", "Human gate"):
        if lane in lanes:
            md += [f"## {lane} ({len(lanes[lane])})", "", "| Score | Archetype | Stage | Activity | Automation | Prerequisites |", "|---|---|---|---|---|---|"]
            md += [f"| {u['score']} | {u['archetype']} | {u['stage']} | {u['activity']} | {u['automation']} | {u['prereq']} |" for u in lanes[lane]]
            md.append("")
    return {"summary": " · ".join(f"{k}: {len(v)}" for k, v in lanes.items()),
            "files": {"usecase_priorities.md": "\n".join(md)}, "notes": []}


def eng_steering(params, p, session):
    period, aud = params.get("period") or date.today().strftime("%B %Y"), params.get("audience") or "Steering committee"
    rd = [readiness_score(t) for t in tracks()]
    kp = q("SELECT * FROM pmo_kpi ORDER BY seq")
    rag = {s: [k for k in kp if k["status"] == s] for s in ("red", "amber", "green")}
    raid = q("SELECT * FROM pmo_raid WHERE status <> 'Closed' ORDER BY CASE severity WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END, id")
    dec = q("SELECT * FROM pmo_raid WHERE kind='Decision' ORDER BY id DESC LIMIT 5")
    sc = doc("stage_checks")
    done = {(r["stage"], r["idx"]) for r in q("SELECT stage, idx FROM pmo_check WHERE done")}
    prog = [(s["name"], sum(1 for i in range(len(sc[s["code"]])) if (s["code"], i) in done), len(sc[s["code"]])) for s in doc("stages")]
    gates = q("SELECT * FROM gate_decision ORDER BY id DESC LIMIT 5")
    overall = "Red" if rag["red"] or any(r["severity"] == "High" and r["kind"] == "Issue" for r in raid) else "Amber" if rag["amber"] else "Green"
    md = [f"# FlyHigh · {aud} pack · {period}", "", f"**Overall status: {overall}** · KPIs {len(rag['green'])} green, {len(rag['amber'])} amber, {len(rag['red'])} red · {len(raid)} open RAID items", "",
          "## Readiness by track", ""] + [f"- **{r['track']}**: {r['overall']}% · {r['band']}" + (f" · lagging: {', '.join(d['dim'] for d in r['dims'] if d['lagging'])}" if any(d['lagging'] for d in r['dims']) else "") for r in rd]
    md += ["", "## KPI scorecard", "", "| Metric | Target | Actual | Status | Note |", "|---|---|---|---|---|"]
    md += [f"| {k['name']} | {k['target']} | {k['actual'] or '—'} | {k['status'].upper()} | {k['note'] or ''} |" for k in rag["red"] + rag["amber"] + rag["green"]]
    md += ["", "## Top risks, issues and dependencies", ""] + [f"- **{r['kind']} · {r['severity']}** — {r['title']} (owner {r['owner'] or 'unassigned'}, due {r['due'] or 'n/a'}, {r['status']})" for r in raid[:8]]
    md += ["", "## Decisions needed from this forum", ""] + ([f"- {r['title']} — {r['owner']}" for r in raid if r["kind"] in ("Dependency", "Issue") and r["severity"] == "High"] or ["- None"])
    md += ["", "## Decisions recorded", ""] + [f"- {r['title']}" for r in dec]
    md += ["", "## Playbook progress", ""] + [f"- {n}: {d} of {t}" for n, d, t in prog]
    if gates:
        md += ["", "## Recent gate decisions", ""] + [f"- {g['gate_code']} ({g['stage_code']}): {g['decision']} by {g['approver']}" for g in gates]
    md += ["", "_Agents compile the pack; the program manager owns the narrative and steering owns the decisions._"]
    return {"summary": f"{aud} · {period}: {overall} · {len(rag['red'])} red / {len(rag['amber'])} amber KPIs · {len(raid)} open RAID items",
            "files": {"steering_pack.md": "\n".join(md)}, "notes": []}


PMO_ENGINES = {"pmo-readiness-scorecard": eng_readiness, "pmo-unit-effort-estimator": eng_estimate,
               "pmo-usecase-prioritizer": eng_usecases, "pmo-steering-pack": eng_steering}
