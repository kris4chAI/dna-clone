"""Skills studio API.

Pursuit skills (the nine AI Native Pursuit Engineering skills) run as engines over the app's own data:
gate readiness, scorecard recompute, commercials, section fixes, loop log, JD drafting, brand audit,
deck spec. Delivery skills (46 Snowflake generators in `snowskills`) emit reviewable Snowflake artefacts.
Every skill can also produce a ready-to-paste prompt for Claude, or call Claude when a key is configured.
"""
import io
import json
import os
import re
import statistics
import zipfile
from pathlib import Path
from typing import Any

import sqlglot

from . import paths  # noqa: F401  (puts skills/delivery on sys.path)
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import snowskills
from snowskills.skillmd import render as render_skill_md

from . import llm
from .access import allowed, allowed_codes, persona, require_stage
from .db import one, q
from .assurance_api import AW_ENGINES, AW_SKILLS
from .pmo_api import PMO_ENGINES, PMO_SKILLS

router = APIRouter(prefix="/api")
PURSUIT_MD = paths.PURSUIT_SKILLS
# Lens-owned engine skills beyond the pursuit set: PMO and assurance
EXTRA = {**{n: {**m, "kind": "pmo", "dir": paths.PMO_SKILLS, "run": PMO_ENGINES[n]} for n, m in PMO_SKILLS.items()},
         **{n: {**m, "kind": "assurance", "dir": paths.AW_SKILLS, "run": AW_ENGINES[n]} for n, m in AW_SKILLS.items()}}


def _md_path(name):
    return (EXTRA[name]["dir"] if name in EXTRA else PURSUIT_MD) / name / "SKILL.md"
PH = re.compile(r"^\[.*\]$")

# ---------------------------------------------------------------------------
# Pursuit skill catalogue
# ---------------------------------------------------------------------------
PURSUIT = {
    "rfp-response-orchestrator": {"title": "Pursuit orchestrator", "stages": [1, 2, 3, 4, 5, 6, 7, 8, 9], "lens": "shared",
        "engine": "Gate readiness: questions closed, template placeholders left, artefacts, stamps and the named approver; records gate decisions.",
        "fields": [{"key": "stage", "label": "Pursuit stage", "kind": "pstage", "default": "signal"}]},
    "rfp-win-scorecard": {"title": "Win scorecard", "stages": [3, 8], "lens": "pursuit",
        "engine": "Recomputes every person's overall score and RAG, simple and influence-weighted averages, competitor totals and the projected score, then lists pending actions by lift.",
        "fields": [{"key": "new_round", "label": "Start a new round (current overall becomes previous)", "kind": "choice", "default": "no", "options": ["no", "yes"]}]},
    "rfp-commercials-model": {"title": "Commercials model", "stages": [6], "lens": "pursuit",
        "engine": "Prices scope options from hours and the rate card, applies term discounts, totals TCO levers and computes client-retained ROI and payback in the kit workbook.",
        "fields": []},
    "rfp-section-rubric": {"title": "Section rubric", "stages": [8], "lens": "shared",
        "engine": "Ranks the highest-leverage fixes per section: missing must-haves first, then criteria by points lost, with what blocks each fix.",
        "fields": [{"key": "section", "label": "Section (blank = all)", "kind": "section", "default": ""}]},
    "rfp-section-loop": {"title": "Section loop", "stages": [8], "lens": "shared",
        "engine": "Records a loop round per section (score, must-haves, fixes) and sets status: PASS, PLATEAU, BLOCKED, ESCALATE or IN PROGRESS.",
        "fields": [{"key": "section", "label": "Section", "kind": "section", "default": "14"},
                   {"key": "record", "label": "Record a round now", "kind": "choice", "default": "no", "options": ["no", "yes"]},
                   {"key": "fixes", "label": "Fixes made this round", "kind": "textarea", "default": ""}]},
    "rfp-section-builder": {"title": "Section builder", "stages": [8], "lens": "shared",
        "engine": "Builds the section brief: what it must prove, must-haves with status, the ranked fix list and the stamps to apply, ready for drafting.",
        "fields": [{"key": "section", "label": "Section", "kind": "section", "default": "14"}]},
    "proposal-to-job-descriptions": {"title": "Job descriptions", "stages": [5], "lens": "shared",
        "engine": "Drafts one JD per role and location in the house style, with the location-tier must-haves taken from the skill.",
        "fields": [{"key": "roles", "label": "Roles (title | tier | count | seniority)", "kind": "lines",
                    "default": "AI Native Solution Architect - Snowflake | Onshore | 1 | Architect\nAI Native Sr Data Engineer - Frameworks | Offshore | 2 | Senior\nAI Native Testing Lead - Snowflake & Tableau | Offshore | 1 | Lead\nAI Native BI Analyst - Supply Chain | Nearshore | 1 | Mid"},
                   {"key": "platform", "label": "Platform", "kind": "text", "default": "Snowflake (Cortex Code, dynamic tables, streams and tasks, Horizon, dbt)"}]},
    "niche-brand-guardian": {"title": "Brand guardian", "stages": [4, 7, 8], "lens": "shared",
        "engine": "Audits titles and text: three-word titles, sentence case, stamps on unvalidated figures, competitor names and filler words.",
        "fields": [{"key": "content", "label": "Slides (title | subtitle | body), one per line", "kind": "lines",
                    "default": "Our Comprehensive Commercial Proposal | Three options | Option 2 saves $1.84M a year\nThree clear options | Option 2 balances scope and cost | 7.5% term discount INDICATIVE\nWhy us | Beyond the badges | Better than BigFirm Consulting with world-class accelerators"},
                   {"key": "competitors", "label": "Competitor names to block", "kind": "lines", "default": "BigFirm Consulting\nRival SI\nBoutique Data Co"}]},
    "niche-exec-offering": {"title": "Exec deck spec", "stages": [3, 4, 5, 6, 7, 8, 9], "lens": "shared",
        "engine": "Turns a response section into a slide spec (title, message subtitle, body, stamp) for the deck builder.",
        "fields": [{"key": "section", "label": "Section", "kind": "section", "default": "13"}]},
}


