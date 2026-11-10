"""Conversational guide.

Works offline with intent rules + retrieval over the Postgres `search_index` view.
If ANTHROPIC_API_KEY is set, the retrieved context is passed to Claude to phrase the answer.
"""
import json
import os
import re

from . import llm
from .access import allowed, allowed_codes
from .db import one, q

STAGE_WORDS = {
    "discover": ["discover", "discovery", "prd", "requirement", "mobilize", "g1"],
    "design": ["design", "architecture", "scope.yaml", "g2", "adr"],
    "decompose": ["decompose", "jira", "backlog", "change spec"],
    "foundation": ["foundation", "rbac", "zone", "masking", "scim", "auth", "encryption", "terraform"],
    "harness": ["harness", "data product", "nine agents", "9 agents", "hir", "customer 360"],
    "migration": ["migration", "migrate", "convert", "conversion", "snowconvert", "aim", "odi", "pl/sql", "cut-over", "cutover"],
    "bi": ["bi ", "bi modern", "tableau", "report", "oac", "power bi", "klipfolio", "rationaliz"],
    "assurance": ["assurance", "test", "qa", "reconcil", "uat", "sit", "performance", "golden quer"],
    "release": ["release", "promot", "ci/cd", "changelog", "dev → stage", "deploy", "g3", "lint"],
    "monitor": ["monitor", "hypercare", "operate", "operations", "runbook", "handover", "training", "observab"],
}
STOP = set("a an the of to in on for and or is are what which who how do does i we my our me it this that with by be can show tell about".split())

SUGGEST_DEFAULT = ["Where do I start?", "Show the agents in Platform migration",
                   "Which KPIs matter to executives?", "Show the customer journey"]

PURSUIT_WORDS = {
    "signal": ["signal", "qualify", "bid decision", "no-bid", "bid memo", "opportunity brief", "g0"],
    "decode": ["decode", "rfp requirement", "compliance matrix", "clarification", "evaluation criteria"],
    "win": ["win strateg", "win theme", "why niche consulting", "competitor", "stakeholder map", "beyond the badges"],
    "solution": ["solution design", "solution review", "target state", "current state", "system of record"],
    "delivery": ["delivery plan", "effort", "resource loading", "raci", "job description", "zero variance", "g4"],
    "commercials": ["commercial", "pricing", "rate card", "tco", "roi", "discount", "deal review", "g5"],
    "trust": ["trust", "security", "msa", "legal review", "g6"],
    "redteam": ["red team", "brand audit", "deck sweep", "assemble", "g7"],
    "submit": ["submit", "orals", "q&a", "retrospective", "submission", "g8"],
}
SUGGEST = {
    "pursuit": ["How do we qualify a bid?", "What does gate G5 need?", "Show the win score", "Which sections are below 90?"],
    "assurance": ["Where do I start?", "Which tests failed?", "What does the latest change impact?", "Show open defects"],
    "pmo": ["How ready is Track A?", "Estimate the effort", "Show the top risks", "Which KPIs are amber or red?"],
    "delivery": ["Where do I start?", "What does the delivery plan stage need?", "Show the agents in Platform migration", "Which sections can I score?"],
}
IMPL_KINDS = {"stage", "agent", "skill", "tool", "framework", "snowflake"}


def _lens_ok(resource, code, lens):
    return allowed(resource, code, lens)


def _pursuit_reply(code, lens):
    s = one("SELECT * FROM pursuit_stage WHERE code=%s", (code,))
    if not _lens_ok("pursuit_stage", code, lens):
        shared = q("""SELECT ps.num, ps.name FROM pursuit_stage ps JOIN access_rule a ON a.resource='pursuit_stage' AND a.code=ps.code
                      WHERE %s = ANY(a.lenses) ORDER BY ps.num""", (lens,))
        return {"reply": f"**{s['num']}. {s['name']}** (gate {s['gate_code']}) stays with the pursuit lens, so your lens can't open it. "
                         "You share these pursuit stages: " + ", ".join(f"{x['num']}. {x['name']}" for x in shared) + ".",
                "cards": [_card("lifecycle", "Lifecycle overview", "See what your lens can open", "lifecycle", "")], "suggestions": SUGGEST[lens][:2]}
    lines = [f"**Pursuit stage {s['num']} · {s['name']}** — gate **{s['gate_code']} {s['gate']}**, approved by {s['approvers']}.",
             s["purpose"], "",
             "**Artefacts:** " + ", ".join(s["artefacts"]),
             "**Skills:** " + " ".join(f"`{k}`" for k in s["skills"]),
             "**Questions to close before the gate:**"] + [f"- {x}" for x in s["questions"]]
    if s["extra"].get("audience") == "shared":
        lines.append(f"\n*Shared with delivery{' and the PMO' if _lens_ok('pursuit_stage', code, 'pmo') else ''}:* {s['extra'].get('shared_reason', '')}")
    return {"reply": "\n".join(lines), "cards": [_card("pursuit", f"{s['num']} · {s['name']}", f"{s['gate_code']} · {s['gate']}", "pursuit", code)],
            "suggestions": ["What's next?", "Which templates help here?"]}


def _tokens(s):
    return [t for t in re.findall(r"[a-z0-9/\-]+", s.lower()) if t not in STOP and len(t) > 1]


