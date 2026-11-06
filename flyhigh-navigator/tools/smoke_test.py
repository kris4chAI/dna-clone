"""End-to-end smoke test for a running FlyHigh Navigator (stdlib only).

    python tools/smoke_test.py                       # http://localhost:8080
    python tools/smoke_test.py http://localhost:8000

Checks: health, UI, persona lens enforcement (401/403), lifecycle, pursuit, kit, win room, quality,
the PMO screens, the chat guide in all three lenses, every pursuit and PMO skill engine and every Snowflake delivery skill.
"""
import json
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080").rstrip("/")
fails = []


def call(path, persona=None, body=None, method=None):
    req = urllib.request.Request(BASE + path, method=method or ("POST" if body is not None else "GET"),
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={**({"X-Persona": persona} if persona else {}), "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if r.headers.get_content_type() == "application/json" else raw)
    except urllib.error.HTTPError as e:
        return e.code, None


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""))
    if not ok:
        fails.append(name)


s, h = call("/api/health")
check("health", s == 200 and h and h.get("ok"), f"llm={h and h.get('llm')} ui={h and h.get('ui')}")
s, _ = call("/")
check("UI served", s == 200)
check("no persona → 401", call("/api/stages")[0] == 401)
S, D, M = "pursuit_lead", "delivery_lead", "program_manager"
check("pursuit blocked from implementation", call("/api/stages", S)[0] == 403)
check("delivery blocked from win room", call("/api/winroom", D)[0] == 403)
check("delivery blocked from stage 1", call("/api/pursuit/stages/signal", D)[0] == 403)
check("delivery sees shared stage 5", call("/api/pursuit/stages/delivery", D)[0] == 200)
for path, who in [("/api/lifecycle", S), ("/api/pursuit/overview", S), ("/api/kit", S), ("/api/winroom", S), ("/api/quality", D),
                  ("/api/stages", D), ("/api/components", D), ("/api/personas", D), ("/api/datamodel", S)]:
    check(f"GET {path} as {who}", call(path, who)[0] == 200)
s, ls = call("/api/lens/list")
check("lenses: pursuit, delivery, PMO (+ sales reserved)", s == 200 and [l["code"] for l in ls if l["available"]] == ["pursuit", "delivery", "pmo"])
for path in ["/api/pmo/playbook", "/api/pmo/readiness", "/api/pmo/roadmap?archetype=bi", "/api/pmo/estimator", "/api/pmo/usecases",
             "/api/pmo/kpis", "/api/pmo/governance", "/api/pmo/team", "/api/stages", "/api/pursuit/stages/delivery"]:
    check(f"GET {path} as {M}", call(path, M)[0] == 200)
check("PMO blocked from win room", call("/api/winroom", M)[0] == 403)
check("PMO blocked from pursuit stage 6", call("/api/pursuit/stages/commercials", M)[0] == 403)
check("pursuit blocked from PMO readiness", call("/api/pmo/readiness", S)[0] == 403)
check("delivery reads the playbook, not the KPI scorecard", call("/api/pmo/playbook", D)[0] == 200 and call("/api/pmo/kpis", D)[0] == 403)
s, r = call("/api/pmo/raid", M, {"kind": "Risk", "title": "smoke test risk"})
check("PMO adds a RAID item", s == 200 and r and call(f"/api/pmo/raid/{r['id']}", M, method="DELETE")[0] == 200)
for who, msg in [(S, "What does gate G5 need?"), (D, "Which skills build RBAC?"), (M, "How ready is Track A?")]:
    s, r = call("/api/chat", who, {"message": msg, "session_id": "smoke"})
    check(f"chat as {who}", s == 200 and r and len(r.get("reply", "")) > 20)

s, cat = call("/api/skills", S)
pursuit = [x["name"] for x in cat["skills"]] if cat else []
check("pursuit skills catalogue", s == 200 and len(pursuit) == 9, f"{len(pursuit)} skills")
for n in pursuit:
    s, r = call(f"/api/skills/{n}/run", S, {"params": {}, "mode": "engine", "session_id": "smoke"})
    check(f"pursuit skill {n}", s == 200 and r and r.get("files"), r.get("summary", "") if r else "")
s, cat = call("/api/skills", D)
delivery = [x["name"] for x in cat["skills"] if x["kind"] == "delivery"] if cat else []
check("delivery skills catalogue", len(delivery) == 46, f"{len(delivery)} Snowflake skills")
bad = [n for n in delivery if call(f"/api/skills/{n}/run", D, {"params": {}, "mode": "engine"})[0] != 200]
check("all delivery skills generate", not bad, ", ".join(bad))
s, cat = call("/api/skills", M)
pmo = [x["name"] for x in cat["skills"] if x["kind"] == "pmo"] if cat else []
check("PMO skills catalogue", len(pmo) == 4, f"{len(pmo)} PMO skills, {len(cat['skills']) if cat else 0} in the PMO lens")
for n in pmo:
    s, r = call(f"/api/skills/{n}/run", M, {"params": {}, "mode": "engine", "session_id": "smoke"})
    check(f"PMO skill {n}", s == 200 and r and r.get("files"), r.get("summary", "") if r else "")
check("PMO runs plan-waves", call("/api/skills/plan-waves/run", M, {"params": {}})[0] == 200)
check("PMO blocked from gen-grants", call("/api/skills/gen-grants/run", M, {"params": {}})[0] == 403)
check("pursuit blocked from delivery skill", call("/api/skills/gen-grants/run", S, {"params": {}})[0] == 403)

print(f"\n{'ALL CHECKS PASSED' if not fails else str(len(fails)) + ' FAILED: ' + ', '.join(fails)}")
sys.exit(1 if fails else 0)