def _skill_ok(name: str, lens: str) -> bool:
    if name in PURSUIT or name in EXTRA:
        return allowed("skill", name, lens)
    if name in snowskills.REGISTRY:
        return allowed("skill", name, lens)
    return False


PMO_DELIVERY_SKILLS = {"plan-waves", "parallel-run", "gen-changelog", "release-notes", "gen-runbook", "gen-training", "kt-checklist"}
PMO_PURSUIT_SKILLS = {"rfp-response-orchestrator", "proposal-to-job-descriptions"}
AW_DELIVERY_SKILLS = {"gen-unit-tests", "reconcile", "parallel-run", "gen-etl-tests", "check-scd", "test-cdc", "replay-load", "compare-reports",
                      "test-rls", "test-metrics", "golden-queries", "load-test", "tune-warehouse", "lint-sql"}


def seed_skill_access(c):
    """Called from the seeder: pursuit skills follow their stages, delivery skills are delivery's
    (plus the planning and release skills the PMO uses), PMO skills are the PMO's."""
    ins = "INSERT INTO access_rule VALUES ('skill',%s,%s,%s,%s) ON CONFLICT DO NOTHING"
    for n, m in PURSUIT.items():
        lenses = ["pursuit"] + (["delivery"] if m["lens"] == "shared" else []) + (["pmo"] if n in PMO_PURSUIT_SKILLS else [])
        c.execute(ins, (n, m["title"], lenses,
                        "Shared: used in the final pursuit stages." if m["lens"] == "shared" else "Pursuit only: buyer intelligence and pricing."))
    for n, m in EXTRA.items():
        c.execute(ins, (n, m["title"], [m["kind"]], "PMO skill: runs over the delivery playbook data." if m["kind"] == "pmo"
                        else "Assurance skill: runs over the assurance workbench data."))
    for n, s in snowskills.REGISTRY.items():
        lenses = ["delivery"] + (["assurance"] if n in AW_DELIVERY_SKILLS else []) + (["pmo"] if n in PMO_DELIVERY_SKILLS else [])
        why = ("Testing and assurance skill shared with the assurance lens." if n in AW_DELIVERY_SKILLS
               else "Planning and release skill shared with the PMO." if n in PMO_DELIVERY_SKILLS else "Implementation skill for delivery personas.")
        c.execute(ins, (n, f"/{n}", lenses, why))


# ---------------------------------------------------------------------------
# Helpers over app data
# ---------------------------------------------------------------------------
def _num(v):
    if isinstance(v, (int, float)):
        return float(v)
    try:
        s = str(v).replace("$", "").replace(",", "").strip()
        return float(s[:-1]) / 100 if s.endswith("%") else float(s)
    except ValueError:
        return None


def _sheet(template_like: str, sheet: str):
    sh = one("""SELECT s.* FROM kit_sheet s JOIN kit_template t ON t.id = s.template_id
                WHERE t.file ILIKE %s AND s.name = %s""", (template_like, sheet))
    rows = q("SELECT id, data FROM kit_row WHERE sheet_id=%s ORDER BY seq, id", (sh["id"],)) if sh else []
    return sh, rows


def _save(row_id, data, who):
    one("UPDATE kit_row SET data=%s, origin='curated', updated_by=%s WHERE id=%s RETURNING 1", (json.dumps(data), who, row_id))


def _rag(v):
    return "Green" if v >= 4 else "Amber" if v >= 3 else "Red"


# ---------------------------------------------------------------------------
# Pursuit engines (each returns {"summary", "files", "notes", "tables"?})
# ---------------------------------------------------------------------------
def eng_orchestrator(params, p, session):
    code = params.get("stage") or "signal"
    require_stage(code, p)
    s = one("SELECT * FROM pursuit_stage WHERE code=%s", (code,))
    done = {r["step_index"] for r in q("SELECT step_index FROM guide_progress WHERE session_id=%s AND stage_code=%s AND done", (session, f"p-{code}"))}
    open_q = [x for i, x in enumerate(s["questions"]) if i not in done]
    ph = q("""SELECT t.file, s.name AS sheet, r.data FROM kit_row r JOIN kit_sheet s ON s.id=r.sheet_id JOIN kit_template t ON t.id=s.template_id
              WHERE t.stage_num=%s AND NOT t.sample""", (s["num"],))
    holes = {}
    for r in ph:
        n = sum(1 for v in r["data"].values() if isinstance(v, str) and PH.match(v.strip()))
        n += 1 if r["sheet"] == "Sections" and not str(r["data"].get("Response", "")).strip() else 0
        if n:
            holes[f"{r['file']} · {r['sheet']}"] = holes.get(f"{r['file']} · {r['sheet']}", 0) + n
    decisions = q("SELECT * FROM gate_decision WHERE stage_code=%s ORDER BY id DESC", (code,))
    ready = not open_q and not holes
    md = [f"# Gate readiness · {s['num']}. {s['name']} · {s['gate_code']} {s['gate']}", "",
          f"**Status:** {'READY for the gate' if ready else 'NOT READY'} · approver: {s['approvers']}", "",
          f"## Questions still open ({len(open_q)} of {len(s['questions'])})", *([f"- [ ] {x}" for x in open_q] or ["- none"]), "",
          "## Template inputs still bracketed or empty", *([f"- {k}: {v}" for k, v in holes.items()] or ["- none"]), "",
          "## Artefacts to draft", *[f"- {a}" for a in s["artefacts"]], "",
          "## Skills to use", *[f"- `{x}`" for x in s["skills"]], "",
          "## Stamps", "- ILLUSTRATIVE (designs, unconfirmed vendor capability) · INDICATIVE (money, TCO, ROI) · FOR JOINT REVIEW (MSA, security, RACI, risks)", "",
          "## Gate log", *([f"- {d['decided_at']:%Y-%m-%d} · **{d['decision']}** by {d['approver']} · {d['conditions'] or ''}" for d in decisions] or ["- no decision recorded"])]
    return {"summary": f"{s['gate_code']}: {'ready' if ready else 'not ready'} · {len(open_q)} questions open · {sum(holes.values())} inputs to fill.",
            "files": {"gate_readiness.md": "\n".join(md)}, "notes": [] if ready else ["No gate passes without a named approver; record the decision below."],
            "gate": {"stage": code, "gate_code": s["gate_code"], "ready": ready, "approvers": s["approvers"], "decisions": decisions}}