def _stage(code):
    s = one("SELECT * FROM stage WHERE code=%s", (code,))
    if not s:
        return None
    s["components"] = q("""SELECT c.kind, c.name, c.category, p.name AS parent FROM stage_component sc
                           JOIN component c ON c.id=sc.component_id LEFT JOIN component p ON p.id=sc.parent_id
                           WHERE sc.stage_id=%s ORDER BY sc.seq""", (s["id"],))
    return s


def _stage_reply(s):
    agents = [c for c in s["components"] if c["kind"] == "agent"]
    skills = sorted({c["name"] for c in s["components"] if c["kind"] == "skill"})
    tools = sorted({c["name"] for c in s["components"] if c["kind"] == "tool"})
    sf = sorted({c["name"] for c in s["components"] if c["kind"] == "snowflake"})
    lines = [f"**Step {s['seq']} · {s['name']}** — led by {s['lead_role']} ({s['mode']}).", s["summary"], ""]
    lines.append("**Agents:** " + ", ".join(a["name"] for a in agents))
    if skills:
        lines.append("**Skills:** " + " ".join(f"`{k}`" for k in skills))
    if tools:
        lines.append("**Tools:** " + ", ".join(tools))
    if sf:
        lines.append("**Snowflake:** " + ", ".join(sf[:6]))
    lines.append(f"**Gate:** {s['gate']}")
    return "\n".join(lines)


def _card(kind, title, subtitle, view, ref):
    return {"kind": kind, "title": title, "subtitle": subtitle, "view": view, "ref": ref}


def _next_stage(code):
    s = one("SELECT seq FROM stage WHERE code=%s", (code,))
    if not s:
        return None
    return one("SELECT code FROM stage WHERE seq>%s ORDER BY seq LIMIT 1", (s["seq"],))


PMO_KIND_SCREEN = {"pmo_kpi": "kpis", "pmo_raid": "governance", "pmo_usecase": "usecases", "aw_case": "aw_design", "aw_defect": "aw_analytics", "aw_test_type": "aw_testmap"}


def assurance_answer(m: str, context: dict):
    """Intent rules for the assurance lens, answered from the assurance workbench tables."""
    from . import assurance_api as A
    card = lambda v, t, s: _card(v, t, s, v, "")
    if re.search(r"\b(hi|hello|help|start|begin|get started|where do i)\b", m) and len(m) < 60:
        s = A.summary(A.DB)
        return {"reply": "You're in the **assurance lens**: the assurance workbench for FlyHigh, in four parts.\n"
                         "- **Design:** generate test cases from user stories or documents, synthetic test data and keyword-driven scripts.\n"
                         "- **Execution:** engines, devices, releases and test plans; run them with self-healing and failure analysis.\n"
                         "- **Analytics:** coverage, results, hotspots, defects and the impact × likelihood grid.\n"
                         "- **Maintenance:** map tests to code and pick the regression suite for each change.\n\n"
                         f"Right now: {s['stories']} stories, {s['covered']} covered; latest results {s['passed']} passed, {s['failed']} failed, {s['skipped']} skipped; "
                         f"{sum(1 for d in s['defects'] if d['status'] != 'Closed')} open defects.",
                "cards": [card("aw_overview", "Assurance overview", "Start here"), card("aw_design", "Design", "Generate test cases")],
                "suggestions": SUGGEST["assurance"]}
    if re.search(r"lakehouse|test map|test strategy|which tests|tests? (for|across|needed|required)|layer|gap", m):
        from .lakehouse_tests import LAYERS
        tm = A.testmap(A.DB)
        hit = [n for n, name in LAYERS.items() if any(w in m for w in name.lower().replace(" and ", " ").split() if len(w) > 4)]
        types = [t for t in tm["types"] if not hit or t["layer"] in hit]
        head = (f"Tests for **{', '.join(LAYERS[n] for n in hit)}**:" if hit else
                "The lakehouse test map covers six platform layers and three cross-cutting disciplines: " + ", ".join(f"{t} {v}" for t, v in tm["counts"].items()) + ".")
        return {"reply": head + "\n" + "\n".join(f"- **{t['code']} {t['name']}** ({t['status']}, {t['cases']} cases): {t['what']}" for t in types[:14]),
                "cards": [card("aw_testmap", "Lakehouse test map", "Coverage by layer")], "suggestions": ["Which tests failed?"]}
    if re.search(r"fail|flaky|hotspot|root cause", m):
        s = A.summary(A.DB)
        return {"reply": "Most-failed test cases:\n" + "\n".join(f"- **{d['key']}** {d['title'][:70]} — {d['failure_rate']}% ({d['root_cause'] or 'n/a'}): {d['resolution'] or ''}" for d in s["most_failed"][:8])
                         + f"\n\nHotspots: {len(s['hotspots']['critical'])} critical, {len(s['hotspots']['flaky'])} flaky, {len(s['hotspots']['stable'])} stable.",
                "cards": [card("aw_analytics", "Assurance analytics", "Test case performance")], "suggestions": ["Show open defects"]}
    if re.search(r"defect|bug", m):
        s = A.summary(A.DB)
        op = [d for d in s["defects"] if d["status"] != "Closed"]
        return {"reply": f"{len(op)} open defects ({', '.join(f'{k} {v}' for k, v in s['severity'].items())} overall):\n" +
                         "\n".join(f"- **{d['key']}** {d['severity']} · {d['title'][:80]}" for d in op[:10]),
                "cards": [card("aw_analytics", "Defect impact analysis", "By severity and suite")], "suggestions": ["Which tests failed?"]}
    if re.search(r"impact|regression|chang|diff|code map|mapping", m):
        mods = A.DB.q("SELECT id, path FROM aw_module WHERE changed")
        rows = A.impact(A.DB, [x["id"] for x in mods]) if mods else []
        return {"reply": ("Changed modules: " + ", ".join(f"`{x['path']}`" for x in mods) + f". {len(rows)} test cases are impacted; run these first:\n" +
                          "\n".join(f"- **{r['key']}** {r['title'][:70]} (risk {r['risk']}, via {r['module']})" for r in rows[:8])) if mods
                         else "No modules are marked as changed. Paste your changed files in **Maintenance → Impact analysis**.",
                "cards": [card("aw_maintenance", "Assurance maintenance", "Impact analysis")], "suggestions": []}
    if re.search(r"coverage|covered|ready|readiness|summary|report", m):
        s = A.summary(A.DB)
        return {"reply": f"{s['covered']} of {s['stories']} user stories have test cases; {s['tested']} have executed results. "
                         f"Latest: {s['passed']} passed, {s['failed']} failed, {s['skipped']} skipped, {s['self_healed']} self-healed. "
                         f"{s['features_ready']} of {s['features_total']} features have no failures.",
                "cards": [card("aw_analytics", "Test report summarizer", "Coverage and readiness")], "suggestions": ["Which tests failed?"]}
    if re.search(r"test data|synthetic|mask", m):
        return {"reply": "The **test data generator** builds valid, boundary, invalid and masked rows from a data-model entity, pasted DDL or a CSV header, with Snowflake INSERT SQL and the data-quality checks the invalid rows must fail.",
                "cards": [card("aw_design", "Design", "Test data generator")], "suggestions": []}
    if re.search(r"script|keyword|automat|framework", m):
        return {"reply": "The **test script generator** turns a test case into a keyword-driven pytest (or a BDD feature) over reusable components: Login, NavigateTo, ApplyFilter, ReadKpiTile, RunSql, CompareToLegacy, AssertRowAccess, AssertMasked, MeasureLatency, AskCortex and AssertDenied.",
                "cards": [card("aw_design", "Design", "Test script generator")], "suggestions": []}
    if re.search(r"engine|device|release|plan|execut|run|schedule|ci/cd|self-heal", m):
        cy = A.DB.q("SELECT name, passed, failed, skipped, self_healed, engine FROM aw_cycle ORDER BY id DESC LIMIT 4")
        return {"reply": "Recent execution cycles:\n" + "\n".join(f"- **{c['name']}** on {c['engine']}: {c['passed']} passed, {c['failed']} failed, {c['skipped']} skipped, {c['self_healed']} self-healed" for c in cy)
                         + "\n\nExecutions run on the built-in simulator until a real engine is connected.",
                "cards": [card("aw_execution", "Assurance execution", "Plans and cycles")], "suggestions": []}
    if re.search(r"test case|generate|user stor", m):
        return {"reply": "The **test case generator** turns user stories (one case per acceptance criterion plus a negative case) or pasted FSD/BRD lines, screens or API endpoints into a versioned suite, classified as functional, data, security, performance, UI or API.",
                "cards": [card("aw_design", "Design", "Test case generator")], "suggestions": []}
    return None
