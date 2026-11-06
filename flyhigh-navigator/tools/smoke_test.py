"""End-to-end smoke test for a running FlyHigh Navigator (stdlib only).

    python tools/smoke_test.py                       # http://localhost:8080
    python tools/smoke_test.py http://localhost:8000

Checks: health, UI, persona lens enforcement (401/403), lifecycle, pursuit, kit, win room, quality,
the chat guide in both lenses, every pursuit skill engine and every Snowflake delivery skill.
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
S, D = "pursuit_lead", "delivery_lead"
check("sales blocked from implementation", call("/api/stages", S)[0] == 403)
check("delivery blocked from win room", call("/api/winroom", D)[0] == 403)
check("delivery blocked from stage 1", call("/api/pursuit/stages/signal", D)[0] == 403)
check("delivery sees shared stage 5", call("/api/pursuit/stages/delivery", D)[0] == 200)
for path, who in [("/api/lifecycle", S), ("/api/pursuit/overview", S), ("/api/kit", S), ("/api/winroom", S), ("/api/quality", D),
                  ("/api/stages", D), ("/api/components", D), ("/api/personas", D), ("/api/datamodel", S)]:
    check(f"GET {path} as {who}", call(path, who)[0] == 200)
for who, msg in [(S, "What does gate G5 need?"), (D, "Which skills build RBAC?")]:
    s, r = call("/api/chat", who, {"message": msg, "session_id": "smoke"})
    check(f"chat as {who}", s == 200 and r and len(r.get("reply", "")) > 20)

s, cat = call("/api/skills", S)
pursuit = [x["name"] for x in cat["skills"]] if cat else []
check("sales skills catalogue", s == 200 and len(pursuit) == 9, f"{len(pursuit)} skills")
for n in pursuit:
    s, r = call(f"/api/skills/{n}/run", S, {"params": {}, "mode": "engine", "session_id": "smoke"})
    check(f"pursuit skill {n}", s == 200 and r and r.get("files"), r.get("summary", "") if r else "")
s, cat = call("/api/skills", D)
delivery = [x["name"] for x in cat["skills"] if x["kind"] == "delivery"] if cat else []
check("delivery skills catalogue", len(delivery) == 46, f"{len(delivery)} Snowflake skills")
bad = [n for n in delivery if call(f"/api/skills/{n}/run", D, {"params": {}, "mode": "engine"})[0] != 200]
check("all delivery skills generate", not bad, ", ".join(bad))
check("sales blocked from delivery skill", call("/api/skills/gen-grants/run", S, {"params": {}})[0] == 403)

print(f"\n{'ALL CHECKS PASSED' if not fails else str(len(fails)) + ' FAILED: ' + ', '.join(fails)}")
sys.exit(1 if fails else 0)