def eng_scorecard(params, p, session):
    out_notes = []
    people = []
    for sheet in ("Executive scorecard", "Evaluator scorecard"):
        sh, rows = _sheet("%proposal scorecard%", sheet)
        dims = [c for c in sh["columns"] if c.endswith("(1–5)") and not c.startswith("Overall")]
        for r in rows:
            d = r["data"]
            if not isinstance(_num(d.get("Influence (1–3)")), float):
                continue
            vals = [_num(d.get(c)) for c in dims if _num(d.get(c)) is not None]
            if not vals:
                continue
            new = round(sum(vals) / len(vals), 1)
            if params.get("new_round") == "yes":
                d["Previous overall (guardrail run)"] = d.get("Overall (1–5)")
            prev = _num(d.get("Previous overall (guardrail run)")) or new
            if d.get("Overall (1–5)") != new:
                out_notes.append(f"{d['Stakeholder']}: overall {d.get('Overall (1–5)')} → {new}")
            d.update({"Overall (1–5)": new, "RAG": _rag(new), "Change": round(new - prev, 1)})
            _save(r["id"], d, p["code"])
            people.append({"group": sheet.split()[0], "name": d["Stakeholder"], "infl": _num(d["Influence (1–3)"]), "overall": new, "change": round(new - prev, 1), "dims": [_num(d.get(c)) for c in dims]})
    def avg(g, w=False):
        ps = [x for x in people if g is None or x["group"] == g]
        if not ps:
            return 0
        return round(sum(x["overall"] * (x["infl"] if w else 1) for x in ps) / sum(x["infl"] if w else 1 for x in ps), 2)
    sh, rub = _sheet("%proposal scorecard%", "Competitor rubric")
    vend = ["Niche Consulting", "Boutique Snowflake firm", "Tier-1 consulting", "Mid-sized SI"]
    crit = [r for r in rub if isinstance(_num(r["data"].get("Weight")), float) and _num(r["data"]["Weight"]) < 1]
    tot = {v: round(sum(_num(r["data"]["Weight"]) * (_num(r["data"].get(v)) or 0) for r in crit), 2) for v in vend}
    for r in crit:
        d = r["data"]; d["Niche Consulting lead vs best rival"] = round((_num(d["Niche Consulting"]) or 0) - max(_num(d[v]) or 0 for v in vend[1:]), 2); _save(r["id"], d, p["code"])
    for r in rub:
        if r["data"].get("Criterion") == "Weighted score":
            d = r["data"]; d.update({v: tot[v] for v in vend}); d["Niche Consulting lead vs best rival"] = round(tot[vend[0]] - max(tot[v] for v in vend[1:]), 2); _save(r["id"], d, p["code"])
    _, acts = _sheet("%proposal scorecard%", "Action items")
    pending = sorted([a["data"] for a in acts if a["data"].get("Status") != "Done"], key=lambda a: -(_num(a.get("Expected lift")) or 0))
    lift = statistics.mean([_num(a.get("Expected lift")) or 0 for a in pending]) if pending else 0
    group_w = avg(None, True)
    best_rival = max(tot[v] for v in vend[1:])
    summary = {"Executive average (simple)": avg("Executive"), "Executive average (influence-weighted)": avg("Executive", True),
               "Evaluator average (simple)": avg("Evaluator"), "Evaluator average (influence-weighted)": avg("Evaluator", True),
               "Whole buying group (influence-weighted)": group_w, "Niche Consulting weighted rubric score": tot[vend[0]],
               "Best rival weighted rubric score": best_rival, "Projected group score if all actions done": round(min(5, group_w + lift), 2)}
    _, srows = _sheet("%proposal scorecard%", "Summary")
    for r in srows:
        d = r["data"]
        if d.get("Measure") in summary:
            new = summary[d["Measure"]]
            if params.get("new_round") == "yes":
                d["Previous run"] = d.get("Score (1–5)")
            d.update({"Score (1–5)": new, "RAG": _rag(new), "Change": round(new - (_num(d.get("Previous run")) or new), 2)})
            _save(r["id"], d, p["code"])
    red = [x["name"] for x in people if x["overall"] < 3]
    g7 = group_w >= 4 and not red
    md = ["# Win scorecard (internal only)", "", "| Measure | Score | RAG |", "|---|---|---|",
          *[f"| {k} | {v} | {_rag(v)} |" for k, v in summary.items()], "",
          f"**Gate G7 test:** group {group_w} (target 4.0) · in red: {', '.join(red) or 'none'} → {'PASS' if g7 else 'NOT YET'}", "",
          "## Pending actions by expected lift", "| ID | Action | Owner | Due | Lift |", "|---|---|---|---|---|",
          *[f"| {a['ID']} | {a['Action']} | {a.get('Niche Consulting owner (role)', '')} | {a.get('Due', '')} | +{a.get('Expected lift')} |" for a in pending]]
    return {"summary": f"Group {group_w} · rubric {tot[vend[0]]} vs best rival {best_rival} · {len(pending)} pending actions · G7 {'pass' if g7 else 'not yet'}.",
            "files": {"scorecard_summary.md": "\n".join(md)}, "notes": out_notes[:12]}


