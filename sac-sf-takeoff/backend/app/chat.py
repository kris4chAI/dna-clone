"""Conversational guide.

Works offline with intent rules + retrieval over the Postgres `search_index` view.
If ANTHROPIC_API_KEY is set, the retrieved context is passed to Claude to phrase the answer.
"""
import json
import os
import re

import httpx

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


def answer(message: str, context: dict | None = None):
    context = context or {}
    m = message.lower().strip()
    cards, suggestions = [], []

    # 1. Orientation
    if re.search(r"\b(hi|hello|help|start|begin|get started|where do i)\b", m) and len(m) < 60:
        stages = q("SELECT code, seq, name, lead_role FROM stage ORDER BY seq")
        reply = ("Welcome to **Keystone Navigator**. The delivery runs in ten guided steps from discovery to monitoring, "
                 "each with its agents, skills, tools and human gates:\n" +
                 "\n".join(f"- {s['seq']}. {s['name']} — {s['lead_role']}" for s in stages) +
                 "\n\nStart with **Discover**: open it, tick off the key steps, then press **Next**. "
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
    if sk:
        rows = q("""SELECT c.name skill, a.name agent, s.name stage, s.code FROM component c
                    JOIN stage_component sc ON sc.component_id=c.id JOIN stage s ON s.id=sc.stage_id
                    LEFT JOIN component a ON a.id=sc.parent_id WHERE c.kind='skill' AND c.name ILIKE %s ORDER BY s.seq""",
                 (sk.group(0) + "%",))
        if rows:
            reply = f"`{rows[0]['skill']}` is invoked by:\n" + "\n".join(f"- **{r['agent']}** in {r['stage']}" for r in rows)
            cards = [_card("stage", r["stage"], r["agent"], "workflow", r["code"]) for r in {r["code"]: r for r in rows}.values()]
            return {"reply": reply, "cards": cards, "suggestions": ["Which skills are used most?"]}

    if "skills" in m and ("most" in m or "all" in m or "list" in m):
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
            s = _stage(code)
            if "agent" in m and "tool" not in m and "skill" not in m:
                agents = [c for c in s["components"] if c["kind"] == "agent"]
                reply = f"**{s['name']}** uses {len(agents)} agents:\n" + "\n".join(f"- **{a['name']}** — {a['category']}" for a in agents)
            else:
                reply = _stage_reply(s)
            return {"reply": reply, "cards": [_card("stage", f"{s['seq']} · {s['name']}", s["gate"], "workflow", s["code"])],
                    "suggestions": (s["extra"] or {}).get("prompts", [])[:3] + ["What's next?"]}

    # 9. Retrieval fallback
    terms = _tokens(m)
    rows = q("SELECT * FROM search_index")
    scored = []
    for r in rows:
        hay = f"{r['title']} {r['body']}".lower()
        score = sum(3 if t in r["title"].lower() else 1 for t in terms if t in hay)
        if score:
            scored.append((score, r))
    scored.sort(key=lambda x: -x[0])
    top = [r for _, r in scored[:6]]
    if not top:
        return {"reply": "I couldn't find that in the Keystone catalog yet. Try asking about a stage, an agent, a skill like `/reconcile`, a KPI or a persona — or add it through the curation screens.",
                "cards": [], "suggestions": SUGGEST_DEFAULT}
    view = {"stage": "workflow", "agent": "catalog", "skill": "catalog", "tool": "catalog", "framework": "catalog", "snowflake": "catalog",
            "persona": "journeys", "journey_step": "journeys", "dashboard": "insights", "insight": "insights",
            "subject_area": "data", "entity": "data", "kpi": "data"}
    reply = "Here's what matches in the catalog:\n" + "\n".join(f"- **{r['title']}** ({r['kind'].replace('_', ' ')}) — {(r['body'] or '')[:110]}" for r in top)
    cards = [_card(r["kind"], r["title"], r["kind"].replace("_", " "), view.get(r["kind"], "catalog"), r["ref"]) for r in top[:4]]
    return {"reply": reply, "cards": cards, "suggestions": SUGGEST_DEFAULT[:2], "context_rows": top}


def llm_polish(message, result):
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return result
    ctx = result["reply"]
    try:
        r = httpx.post("https://api.anthropic.com/v1/messages", timeout=30, headers={
            "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5"), "max_tokens": 600,
                  "system": "You are the Keystone Navigator guide for a Snowflake modernization program. Answer only from the CONTEXT. Be concise; use short markdown bullets.",
                  "messages": [{"role": "user", "content": f"CONTEXT:\n{ctx}\n\nQUESTION: {message}"}]})
        r.raise_for_status()
        result["reply"] = "".join(b.get("text", "") for b in r.json()["content"])
        result["llm"] = True
    except Exception as e:  # keep the rule-based answer
        result["llm_error"] = str(e)[:200]
    return result


def handle(message, session_id, context):
    res = answer(message, context)
    res.pop("context_rows", None)
    res = llm_polish(message, res)
    q_ = "INSERT INTO chat_message(session_id,role,content,payload) VALUES (%s,%s,%s,%s) RETURNING id"
    one(q_, (session_id, "user", message, json.dumps(context or {})))
    one(q_, (session_id, "assistant", res["reply"], json.dumps({k: v for k, v in res.items() if k != "reply"})))
    return res
