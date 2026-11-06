"""Pursuit lifecycle API: overview, stages, kit workspace, win room, response quality, lens."""
import json
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .access import allowed, allowed_codes, persona, require_stage, screen, stage_code_for_num
from .db import one, q
from .paths import TEMPLATES

router = APIRouter(prefix="/api")
LOCKED_FIELDS = ("code", "num", "name", "loop", "gate_code", "lane", "critical")


# ---------------- Lens ----------------
@router.get("/lens/roles")
def lens_roles():
    return q("SELECT * FROM lens_role ORDER BY seq")


@router.get("/lens/list")
def lens_list():
    """Every lens, its personas and whether it is available yet (no persona needed: this feeds the picker)."""
    lenses = q("SELECT * FROM lens ORDER BY seq")
    roles = q("SELECT * FROM lens_role ORDER BY seq")
    for l in lenses:
        l["roles"] = [r for r in roles if r["lens"] == l["code"]]
    return lenses


@router.get("/lens/me")
def lens_me(p: dict = Depends(persona)):
    return {"persona": p, "lens": p["lens"], "lens_info": one("SELECT * FROM lens WHERE code=%s", (p["lens"],)),
            "screens": sorted(allowed_codes("screen", p["lens"])),
            "pursuit_stages": sorted(allowed_codes("pursuit_stage", p["lens"]))}


@router.get("/lens/access")
def lens_access(p: dict = Depends(persona)):
    return q("""SELECT a.*, ps.num FROM access_rule a LEFT JOIN pursuit_stage ps ON a.resource='pursuit_stage' AND ps.code=a.code
                ORDER BY a.resource DESC, ps.num NULLS FIRST, a.label""")


# ---------------- Lifecycle overview (both lenses) ----------------
@router.get("/lifecycle")
def lifecycle(p: dict = Depends(screen("lifecycle"))):
    lens = p["lens"]
    ok = allowed_codes("pursuit_stage", lens)
    pursuit = q("SELECT code, num, name, gate_code, gate, loop, critical, extra->>'audience' AS audience FROM pursuit_stage ORDER BY num")
    for s in pursuit:
        s["locked"] = s["code"] not in ok
    impl = q("SELECT code, seq, name, gate, lead_role, phase FROM stage ORDER BY seq")
    impl_ok = allowed("screen", "workflow", lens)
    for s in impl:
        s["locked"] = not impl_ok
    pb = one("SELECT data FROM pb_doc WHERE key='stages'")
    pmo_ok = allowed("screen", "roadmap", lens)
    program = [{**s, "seq": i + 1, "locked": not pmo_ok} for i, s in enumerate(pb["data"] if pb else [])]
    return {"lens": lens, "pursuit": pursuit, "implementation": impl, "program": program,
            "lenses": q("SELECT * FROM lens ORDER BY seq"),
            "screens": q("SELECT * FROM access_rule WHERE resource='screen' ORDER BY label")}


# ---------------- Pursuit ----------------
def _num_set(stages: str) -> set[int]:
    out = set()
    for part in re.split(r"[,\s]+", stages or ""):
        if "-" in part:
            a, b = part.split("-"); out |= set(range(int(a), int(b) + 1))
        elif part.isdigit():
            out.add(int(part))
    return out


@router.get("/pursuit/overview")
def pursuit_overview(p: dict = Depends(screen("pursuit"))):
    lens = p["lens"]
    ok = allowed_codes("pursuit_stage", lens)
    stages = q("SELECT * FROM pursuit_stage ORDER BY num")
    out = []
    for s in stages:
        if s["code"] in ok:
            out.append({**s, "locked": False, "audience": s["extra"].get("audience")})
        else:
            out.append({**{k: s[k] for k in LOCKED_FIELDS}, "locked": True, "audience": s["extra"].get("audience")})
    nums = {s["num"] for s in stages if s["code"] in ok}
    arts = [a for a in q("SELECT * FROM pursuit_artefact ORDER BY id") if _num_set(a["stages"]) & nums]
    refs = q("SELECT kind, data FROM pursuit_ref ORDER BY kind, seq")
    method = next(r["data"] for r in refs if r["kind"] == "method")
    pack = lambda k: [r["data"] for r in refs if r["kind"] == k]
    return {"lens": lens, "stages": out, "artefacts": arts, "method": method,
            "dependencies": pack("dependency"),
            "human_inputs": pack("human_input") if lens == "pursuit" else [],
            "objections": pack("objection") if lens == "pursuit" else [],
            "roles": q("SELECT * FROM lens_role ORDER BY seq")}