def eng_commercials(params, p, session):
    notes = []
    _, rc = _sheet("Commercials and value model%", "Rate card")
    rates = {r["data"]["Item"]: _num(r["data"]["Value"]) for r in rc}
    on, off = rates.get("Onsite $/hr") or 0, rates.get("Offshore $/hr") or 0
    _, opts = _sheet("Commercials and value model%", "Options")
    table = []
    for r in opts:
        d = r["data"]
        oh, fh = _num(d.get("Onsite hours")) or 0, _num(d.get("Offshore hours")) or 0
        orate, frate = _num(d.get("Onsite rate")) or on, _num(d.get("Offshore rate")) or off
        price = round(oh * orate + fh * frate, 2)
        d.update({"Onsite rate": orate, "Offshore rate": frate, "Price": price})
        _save(r["id"], d, p["code"])
        table.append((d["Option"], d.get("Scope"), oh, fh, price, round(price / (oh + fh), 2) if oh + fh else 0))
        if not oh and not fh:
            notes.append(f"{d['Option']}: hours are zero; enter loading from the resource-loading workbook.")
    _, terms = _sheet("Commercials and value model%", "Term discounts")
    trows = []
    for r in terms:
        d = r["data"]
        fx, lst = _num(d.get("Fixed discount")), _num(d.get("Annual list")) or 0
        if fx is None:
            notes.append(f"Term {d.get('Term (years)')}: fixed discount is still a placeholder.")
            fx = 0
        fl = _num(d.get("Flex discount"))
        if fl is None:
            d["Flex discount"] = f"{fx / 2 * 100:g}%"
        d["Annual net"] = round(lst * (1 - fx), 2)
        _save(r["id"], d, p["code"])
        trows.append((d.get("Term (years)"), fx, d["Annual net"]))
    _, tco = _sheet("Commercials and value model%", "TCO")
    today = target = 0
    for r in tco:
        d = r["data"]
        if d.get("Cost lever") == "Total":
            d.update({"Today (annual)": today, "Target (annual)": target, "Change": round(target - today, 2)}); _save(r["id"], d, p["code"]); continue
        a, b = _num(d.get("Today (annual)")) or 0, _num(d.get("Target (annual)")) or 0
        today += a; target += b
        d["Change"] = round(b - a, 2); _save(r["id"], d, p["code"])
    _, roi = _sheet("Commercials and value model%", "ROI")
    client_value = sum(_num(r["data"].get("Amount")) or 0 for r in roi if str(r["data"].get("Counts as client value?", "")).startswith("Yes"))
    price = sum(_num(r["data"].get("Amount")) or 0 for r in roi if r["data"].get("Counts as client value?") == "Cost")
    excluded = sum(_num(r["data"].get("Amount")) or 0 for r in roi if str(r["data"].get("Counts as client value?", "")).startswith("No"))
    savings = today - target
    payback = round(price / (savings / 12), 1) if savings > 0 and price else None
    md = ["# Commercials · INDICATIVE · FOR REVIEW: deal desk", "", f"Rate card: onsite ${on:g}/h · offshore ${off:g}/h", "",
          "| Option | Scope | Onsite h | Offshore h | Price | Blended $/h |", "|---|---|---|---|---|---|",
          *[f"| {o} | {s} | {a:g} | {b:g} | ${pr:,.0f} | {bl:g} |" for o, s, a, b, pr, bl in table], "",
          "| Term (years) | Fixed discount | Annual net |", "|---|---|---|", *[f"| {t} | {fx*100:g}% | ${n:,.0f} |" for t, fx, n in trows], "",
          f"TCO: today ${today:,.0f} → target ${target:,.0f} a year (savings ${savings:,.0f}).",
          f"ROI: client-retained value ${client_value:,.0f} vs program price ${price:,.0f}; partner/vendor-funded value shown separately (${excluded:,.0f}).",
          f"Payback: {payback} months" if payback else "Payback: needs TCO baselines and the program price (client inputs)."]
    return {"summary": f"{len(table)} options priced · TCO savings ${savings:,.0f}/yr · payback {payback or 'n/a'} months.",
            "files": {"commercials_summary.md": "\n".join(md)}, "notes": notes}


def _fixes(section):
    crit = q("SELECT * FROM rubric_criterion ORDER BY seq")
    sc = {x["criterion"]: x["score"] for x in q("SELECT * FROM section_score WHERE section_id=%s", (section["id"],))}
    met = {x["idx"]: x["met"] for x in q("SELECT * FROM section_musthave WHERE section_id=%s", (section["id"],))}
    fixes = [{"fix": f"Add must-have: {m}", "points": "uncaps 89", "blocked_by": section["blocked_by"]} for i, m in enumerate(section["must_haves"]) if not met.get(i)]
    if sc:
        lost = sorted(((c["weight"] * (4 - sc.get(c["code"], 0)) / 4, c) for c in crit), key=lambda x: -x[0])
        fixes += [{"fix": f"Lift {c['name']} ({sc.get(c['code'], 0)} → 4): {c['full_marks']}", "points": f"+{pts:g}", "blocked_by": "None"} for pts, c in lost if pts > 0][:5]
    else:
        fixes.append({"fix": section["fixes"], "points": f"baseline {section['baseline']}", "blocked_by": section["blocked_by"]})
    return fixes


def _sections(params, p):
    num = str(params.get("section") or "").strip()
    secs = q("SELECT * FROM response_section ORDER BY num")
    return [s for s in secs if not num or str(s["num"]) == num]