ARCH_WORDS = {"migrate": ["dmlc", "warehouse migration", "legacy warehouse", "migration archetype"],
              "product": ["dplc", "data product", "medallion"],
              "bi": ["bmlc", "bi and semantic", "semantic modern", "bi modern"],
              "ai": ["ailc", "cortex ai", "agents archetype", "cortex agent"]}


def pmo_answer(m: str, context: dict):
    """Intent rules for the PMO lens, answered from the delivery playbook and the pmo_* working tables."""
    from . import pmo_api as P
    if re.search(r"\b(hi|hello|help|start|begin|get started|where do i)\b", m) and len(m) < 60:
        st = P.doc("stages")
        return {"reply": "You're in the **PMO lens**: the program office for FlyHigh, run on the AI Native Delivery Playbook. "
                         "Agents convert, build and test; named people own G1 (PRD), G2 (design), G3 (verified in production) and every reconciliation variance.\n" +
                         "\n".join(f"- {i + 1}. **{s['name']}**" for i, s in enumerate(st)) +
                         "\n\nStart with the **Delivery playbook** primer, score each track in the **Readiness scorecard**, then plan waves back from the licence dates. "
                         "Track value in the **KPI scorecard** and run steering from **Governance and RAID**.",
                "cards": [_card("playbook", "Delivery playbook", "Primer and archetypes", "playbook", ""),
                          _card("readiness", "Readiness scorecard", "Qualify each track", "readiness", "")],
                "suggestions": SUGGEST["pmo"]}
    if re.search(r"readiness|ready|qualif", m):
        rows = [P.readiness_score(t) for t in P.tracks()]
        lines = []
        for r in rows:
            lag = [d for d in r["dims"] if d["lagging"]]
            lines.append(f"- **{r['track']}**: {r['overall']}% · {r['band']}" + (f" · lagging: {', '.join(d['dim'] for d in lag)}" if lag else ""))
        first_lag = next((d for r in rows for d in r["dims"] if d["lagging"]), None)
        tail = f"\n\nFirst remediation for **{first_lag['dim']}**:\n" + "\n".join(f"- {x}" for x in first_lag["remedy"][:3]) if first_lag else ""
        return {"reply": "Readiness on 17 questions across five weighted dimensions (75%+ ready, 50%+ ready with remediation):\n" + "\n".join(lines) + tail,
                "cards": [_card("readiness", "Readiness scorecard", "Score and remediate", "readiness", "")],
                "suggestions": ["Run the steering pack", "Show the top risks"]}
    if re.search(r"estimat|effort|person-day|person day|\bfte\b|unit effort|sizing", m):
        r = P.estimate({})
        return {"reply": f"Unit-effort model with the FlyHigh defaults: **{r['total_pd']:,} person-days**, {r['person_months']} person-months, "
                         f"**{r['avg_fte']} average FTE** over {int(r['inputs']['months'])} months. Without the wave speed-up it would be {r['without_speedup_pd']:,} PD.\n"
                         + "\n".join(f"- {c}: {v['objects']:.0f} objects → {v['with_speedup']:,} PD" for c, v in r["components"].items())
                         + f"\n- Frameworks {r['frameworks_pd']:,} PD · discovery {r['discovery_pd']:,} PD\n\n{r['note']}",
                "cards": [_card("estimator", "Unit-effort estimator", "Try your own counts", "estimator", "")], "suggestions": ["Which use cases go in the pilot?"]}
    if re.search(r"\brisk|\braid\b|issue|dependenc|assumption|blocker", m):
        rows = q("SELECT * FROM pmo_raid WHERE status <> 'Closed' ORDER BY CASE severity WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END, id LIMIT 8")
        return {"reply": "Open RAID items, highest severity first:\n" + "\n".join(f"- **{r['kind']} · {r['severity']}** — {r['title']} ({r['owner'] or 'unassigned'}, {r['due'] or 'no date'})" for r in rows),
                "cards": [_card("governance", "Governance and RAID", "Add or update items", "governance", "")], "suggestions": ["Run the steering pack"]}
    if re.search(r"steering|status report|status pack", m):
        return {"reply": "The **steering pack** skill compiles readiness per track, the KPI scorecard by RAG, top RAID items, decisions needed and playbook progress. "
                         "Monthly steering covers milestones, benefits and licence retirement; RAID is weekly, gate reviews bi-weekly.",
                "cards": [_card("skill", "Steering pack", "Run it in the skills studio", "skills", "pmo-steering-pack")], "suggestions": ["Which KPIs are amber or red?"]}
    if re.search(r"\bkpi|scorecard|metric|amber|\bred\b|green|measure", m) and not re.search(r"otif|dwell|fact|warehouse kpi|executive", m):
        rows = q("SELECT * FROM pmo_kpi ORDER BY CASE status WHEN 'red' THEN 0 WHEN 'amber' THEN 1 WHEN 'green' THEN 2 ELSE 3 END, seq")
        flagged = [r for r in rows if r["status"] in ("red", "amber")]
        return {"reply": "Measure AI-native delivery by trusted numbers and legacy retired on date, not by the volume of converted code.\n\n"
                         + (f"{len(flagged)} metrics need attention:\n" + "\n".join(f"- **{r['name']}** {r['actual']} vs target {r['target']} ({r['status'].upper()}) {r['note'] or ''}" for r in flagged)
                            if flagged else "All tracked metrics are green."),
                "cards": [_card("kpis", "KPI scorecard", f"{len(rows)} metrics", "kpis", "")], "suggestions": ["Run the steering pack"]}
    if re.search(r"raci|accountab|who approves|team|pod|topology|roles?\b", m):
        t = P.doc("team")
        return {"reply": "One AI Native core pod (~6 FTE) builds the frameworks once; AI-assisted track pods (~3.5 FTE each) reuse them every wave. "
                         "Named humans are accountable at three gates.\n" + "\n".join(f"- **{x['principle']}**: {x['detail']}" for x in t["topology"]) +
                         "\n\nTeam sizes: " + ", ".join(f"{a['name']} {a['size']}" for a in t["archetypes"]) + ".",
                "cards": [_card("team", "Team and RACI", "Topology, roles, RACI", "team", "")], "suggestions": ["Who approves G3?"]}
    if re.search(r"responsible ai|\brai\b|governance|guardrail|pillar|nist|eu ai act|compliance", m):
        r = P.doc("rai")
        return {"reply": r["principle"] + "\n\n" + "\n".join(f"- **{x['pillar']}**: {x['control']}" for x in r["pillars"]) + f"\n\nStandards: {r['standards']}.",
                "cards": [_card("governance", "Governance and RAID", "Responsible AI controls", "governance", "")], "suggestions": ["Show the top risks"]}
    if re.search(r"use case|use-case|prioriti|where .*agent|automation potential|pilot candidate", m):
        rows = sorted((P.uc_score(u) for u in q("SELECT * FROM pmo_usecase")), key=lambda u: -u["score"])
        return {"reply": "Top AI use cases by weighted score (value 30, repeatability 20, feasibility 20, trust 15, automation 15):\n" +
                         "\n".join(f"- **{u['score']}** {u['activity']} ({u['archetype']} · {u['lane']})" for u in rows[:8]),
                "cards": [_card("usecases", "AI use-case matrix", "Rate and rank", "usecases", "")], "suggestions": ["Estimate the effort"]}
    for key, words in ARCH_WORDS.items():
        if any(w in m for w in words):
            a = next(x for x in P.doc("archetypes") if x["key"] == key)
            return {"reply": f"**{a['title']}** ({a['lc']}) — {a['summary']}\n\n**Method:** {a['method']}\n\n**Artefacts:** " + ", ".join(a["artefacts"]) +
                             f"\n\n**FlyHigh:** {a['example']}",
                    "cards": [_card("roadmap", a["title"], "Execute activities", "roadmap", key)], "suggestions": ["How ready is Track A?"]}
    if re.search(r"\bplan\b|planning|setup|set up|onboard|sprint 0|wave plan|optimi", m):
        ob = P.doc("onboarding")
        return {"reply": "From kickoff to transition in nine phases:\n" + "\n".join(f"- **{o['phase']}** ({o['timeline']}): {o['activities']} → {o['output']}" for o in ob) +
                         "\n\nThe Plan and execute screen holds the 13 planning steps, 7 setup steps and the activities per archetype.",
                "cards": [_card("roadmap", "Plan and execute", "Steps and checklists", "roadmap", "")], "suggestions": ["Estimate the effort"]}
    if re.search(r"primer|shift|why .*chang|ai-native|ai native|mindset", m):
        pr = {x["code"]: x for x in P.doc("primer")}
        return {"reply": pr["shifts"]["body"][:1500], "cards": [_card("playbook", "Delivery playbook", "Primer", "playbook", "")], "suggestions": []}
    return None