@router.get("/pursuit/stages/{code}")
def pursuit_stage(code: str, p: dict = Depends(screen("pursuit"))):
    s = one("SELECT * FROM pursuit_stage WHERE code=%s", (code,))
    if not s:
        raise HTTPException(404)
    require_stage(code, p)
    s["audience"] = s["extra"].get("audience")
    s["templates"] = q("SELECT t.*, (SELECT count(*) FROM kit_sheet WHERE template_id=t.id) AS sheets FROM kit_template t WHERE stage_num=%s ORDER BY sample, file", (s["num"],))
    s["artefact_detail"] = [a for a in q("SELECT * FROM pursuit_artefact ORDER BY id") if s["num"] in _num_set(a["stages"])]
    names = [re.sub(r" \(.*", "", x) for x in s["skills"] + s["tools"]]
    s["skill_detail"] = q("SELECT * FROM pursuit_skill WHERE name = ANY(%s)", (names,))
    hand = s["extra"].get("handover") or []
    can_impl = allowed("screen", "workflow", p["lens"])
    s["handover"] = [{"code": h["code"], "name": h["name"], "seq": h["seq"], "locked": not can_impl}
                     for h in q("SELECT code, name, seq FROM stage WHERE code = ANY(%s) ORDER BY seq", (hand,))]
    return s


# ---------------- Kit workspace ----------------
def _template_access(tid: int, p: dict) -> dict:
    t = one("SELECT * FROM kit_template WHERE id=%s", (tid,))
    if not t:
        raise HTTPException(404)
    require_stage(stage_code_for_num(t["stage_num"]), p)
    return t


def _sheet_access(sid: int, p: dict) -> dict:
    sh = one("SELECT * FROM kit_sheet WHERE id=%s", (sid,))
    if not sh:
        raise HTTPException(404)
    _template_access(sh["template_id"], p)
    return sh


@router.get("/kit")
def kit(p: dict = Depends(screen("kit"))):
    ok = allowed_codes("pursuit_stage", p["lens"])
    stages = q("SELECT code, num, name, gate_code FROM pursuit_stage ORDER BY num")
    nums = {s["num"] for s in stages if s["code"] in ok}
    temps = q("SELECT * FROM kit_template ORDER BY stage_num, sample, file")
    sheets = q("SELECT s.id, s.template_id, s.seq, s.name, s.title, (SELECT count(*) FROM kit_row r WHERE r.sheet_id=s.id) AS rows FROM kit_sheet s ORDER BY template_id, seq")
    for t in temps:
        t["sheets"] = [s for s in sheets if s["template_id"] == t["id"]]
    return {"stages": [{**s, "locked": s["code"] not in ok} for s in stages],
            "templates": [t for t in temps if t["stage_num"] in nums],
            "skills": q("SELECT * FROM pursuit_skill ORDER BY id")}


@router.get("/kit/sheets/{sid}")
def kit_sheet(sid: int, p: dict = Depends(screen("kit"))):
    sh = _sheet_access(sid, p)
    sh["rows"] = q("SELECT id, seq, data, origin, updated_by FROM kit_row WHERE sheet_id=%s ORDER BY seq, id", (sid,))
    sh["template"] = one("SELECT * FROM kit_template WHERE id=%s", (sh["template_id"],))
    return sh


@router.post("/kit/sheets/{sid}/rows")
def kit_add_row(sid: int, data: dict[str, Any] = Body(...), p: dict = Depends(screen("kit"))):
    _sheet_access(sid, p)
    seq = one("SELECT COALESCE(max(seq),0)+1 AS n FROM kit_row WHERE sheet_id=%s", (sid,))["n"]
    return one("INSERT INTO kit_row(sheet_id,seq,data,origin,updated_by) VALUES (%s,%s,%s,'curated',%s) RETURNING *",
               (sid, seq, json.dumps(data), p["code"]))


@router.put("/kit/rows/{rid}")
def kit_update_row(rid: int, data: dict[str, Any] = Body(...), p: dict = Depends(screen("kit"))):
    r = one("SELECT * FROM kit_row WHERE id=%s", (rid,))
    if not r:
        raise HTTPException(404)
    _sheet_access(r["sheet_id"], p)
    return one("UPDATE kit_row SET data=%s, origin='curated', updated_by=%s WHERE id=%s RETURNING *", (json.dumps(data), p["code"], rid))


@router.delete("/kit/rows/{rid}")
def kit_delete_row(rid: int, p: dict = Depends(screen("kit"))):
    r = one("SELECT * FROM kit_row WHERE id=%s", (rid,))
    if not r:
        raise HTTPException(404)
    _sheet_access(r["sheet_id"], p)
    one("DELETE FROM kit_row WHERE id=%s RETURNING id", (rid,))
    return {"deleted": rid}


@router.get("/kit/download/{tid}")
def kit_download(tid: int, persona_code: str):
    # Browser downloads can't set headers, so the persona comes as a query parameter here.
    p = persona(persona_code)
    if not allowed("screen", "kit", p["lens"]):
        raise HTTPException(403)
    t = _template_access(tid, p)
    if not t["download"]:
        raise HTTPException(404, "FlyHigh samples are client-confidential and stay in the pursuit folder.")
    f = TEMPLATES / t["download"]
    if not f.is_file():
        raise HTTPException(404)
    return FileResponse(f, filename=t["file"])