def eng_rubric(params, p, session):
    from .pursuit_api import _section_scores
    _, secs, overall, base = _section_scores()
    chosen = {s["num"] for s in _sections(params, p)}
    md = ["# Section rubric · ranked fixes", "", f"Overall weighted score {overall} (baseline {base}); a section passes at 90 with every must-have met.", ""]
    for s in secs:
        if s["num"] not in chosen:
            continue
        md += [f"## {s['num']}. {s['name']} · {s['current']} {'PASS' if s['passes'] else ''}", "| Fix | Points | Blocked by |", "|---|---|---|",
               *[f"| {f['fix']} | {f['points']} | {f['blocked_by']} |" for f in _fixes(s)[:3]], ""]
    return {"summary": f"Fixes ranked for {len(chosen)} section(s); overall {overall}.", "files": {"rubric_fixes.md": "\n".join(md)}, "notes": []}


def eng_loop(params, p, session):
    from .pursuit_api import _section_scores
    _, secs, overall, _ = _section_scores()
    num = int(params.get("section") or 14)
    s = next(x for x in secs if x["num"] == num)
    if p["lens"] != "pursuit" and s["owner_lens"] != "shared":
        raise HTTPException(403, f"Section '{s['name']}' is looped by the pursuit team.")
    if params.get("record") == "yes":
        n = one("SELECT COALESCE(MAX(round),0)+1 AS n FROM section_round WHERE section_id=%s", (s["id"],))["n"]
        one("INSERT INTO section_round(section_id, round, score, musts_met, fixes, recorded_by) VALUES (%s,%s,%s,%s,%s,%s) RETURNING 1",
            (s["id"], n, s["current"], all(s["musthave_met"]), params.get("fixes") or "", p["code"]))
    rounds = q("SELECT * FROM section_round WHERE section_id=%s ORDER BY round", (s["id"],))
    status = "NOT STARTED"
    if rounds:
        last = rounds[-1]
        if float(last["score"]) >= 90 and last["musts_met"]:
            status = "PASS"
        elif len(rounds) >= 4:
            status = "ESCALATE (four rounds used)"
        elif len(rounds) >= 3 and float(last["score"]) - float(rounds[-3]["score"]) < 2:
            status = "BLOCKED" if s["blocked_by"] not in ("None", "") else "PLATEAU"
        else:
            status = "IN PROGRESS"
    md = [f"# Loop log · {s['num']}. {s['name']}", "", f"Baseline {s['baseline']} · current {s['current']} · status **{status}**", "",
          "| Round | Score | Must-haves met | Fixes | By |", "|---|---|---|---|---|",
          *[f"| {r['round']} | {float(r['score']):g} | {'yes' if r['musts_met'] else 'no'} | {r['fixes']} | {r['recorded_by']} |" for r in rounds]]
    if status.startswith(("BLOCKED", "ESCALATE")):
        md += ["", f"Inputs needed: {s['blocked_by']} · insert labelled placeholders, list each input with an owner and date."]
    return {"summary": f"Section {num}: {status} after {len(rounds)} round(s).", "files": {"loop_log.md": "\n".join(md)}, "notes": [],
            "loop": {"section": num, "status": status, "rounds": len(rounds)}}


def eng_builder(params, p, session):
    from .pursuit_api import _section_scores
    _, secs, _, _ = _section_scores()
    num = int(params.get("section") or 14)
    s = next(x for x in secs if x["num"] == num)
    stamp = {13: "INDICATIVE", 5: "ILLUSTRATIVE", 4: "ILLUSTRATIVE", 3: "ILLUSTRATIVE", 10: "FOR JOINT REVIEW", 12: "FOR JOINT REVIEW", 8: "INDICATIVE"}.get(num, "as needed")
    md = [f"# Section brief · {s['num']}. {s['name']}", "", f"**Must prove:** {s['proves']}", f"**Slides:** {s['slides']} ({s['slide_count']})", f"**Stamp:** {stamp}", "",
          "## Must-haves", *[f"- [{'x' if m else ' '}] {t}" for t, m in zip(s["must_haves"], s["musthave_met"])], "",
          "## Fix list (from the rubric)", *[f"- {f['fix']} · {f['points']} · blocked by {f['blocked_by']}" for f in _fixes(s)], "",
          "## Rules", "- Titles of three words or fewer, sentence case; message in the subtitle", "- No invented client facts: use [client input] placeholders",
          "- No competitor names; flag logos", "- Keep figures consistent with the other sections", "",
          "## Hand-off", "Draft the slides with niche-exec-offering, then score with rfp-section-rubric (fresh context)."]
    return {"summary": f"Brief for section {num} with {len(s['must_haves'])} must-haves.", "files": {f"section_{num}_brief.md": "\n".join(md)}, "notes": []}