def answer(message: str, context: dict | None = None, lens: str = "delivery"):
    context = context or {}
    m = message.lower().strip()
    cards, suggestions = [], []
    impl_ok = _lens_ok("screen", "workflow", lens)

    # 0. Pursuit lens orientation: the pursuit lifecycle
    if lens == "pursuit" and re.search(r"\b(hi|hello|help|start|begin|get started|where do i)\b", m) and len(m) < 60:
        st = q("SELECT num, name, gate_code, gate FROM pursuit_stage ORDER BY num")
        return {"reply": "You're in the **pursuit lens**. A pursuit runs in nine gated stages, from RFP signal to orals:\n" +
                         "\n".join(f"- {x['num']}. {x['name']} — **{x['gate_code']}** {x['gate']}" for x in st) +
                         "\n\nAgents draft, people decide: no gate passes without a named approver. Start with **Signal and qualify**, "
                         "use the pursuit kit for each stage's template, and track the win score and section rubric as you go.",
                "cards": [_card("pursuit", "1 · Signal and qualify", "Start here", "pursuit", "signal")],
                "suggestions": SUGGEST["pursuit"]}

    # Assurance lens: the assurance workbench
    if lens == "assurance":
        r = assurance_answer(m, context)
        if r:
            return r

    # PMO lens: the delivery playbook
    if lens == "pmo":
        r = pmo_answer(m, context)
        if r:
            return r

    # Pursuit "next" when on a pursuit stage
    if re.search(r"\b(next|what now|then what|after this)\b", m) and context.get("pstage"):
        cur = one("SELECT num FROM pursuit_stage WHERE code=%s", (context["pstage"],))
        nxt = cur and one("SELECT code FROM pursuit_stage WHERE num>%s ORDER BY num LIMIT 1", (cur["num"],))
        if nxt:
            return _pursuit_reply(nxt["code"], lens)
        return {"reply": "Gate **G8** is the last pursuit gate. After award, the plan hands over to implementation **Discover**" +
                         ("." if impl_ok else ", which the delivery lens runs."),
                "cards": [_card("lifecycle", "Lifecycle overview", "Pursuit → implementation", "lifecycle", "")], "suggestions": []}

    # Win room, rubric and kit intents
    if re.search(r"win score|scorecard|buying group|stakeholder score|evaluator", m):
        if not _lens_ok("screen", "winroom", lens):
            return {"reply": "The win room (buyer and evaluator scorecard, competitor rubric) stays with the **pursuit lens**.", "cards": [], "suggestions": SUGGEST[lens][:2]}
        summ = q("""SELECT r.data FROM kit_row r JOIN kit_sheet s ON s.id=r.sheet_id WHERE s.name='Summary' ORDER BY r.seq LIMIT 8""")
        return {"reply": "Current FlyHigh scorecard:\n" + "\n".join(f"- {x['data']['Measure']}: **{x['data']['Score (1–5)']}** ({x['data']['RAG']})" for x in summ) +
                         "\n\nGate G7 needs a buying-group score of 4.0 or higher with no stakeholder in red.",
                "cards": [_card("winroom", "Win room", "Scorecard and actions", "winroom", "")], "suggestions": ["Which sections are below 90?"]}
    if re.search(r"rubric|section|below 90|must-have|must have|score .*section", m) and _lens_ok("screen", "quality", lens):
        rows = q("SELECT num, name, baseline, missing, owner_lens FROM response_section ORDER BY baseline")
        mine = [r for r in rows if lens == "pursuit" or r["owner_lens"] == "shared"]
        reply = ("Sections score on 10 weighted criteria (points = weight × score ÷ 4); 90 passes only with every must-have met, and a missing must-have caps the section at 89.\n"
                 "Lowest baselines:\n" + "\n".join(f"- {r['num']}. **{r['name']}** {r['baseline']} — missing: {r['missing']}" for r in rows[:6]))
        if lens == "delivery":
            reply += "\n\nIn the delivery lens you score the shared sections: " + ", ".join(r["name"] for r in mine) + "."
        return {"reply": reply, "cards": [_card("quality", "Response quality", "Section rubric", "quality", "")], "suggestions": []}
    if re.search(r"template|kit|workbook|aid", m):
        ok = list(allowed_codes("pursuit_stage", lens))
        rows = q("""SELECT t.file, t.sample, ps.num, ps.name FROM kit_template t JOIN pursuit_stage ps ON ps.num=t.stage_num
                    WHERE ps.code = ANY(%s) ORDER BY ps.num, t.sample""", (ok,))
        return {"reply": "Templates and aids you can open:\n" + "\n".join(f"- {r['num']}. {r['name']}: {r['file']}{' *(FlyHigh sample)*' if r['sample'] else ''}" for r in rows),
                "cards": [_card("kit", "Pursuit kit", f"{len(rows)} files", "kit", "")], "suggestions": []}

    # Pursuit stage by name (pursuit lens first; other lenses only reach here if their own words don't match)
    if lens == "pursuit" or re.search(r"pursuit|proposal|rfp|bid", m):
        for code, words in PURSUIT_WORDS.items():
            if any(w in m for w in words):
                return _pursuit_reply(code, lens)

    # 1. Orientation
    if impl_ok and re.search(r"\b(hi|hello|help|start|begin|get started|where do i)\b", m) and len(m) < 60:
        stages = q("SELECT code, seq, name, lead_role FROM stage ORDER BY seq")
        reply = ("Welcome to **FlyHigh Navigator**. The delivery runs in ten guided steps from discovery to monitoring, "
                 "each with its agents, skills, tools and human gates:\n" +
                 "\n".join(f"- {s['seq']}. {s['name']} — {s['lead_role']}" for s in stages) +
                 "\n\nStart with **Discover**: open it, tick off the key steps, then press **Next**. "
                 "From the pursuit you share stages **5 Delivery plan and effort (G4)**, **8 Red team (G7)** and **9 Submit and orals (G8)**. "
                 "You can also curate persona journeys, insights and the logistics data model from the left menu.")
        return {"reply": reply, "cards": [_card("stage", "1 · Discover", "Start here", "workflow", "discover")],
                "suggestions": ["What does the PRD Agent do?", "Show the 20 subject areas", "Which skills are used most?"]}

    # 2. Next step in the guided flow
    if re.search(r"\b(next|what now|then what|after this)\b", m) and context.get("stage"):
        nxt = _next_stage(context["stage"])
        if nxt:
            s = _stage(nxt["code"])
            return {"reply": "Next up:\n\n" + _stage_reply(s), "cards": [_card("stage", f"{s['seq']} · {s['name']}", s["gate"], "workflow", s["code"])],
                    "suggestions": (s["extra"] or {}).get("prompts", [])[:3]}
        return {"reply": "You're at the last step, **Operate & monitor**. Build learnings flow back into Discover for the next wave.",
                "cards": [_card("stage", "1 · Discover", "Start the next wave", "workflow", "discover")], "suggestions": []}

    # 3. A slash skill
    sk = re.search(r"/[a-z][a-z\-]+", m)
    if sk and impl_ok:
        rows = q("""SELECT c.name skill, a.name agent, s.name stage, s.code FROM component c
                    JOIN stage_component sc ON sc.component_id=c.id JOIN stage s ON s.id=sc.stage_id
                    LEFT JOIN component a ON a.id=sc.parent_id WHERE c.kind='skill' AND c.name ILIKE %s ORDER BY s.seq""",
                 (sk.group(0) + "%",))
        if rows:
            reply = f"`{rows[0]['skill']}` is invoked by:\n" + "\n".join(f"- **{r['agent']}** in {r['stage']}" for r in rows)
            cards = [_card("skill", f"/{rows[0]['skill'].lstrip('/')}", "Run it in the skills studio", "skills", rows[0]["skill"].lstrip("/"))]
            cards += [_card("stage", r["stage"], r["agent"], "workflow", r["code"]) for r in {r["code"]: r for r in rows}.values()]
            return {"reply": reply, "cards": cards, "suggestions": ["Which skills are used most?"]}

    if impl_ok and "skills" in m and ("most" in m or "all" in m or "list" in m):
        rows = q("""SELECT c.name, count(DISTINCT sc.stage_id) n FROM component c JOIN stage_component sc ON sc.component_id=c.id
                    WHERE c.kind='skill' GROUP BY c.name ORDER BY n DESC, c.name LIMIT 12""")
        return {"reply": "Skills used across the most stages:\n" + "\n".join(f"- `{r['name']}` — {r['n']} stage(s)" for r in rows),
                "cards": [_card("catalog", "Toolkit catalog", "All skills", "catalog", "skill")], "suggestions": []}

    # 4. KPIs
    if "kpi" in m or "metric" in m or "measure" in m:
        aud = "E" if "exec" in m else "O" if "operat" in m else "C" if "customer" in m or "shipper" in m else None
        terms = [t for t in _tokens(m) if t not in {"kpi", "kpis", "metric", "metrics", "measure", "matter", "executives", "executive", "operational", "customer", "customers"}]
        rows = q("SELECT * FROM kpi ORDER BY domain, id")
        if aud:
            rows = [r for r in rows if aud in (r["audiences"] or "")]
        if terms:
            hit = [r for r in rows if any(t in f"{r['name']} {r['domain']} {r['formula']}".lower() for t in terms)]
            rows = hit or rows
        label = {"E": "executive", "O": "operational", "C": "external customer"}.get(aud, "")
        reply = f"{len(rows)} certified {label} KPIs:\n" + "\n".join(f"- **{r['name']}** = {r['formula']}" for r in rows[:14])
        return {"reply": reply, "cards": [_card("kpi", "KPI library", f"{len(rows)} KPIs", "data", "kpis")],
                "suggestions": ["Which fact feeds OTIF?", "Show the warehouse schema"]}

    # 5. Personas / journeys
    if "journey" in m or "persona" in m:
        rows = q("SELECT * FROM persona ORDER BY id")
        terms = _tokens(m)
        hit = [p for p in rows if any(t in f"{p['name']} {p['roles']} {p['segment']} {p['journey']}".lower() for t in terms if t not in {"journey", "persona", "personas", "journeys"})]
        if hit:
            p = hit[0]
            steps = q("SELECT * FROM journey_step WHERE persona_id=%s ORDER BY seq", (p["id"],))
            reply = f"**{p['name']}** ({p['roles']}) wants: {p['wants']}.\n" + "\n".join(
                f"- {s['seq']}. **{s['name']}** — “{s['question']}” → {s['experience']}" for s in steps)
            return {"reply": reply, "cards": [_card("persona", p["name"], p["segment"], "journeys", str(p["id"]))], "suggestions": ["Show the executive dashboard"]}
        reply = f"{len(rows)} personas across internal, customer and automation journeys:\n" + "\n".join(f"- **{p['name']}** · {p['segment']} · {p['roles']}" for p in rows)
        return {"reply": reply, "cards": [_card("persona", "Persona journeys", "Curate", "journeys", "")], "suggestions": ["Show the customer journey", "Show the dispatcher journey"]}

    # 6. Insights
    if "dashboard" in m or "insight" in m:
        rows = q("SELECT * FROM insight_dashboard ORDER BY id")
        terms = _tokens(m)
        hit = [d for d in rows if any(t in d["name"].lower() or t in (d["audience"] or "").lower() for t in terms if t not in {"dashboard", "insight", "insights"})]
        if hit:
            d = hit[0]
            qs = q("SELECT * FROM insight_question WHERE dashboard_id=%s ORDER BY seq", (d["id"],))
            reply = f"**{d['name']}** — {d['headline']}\n" + "\n".join(f"- *{x['kind']}*: “{x['question']}” {x['answer']}" for x in qs)
            return {"reply": reply, "cards": [_card("dashboard", d["name"], d["audience"], "insights", str(d["id"]))], "suggestions": []}
        return {"reply": "Four insight dashboards, each answering what happened, why, what will happen and what to do:\n" +
                         "\n".join(f"- **{d['name']}** — {d['headline']}" for d in rows),
                "cards": [_card("dashboard", "Insights", "4 dashboards", "insights", "")], "suggestions": ["Show the operations dashboard"]}

    # 7. Data model
    if "subject area" in m or "data model" in m or "domain" in m:
        rows = q("SELECT sa.num, sa.name, d.name AS domain FROM subject_area sa JOIN domain d ON d.id=sa.domain_id ORDER BY sa.num")
        reply = f"{len(rows)} subject areas on a conformed backbone:\n" + "\n".join(f"- {r['num']}. {r['name']} ({r['domain']})" for r in rows)
        return {"reply": reply, "cards": [_card("data", "Logistics data model", "Subject areas", "data", "areas")], "suggestions": ["Show the warehouse schema", "Which fact feeds OTIF?"]}
    if "schema" in m or re.search(r"\b(fact|dim)", m):
        model = "Transportation" if "transport" in m else "Automation & labor" if ("automation" in m or "labor" in m) else "Warehouse"
        rows = q("SELECT name, kind, type, description FROM data_entity WHERE model=%s ORDER BY kind DESC, id", (model,))
        if "feeds" in m or "source" in m:
            terms = [t for t in _tokens(m) if t not in {"fact", "feeds", "source", "which"}]
            ks = [k for k in q("SELECT * FROM kpi") if any(t in k["name"].lower() for t in terms)]
            if ks:
                return {"reply": "\n".join(f"**{k['name']}** is computed from `{k['source_fact'] or 'to be confirmed in discovery'}` ({k['formula']})." for k in ks),
                        "cards": [_card("kpi", "KPI library", "", "data", "kpis")], "suggestions": []}
        reply = f"**{model} schema** — {len(rows)} entities:\n" + "\n".join(f"- `{r['name']}` ({r['type']}) {r['description'][:80]}" for r in rows[:16])
        return {"reply": reply, "cards": [_card("data", f"{model} schema", "Star schema", "data", "schemas")], "suggestions": []}

    # 8. A workflow stage mentioned by name
    for code, words in STAGE_WORDS.items():
        if any(w in m + " " for w in words):
            if not impl_ok:
                return {"reply": "The implementation lifecycle (Discover to Operate & monitor) is in the **delivery lens**. "
                                 "In the pursuit lens, engineering shows up as proposal section 7 and the delivery plan in pursuit stage 5.",
                        "cards": [_card("lifecycle", "Lifecycle overview", "", "lifecycle", "")], "suggestions": SUGGEST[lens][:2]}
            s = _stage(code)
            if "agent" in m and "tool" not in m and "skill" not in m:
                agents = [c for c in s["components"] if c["kind"] == "agent"]
                reply = f"**{s['name']}** uses {len(agents)} agents:\n" + "\n".join(f"- **{a['name']}** — {a['category']}" for a in agents)
            else:
                reply = _stage_reply(s)
            return {"reply": reply, "cards": [_card("stage", f"{s['seq']} · {s['name']}", s["gate"], "workflow", s["code"])],
                    "suggestions": (s["extra"] or {}).get("prompts", [])[:3] + ["What's next?"]}

    for code, words in PURSUIT_WORDS.items():
        if any(w in m for w in words):
            return _pursuit_reply(code, lens)

    # 9. Retrieval fallback
    terms = _tokens(m)
    rows = q("SELECT * FROM search_index")
    ok_stages = allowed_codes("pursuit_stage", lens)
    ok_screens = allowed_codes("screen", lens)
    ok_nums = {r["num"] for r in q("SELECT num, code FROM pursuit_stage") if r["code"] in ok_stages}
    tmpl_num = {str(r["id"]): r["stage_num"] for r in q("SELECT id, stage_num FROM kit_template")}
    def visible(r):
        if r["kind"] in IMPL_KINDS:
            return impl_ok
        if r["kind"] == "pursuit_stage":
            return r["ref"] in ok_stages
        if r["kind"] == "kit_template":
            return tmpl_num.get(r["ref"]) in ok_nums
        if r["kind"] in ("pursuit_artefact", "pursuit_skill"):
            return lens == "pursuit" or any(str(n) in (r["body"] or "") for n in ok_nums)
        if r["kind"] in PMO_KIND_SCREEN:
            return PMO_KIND_SCREEN[r["kind"]] in ok_screens
        if r["kind"] in ("persona", "journey_step"):
            return "journeys" in ok_screens
        if r["kind"] in ("dashboard", "insight"):
            return "insights" in ok_screens
        if r["kind"] in ("subject_area", "entity", "kpi"):
            return "data" in ok_screens
        if r["kind"] == "section":
            return "quality" in ok_screens
        return True
    rows = [r for r in rows if visible(r)]
    scored = []
    for r in rows:
        hay = f"{r['title']} {r['body']}".lower()
        score = sum(3 if t in r["title"].lower() else 1 for t in terms if t in hay)
        if score:
            scored.append((score, r))
    scored.sort(key=lambda x: -x[0])
    top = [r for _, r in scored[:6]]
    if not top:
        return {"reply": "I couldn't find that in what your lens can open. Try a stage, gate, template, section or KPI." if lens == "pursuit" else
                "I couldn't find that in the playbook. Try readiness, the estimate, a KPI, the RAID log, RACI or an archetype such as migration." if lens == "pmo" else "I couldn't find that in the FlyHigh catalog yet. Try asking about a stage, an agent, a skill like `/reconcile`, a KPI or a persona — or add it through the curation screens.",
                "cards": [], "suggestions": SUGGEST_DEFAULT}
    view = {"stage": "workflow", "agent": "catalog", "skill": "catalog", "tool": "catalog", "framework": "catalog", "snowflake": "catalog",
            "persona": "journeys", "journey_step": "journeys", "dashboard": "insights", "insight": "insights",
            "subject_area": "data", "entity": "data", "kpi": "data", "pursuit_stage": "pursuit", "pursuit_artefact": "pursuit",
            "pursuit_skill": "kit", "kit_template": "kit", "section": "quality",
            "pmo_kpi": "kpis", "pmo_raid": "governance", "pmo_usecase": "usecases", "aw_case": "aw_design", "aw_defect": "aw_analytics", "aw_test_type": "aw_testmap"}
    reply = "Here's what matches in the catalog:\n" + "\n".join(f"- **{r['title']}** ({r['kind'].replace('_', ' ')}) — {(r['body'] or '')[:110]}" for r in top)
    cards = [_card(r["kind"], r["title"], r["kind"].replace("_", " "), view.get(r["kind"], "catalog"), r["ref"]) for r in top[:4]]
    return {"reply": reply, "cards": cards, "suggestions": SUGGEST[lens][:2], "context_rows": top}


def llm_polish(message, result):
    """Rephrase the rule-based answer with the configured LLM (any provider); keep the original on any failure."""
    if not llm.available() or os.getenv("CHAT_USE_LLM", "true").lower() == "false":
        return result
    try:
        result["reply"] = llm.complete(
            "You are the FlyHigh Navigator guide for a Niche Consulting pursuit, Snowflake modernization program and its program office. "
            "Answer only from the CONTEXT, which is already filtered to the user's persona lens; never add content beyond it. "
            "Be concise; use short markdown bullets.",
            f"CONTEXT:\n{result['reply']}\n\nQUESTION: {message}", max_tokens=600)
        result["llm"] = True
    except Exception as e:  # keep the rule-based answer
        result["llm_error"] = str(e)[:200]
    return result


def handle(message, session_id, context, p):
    res = answer(message, context, p["lens"])
    res.pop("context_rows", None)
    res = llm_polish(message, res)
    q_ = "INSERT INTO chat_message(session_id,role,content,payload) VALUES (%s,%s,%s,%s) RETURNING id"
    one(q_, (session_id, "user", message, json.dumps(context or {})))
    one(q_, (session_id, "assistant", res["reply"], json.dumps({k: v for k, v in res.items() if k != "reply"})))
    return res