# ---------------- Win room (pursuit only) ----------------
@router.get("/winroom")
def winroom(p: dict = Depends(screen("winroom"))):
    t = one("SELECT * FROM kit_template WHERE file LIKE %s", ("%proposal scorecard%",))
    sheets = q("SELECT * FROM kit_sheet WHERE template_id=%s ORDER BY seq", (t["id"],))
    out = {}
    for sh in sheets:
        rows = q("SELECT id, data FROM kit_row WHERE sheet_id=%s ORDER BY seq, id", (sh["id"],))
        out[sh["name"]] = {"sheet_id": sh["id"], "title": sh["title"], "guidance": sh["guidance"], "columns": sh["columns"],
                           "rows": [{"id": r["id"], **r["data"]} for r in rows]}
    return out


# ---------------- Response quality ----------------
def _section_scores():
    crit = q("SELECT * FROM rubric_criterion ORDER BY seq")
    secs = q("SELECT * FROM response_section ORDER BY num")
    scores = q("SELECT * FROM section_score")
    mh = q("SELECT * FROM section_musthave")
    total = 0.0
    for s in secs:
        sc = {x["criterion"]: x for x in scores if x["section_id"] == s["id"]}
        s["scores"] = {c["code"]: {"score": sc[c["code"]]["score"], "evidence": sc[c["code"]]["evidence"]} if c["code"] in sc else None for c in crit}
        met = {x["idx"]: x["met"] for x in mh if x["section_id"] == s["id"]}
        s["musthave_met"] = [met.get(i, False) for i in range(len(s["must_haves"]))]
        if sc:
            pts = sum(c["weight"] * (sc[c["code"]]["score"] if c["code"] in sc else 0) / 4 for c in crit)
            if not all(s["musthave_met"]):
                pts = min(pts, 89)
            s["current"] = round(pts, 1)
            s["scored"] = True
        else:
            s["current"] = s["baseline"]
            s["scored"] = False
        s["passes"] = s["current"] >= 90 and all(s["musthave_met"])
        s["weight"] = float(s["weight"])
        total += s["weight"] * s["current"] / 100
    baseline = sum(float(s["weight"]) * s["baseline"] / 100 for s in secs)
    return crit, secs, round(total, 1), round(baseline, 1)


@router.get("/quality")
def quality(p: dict = Depends(screen("quality"))):
    crit, secs, total, base = _section_scores()
    for s in secs:
        s["editable"] = p["lens"] == "pursuit" or s["owner_lens"] == "shared"
    return {"criteria": crit, "sections": secs, "overall": total, "baseline": base, "threshold": 90, "lens": p["lens"]}


class ScoreIn(BaseModel):
    criterion: str
    score: int
    evidence: str | None = None


def _editable(sid: int, p: dict):
    s = one("SELECT * FROM response_section WHERE id=%s", (sid,))
    if not s:
        raise HTTPException(404)
    if not (p["lens"] == "pursuit" or s["owner_lens"] == "shared"):
        raise HTTPException(403, f"Section '{s['name']}' is scored by the pursuit team; delivery reviewers score the shared sections.")


@router.put("/quality/{sid}/score")
def set_score(sid: int, body: ScoreIn, p: dict = Depends(screen("quality"))):
    _editable(sid, p)
    if not 0 <= body.score <= 4:
        raise HTTPException(400, "Score is 0–4")
    one("""INSERT INTO section_score(section_id,criterion,score,evidence,updated_by) VALUES (%s,%s,%s,%s,%s)
           ON CONFLICT (section_id,criterion) DO UPDATE SET score=EXCLUDED.score, evidence=EXCLUDED.evidence,
           updated_by=EXCLUDED.updated_by, updated_at=now() RETURNING 1""", (sid, body.criterion, body.score, body.evidence, p["code"]))
    return quality(p)


class MustIn(BaseModel):
    idx: int
    met: bool


@router.put("/quality/{sid}/musthave")
def set_musthave(sid: int, body: MustIn, p: dict = Depends(screen("quality"))):
    _editable(sid, p)
    one("""INSERT INTO section_musthave VALUES (%s,%s,%s) ON CONFLICT (section_id,idx) DO UPDATE SET met=EXCLUDED.met RETURNING 1""",
        (sid, body.idx, body.met))
    return quality(p)


@router.delete("/quality/{sid}")
def reset_section(sid: int, p: dict = Depends(screen("quality"))):
    _editable(sid, p)
    one("DELETE FROM section_score WHERE section_id=%s RETURNING 1", (sid,))
    one("DELETE FROM section_musthave WHERE section_id=%s RETURNING 1", (sid,))
    return quality(p)