def eng_jd(params, p, session):
    text = (PURSUIT_MD / "proposal-to-job-descriptions" / "SKILL.md").read_text()
    tiers = {}
    for t in ("Onshore", "Nearshore", "Offshore"):
        m = re.search(rf"### {t} must-haves\n\n(.*?)(?=\n### )", text, re.S)
        tiers[t] = [re.sub(r"^\d+\.\s*", "", l).strip() for l in (m.group(1) if m else "").splitlines() if re.match(r"^\d+\.", l.strip())]
    out, summ = [], []
    for line in [l for l in str(params.get("roles", "")).splitlines() if l.strip()]:
        parts = [x.strip() for x in line.split("|")] + ["", "", "", ""]
        title, tier, count, band = parts[0], parts[1] or "Offshore", parts[2] or "1", parts[3] or "Senior"
        years = {"Architect": "14+", "Lead": "12+", "Senior": "10+", "Mid": "5-8", "Associate": "2-5"}.get(band, "10+")
        must = tiers.get(tier, tiers["Offshore"])
        if band in ("Mid", "Associate"):
            must = must[:3]
        arch = band == "Architect"
        out += [f"## {title} | {tier} | {count} position(s)", "",
                f"**Primary Focus:** {'Design and govern' if arch else 'Build and deliver'} the FlyHigh {params.get('platform', 'Snowflake')} workstream",
                f"**Secondary Focus:** {'Reference architecture, standards and reviews' if arch else 'Tests, harnesses and production readiness'}",
                f"**Experience:** {years} years · {band} with Snowflake and AI-assisted engineering experience", "",
                "### Key Responsibilities", f"- [6–9 action-led bullets tied to FlyHigh deliverables — draft with Claude using this skill]", "",
                "### Essential Skills", f"- **Platform Expertise:** {params.get('platform', 'Snowflake')}", "- **AI-Assisted Engineering:** Claude Code, Cortex Code",
                *(["- **Architecture & Design:** reference architectures, NFRs", "- **Governance & Security:** RBAC, masking, row access, lineage"] if arch else []), "",
                f"### Location Must-Haves [MUST-HAVE · {tier}]", *[f"- {m}" for m in must], "",
                "### Good-to-Have", "- [domain or certification]", ""]
        summ.append(f"| {title} | {tier} | {count} | {band} |")
    md = ["# Job descriptions · FlyHigh", "", "| Role | Tier | Count | Band |", "|---|---|---|---|", *summ, "", *out]
    return {"summary": f"{len(summ)} JDs drafted with tier must-haves.", "files": {"job_descriptions.md": "\n".join(md)},
            "notes": ["Responsibilities are placeholders: run in Claude mode to write them from the proposal."]}


FILLER = ["leverage", "synergy", "world-class", "cutting-edge", "best-in-class", "seamless", "robust", "holistic", "game-changing"]


def eng_brand(params, p, session):
    rows, comps = [], [c.strip() for c in str(params.get("competitors", "")).splitlines() if c.strip()]
    for i, line in enumerate([l for l in str(params.get("content", "")).splitlines() if l.strip()], 1):
        parts = [x.strip() for x in line.split("|")] + ["", ""]
        title, sub, body = parts[0], parts[1], parts[2]
        where = f"Slide {i}"
        if len(title.split()) > 3:
            rows.append(("Titles", where, f"Title has {len(title.split())} words: '{title}'", "Cut to three words; move the message to the subtitle", "Amber"))
        words = title.split()
        if len(words) > 1 and sum(1 for w in words[1:] if w[:1].isupper()) >= len(words[1:]) and title != title.upper():
            rows.append(("Case", where, f"Title Case: '{title}'", "Use sentence case", "Amber"))
        allt = f"{title} {sub} {body}"
        if re.search(r"\$\s?\d|\d+(\.\d+)?\s?%|\bROI\b|\bTCO\b|sav(e|ing)", allt, re.I) and "INDICATIVE" not in allt:
            rows.append(("Honest labels", where, "Money, percentage or savings without INDICATIVE", "Add the INDICATIVE stamp", "Red"))
        for c in comps:
            if re.search(rf"\b{re.escape(c)}\b", allt, re.I):
                rows.append(("Competitors", where, f"Names a competitor ({c})", "Remove the name; use a rival archetype internally only", "Red"))
        for f_ in FILLER:
            if f_ in allt.lower():
                rows.append(("Voice", where, f"Filler word '{f_}'", "Say what it does, with evidence", "Green"))
    md = ["# Brand audit", "", "| Rule | Where | Issue | Fix | Severity |", "|---|---|---|---|---|", *[f"| {' | '.join(r)} |" for r in rows]]
    red = sum(1 for r in rows if r[4] == "Red")
    return {"summary": f"{len(rows)} findings ({red} red).", "files": {"brand_audit.md": "\n".join(md)}, "notes": []}


def eng_deck(params, p, session):
    from .pursuit_api import _section_scores
    _, secs, _, _ = _section_scores()
    num = int(params.get("section") or 13)
    s = next(x for x in secs if x["num"] == num)
    stamp = {13: "INDICATIVE", 8: "INDICATIVE", 3: "ILLUSTRATIVE", 4: "ILLUSTRATIVE", 5: "ILLUSTRATIVE", 10: "FOR JOINT REVIEW", 12: "FOR JOINT REVIEW"}.get(num)
    slides = [{"title": " ".join(m.split()[:3]).capitalize(), "subtitle": f"[message: {m}]", "body": ["[client input]"], "stamp": stamp, "evidence": []}
              for m in s["must_haves"]]
    spec = {"section": num, "title": s["name"], "proves": s["proves"], "slides": slides}
    return {"summary": f"Spec with {len(slides)} slides for section {num}.", "files": {f"section_{num}_spec.json": json.dumps(spec, indent=2)},
            "notes": ["Titles are three-word seeds from the must-haves; rewrite them as assertions."]}


ENGINES = {"rfp-response-orchestrator": eng_orchestrator, "rfp-win-scorecard": eng_scorecard, "rfp-commercials-model": eng_commercials,
           "rfp-section-rubric": eng_rubric, "rfp-section-loop": eng_loop, "rfp-section-builder": eng_builder,
           "proposal-to-job-descriptions": eng_jd, "niche-brand-guardian": eng_brand, "niche-exec-offering": eng_deck}


# ---------------------------------------------------------------------------
# Validation and Snowflake execution
# ---------------------------------------------------------------------------
def validate_sql(name: str, body: str) -> dict:
    if not name.endswith(".sql"):
        return {}
    stripped = re.sub(r"\$\$.*?\$\$", "'BODY'", body, flags=re.S)
    stripped = "\n".join(l for l in stripped.splitlines() if not l.strip().startswith("--"))
    stmts = [s for s in stripped.split(";") if s.strip()]
    ok = passthrough = 0
    errors = []
    import logging
    logging.disable(logging.WARNING)
    for s in stmts:
        try:
            e = sqlglot.parse_one(s, read="snowflake")
            if type(e).__name__ == "Command":
                passthrough += 1
            else:
                ok += 1
        except Exception as ex:
            errors.append(str(ex).splitlines()[0][:140])
    logging.disable(logging.NOTSET)
    return {"statements": len(stmts), "parsed": ok, "snowflake_only": passthrough + len(errors), "messages": errors[:3]}


def sf_config():
    acct = os.getenv("SNOWFLAKE_ACCOUNT")
    return {"configured": bool(acct), "account": acct, "role": os.getenv("SNOWFLAKE_ROLE"), "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
            "execute_enabled": os.getenv("SNOWFLAKE_ALLOW_EXECUTE", "false").lower() == "true", "database": os.getenv("SNOWFLAKE_DATABASE")}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.get("/skills")
def list_skills(p: dict = Depends(persona)):
    lens = p["lens"]
    stages = {s["num"]: s for s in q("SELECT num, code, name FROM pursuit_stage")}
    impl = {s["code"]: s for s in q("SELECT code, seq, name FROM stage")}
    out = []
    for n, m in PURSUIT.items():
        if _skill_ok(n, lens):
            out.append({"name": n, "kind": "pursuit", "title": m["title"], "engine": m["engine"],
                        "stages": [{"num": x, "name": stages[x]["name"]} for x in m["stages"]],
                        "description": _frontmatter(n).get("description", "")})
    screens = {r["code"]: r["label"] for r in q("SELECT code, label FROM access_rule WHERE resource='screen'")}
    for n, m in EXTRA.items():
        if _skill_ok(n, lens):
            out.append({"name": n, "kind": m["kind"], "title": m["title"], "engine": m["engine"],
                        "screens": [{"code": x, "label": screens.get(x, x)} for x in m["screens"]],
                        "description": _frontmatter(n).get("description", "")})
    for n, s in snowskills.REGISTRY.items():
        if _skill_ok(n, lens):
            st = impl.get(s.stage, {})
            out.append({"name": n, "kind": "delivery", "title": s.title, "description": s.description, "agent": s.agent,
                        "stage": s.stage, "stage_name": st.get("name"), "stage_seq": st.get("seq"), "package": s.package, "snowflake": s.snowflake})
    return {"skills": out, "llm": llm.available(), "llm_status": llm.status(), "snowflake": sf_config()}


def _frontmatter(n):
    t = _md_path(n).read_text()
    m = re.search(r'description:\s*"(.*?)"', t)
    return {"description": m.group(1) if m else ""}


@router.get("/skills/{name}")
def get_skill(name: str, p: dict = Depends(persona)):
    if not _skill_ok(name, p["lens"]):
        raise HTTPException(403, f"Skill '{name}' is not available in the {p['lens']} lens.")
    runs = q("SELECT id, mode, summary, persona, created_at FROM skill_run WHERE skill=%s ORDER BY id DESC LIMIT 10", (name,))
    if name in PURSUIT:
        m = PURSUIT[name]
        md = (PURSUIT_MD / name / "SKILL.md").read_text()
        fields = m["fields"]
        if name == "rfp-response-orchestrator":
            ok = allowed_codes("pursuit_stage", p["lens"])
            fields = [{**fields[0], "options": [s["code"] for s in q("SELECT code FROM pursuit_stage ORDER BY num") if s["code"] in ok],
                       "default": "signal" if "signal" in ok else "delivery"}]
        return {"name": name, "kind": "pursuit", "title": m["title"], "engine": m["engine"], "skill_md": md, "fields": fields, "runs": runs}
    if name in EXTRA:
        m = EXTRA[name]
        return {"name": name, "kind": m["kind"], "title": m["title"], "engine": m["engine"], "screens": m["screens"],
                "skill_md": _md_path(name).read_text(), "fields": m["fields"], "runs": runs}
    s = snowskills.REGISTRY[name]
    return {"name": name, "kind": "delivery", "title": s.title, "description": s.description, "agent": s.agent, "stage": s.stage,
            "gate": s.gate, "package": s.package, "snowflake": s.snowflake, "skill_md": render_skill_md(s),
            "fields": [{"key": f.key, "label": f.label, "kind": f.kind, "default": f.default, "options": f.options} for f in s.fields], "runs": runs}


class RunIn(BaseModel):
    params: dict[str, Any] = {}
    mode: str = "engine"          # engine | prompt | claude
    session_id: str = "anon"
    instruction: str | None = None


@router.post("/skills/{name}/run")
def run_skill(name: str, body: RunIn, p: dict = Depends(persona)):
    if not _skill_ok(name, p["lens"]):
        raise HTTPException(403, f"Skill '{name}' is not available in the {p['lens']} lens.")
    if name in PURSUIT:
        params = {f["key"]: f.get("default", "") for f in PURSUIT[name]["fields"]}
        params.update({k: v for k, v in (body.params or {}).items() if v not in (None, "")})
        res = ENGINES[name](params, p, body.session_id)
        md_text = (PURSUIT_MD / name / "SKILL.md").read_text()
    elif name in EXTRA:
        params = {f["key"]: f.get("default", "") for f in EXTRA[name]["fields"]}
        params.update({k: v for k, v in (body.params or {}).items() if v not in (None, "")})
        res = EXTRA[name]["run"](params, p, body.session_id)
        md_text = _md_path(name).read_text()
    else:
        res = snowskills.run(name, body.params)
        md_text = render_skill_md(snowskills.REGISTRY[name])
    res["validation"] = {f: v for f, b in res["files"].items() if (v := validate_sql(f, b))}
    context = "\n\n".join(f"### {f}\n```\n{b[:6000]}\n```" for f, b in res["files"].items())
    prompt = (f"Use the `{snowskills.REGISTRY[name].package if name in snowskills.REGISTRY else name}` skill.\n\n"
              f"Inputs:\n```json\n{json.dumps(body.params or {}, indent=2, default=str)[:4000]}\n```\n\n"
              f"Deterministic draft from FlyHigh Navigator:\n{context}\n\n"
              f"{body.instruction or 'Review the draft against the skill, fill anything marked as a placeholder only where the inputs support it, and list what still needs a human decision.'}")
    res["prompt"] = prompt
    if body.mode == "claude":
        try:
            res["claude"] = llm.complete(md_text, prompt)
        except Exception as e:
            res["claude_error"] = str(e)
    row = one("""INSERT INTO skill_run(skill, kind, persona, mode, params, summary, output) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
              (name, "pursuit" if name in PURSUIT else EXTRA[name]["kind"] if name in EXTRA else "delivery", p["code"], body.mode, json.dumps(body.params, default=str), res.get("summary", ""),
               json.dumps({k: v for k, v in res.items() if k != "prompt"}, default=str)))
    res["run_id"] = row["id"]
    return res


@router.get("/skills/runs/{rid}/zip")
def run_zip(rid: int, persona_code: str):
    p = persona(persona_code)
    r = one("SELECT * FROM skill_run WHERE id=%s", (rid,))
    if not r or not _skill_ok(r["skill"], p["lens"]):
        raise HTTPException(404)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f, b in r["output"]["files"].items():
            z.writestr(f, b)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{r["skill"]}-run-{rid}.zip"'})


@router.get("/skills/{name}/package")
def skill_package(name: str, persona_code: str):
    """Download the skill as a .skill package (zip with SKILL.md, scripts and example params)."""
    p = persona(persona_code)
    if not _skill_ok(name, p["lens"]):
        raise HTTPException(403)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        if name in PURSUIT or name in EXTRA:
            z.writestr(f"{name}/SKILL.md", _md_path(name).read_text())
            fname = f"{name}.skill"
        else:
            from snowskills.package import add_to_zip
            fname = add_to_zip(z, snowskills.REGISTRY[name])
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{fname}"'})


class GateIn(BaseModel):
    stage: str
    approver: str
    decision: str
    conditions: str | None = None


@router.post("/skills/gate-decision")
def gate_decision(body: GateIn, p: dict = Depends(persona)):
    require_stage(body.stage, p)
    if not body.approver.strip():
        raise HTTPException(400, "A named approver is required: agents draft, people decide.")
    s = one("SELECT gate_code FROM pursuit_stage WHERE code=%s", (body.stage,))
    one("""INSERT INTO gate_decision(stage_code, gate_code, approver, decision, conditions, recorded_by) VALUES (%s,%s,%s,%s,%s,%s) RETURNING 1""",
        (body.stage, s["gate_code"], body.approver.strip(), body.decision, body.conditions, p["code"]))
    return q("SELECT * FROM gate_decision WHERE stage_code=%s ORDER BY id DESC", (body.stage,))


@router.get("/snowflake/status")
def sf_status(p: dict = Depends(persona)):
    return sf_config()


class ExecIn(BaseModel):
    file: str
    confirm: bool = False


@router.post("/skills/runs/{rid}/execute")
def execute(rid: int, body: ExecIn, p: dict = Depends(persona)):
    if p["lens"] != "delivery":
        raise HTTPException(403, "Only delivery personas can execute against Snowflake.")
    cfg = sf_config()
    if not cfg["configured"] or not cfg["execute_enabled"]:
        raise HTTPException(400, "Snowflake execution is off. In .env set SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PRIVATE_KEY_FILE "
                                 "(a key in ./secrets, mounted read-only) or SNOWFLAKE_PASSWORD, SNOWFLAKE_ROLE, SNOWFLAKE_WAREHOUSE and "
                                 "SNOWFLAKE_ALLOW_EXECUTE=true, then docker compose up -d. Point it at a DEV account.")
    if not body.confirm:
        raise HTTPException(400, "Confirm that a person reviewed this SQL.")
    r = one("SELECT * FROM skill_run WHERE id=%s", (rid,))
    if not r or r["kind"] != "delivery" or not body.file.endswith(".sql") or body.file not in r["output"]["files"]:
        raise HTTPException(404)
    try:
        import snowflake.connector
    except ImportError:
        raise HTTPException(500, "snowflake-connector-python is missing from the image; rebuild with docker compose build.")
    kw = {"account": cfg["account"], "user": os.getenv("SNOWFLAKE_USER"), "role": cfg["role"], "warehouse": cfg["warehouse"]}
    if os.getenv("SNOWFLAKE_PRIVATE_KEY_FILE"):
        kw.update(authenticator="SNOWFLAKE_JWT", private_key_file=os.getenv("SNOWFLAKE_PRIVATE_KEY_FILE"),
                  private_key_file_pwd=os.getenv("SNOWFLAKE_PRIVATE_KEY_FILE_PWD"))
    else:
        kw["password"] = os.getenv("SNOWFLAKE_PASSWORD")
    results = []
    con = snowflake.connector.connect(**kw)
    try:
        con.cursor().execute("ALTER SESSION SET QUERY_TAG = 'flyhigh-navigator'")
        for cur in con.execute_string(r["output"]["files"][body.file], remove_comments=True):
            rows = cur.fetchmany(20) if cur.description else []
            results.append({"query_id": cur.sfqid, "rows": [list(map(str, x)) for x in rows], "columns": [d[0] for d in (cur.description or [])]})
    except Exception as e:
        results.append({"error": str(e)[:500]})
    finally:
        con.close()
    one("INSERT INTO skill_execution(run_id, file, persona, result) VALUES (%s,%s,%s,%s) RETURNING 1", (rid, body.file, p["code"], json.dumps(results)))
    return {"results": results}
