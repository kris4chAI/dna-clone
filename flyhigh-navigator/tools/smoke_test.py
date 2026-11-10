"""End-to-end smoke test for a running FlyHigh Navigator (stdlib only).

    python tools/smoke_test.py                       # http://localhost:8080
    python tools/smoke_test.py http://localhost:8000

Checks: health, UI, persona lens enforcement (401/403), lifecycle, pursuit, kit, win room, quality,
the PMO and assurance screens, the chat guide in all four lenses, every pursuit, PMO and assurance skill engine and every Snowflake delivery skill.
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
check("lenses: pursuit, delivery, assurance, PMO (+ sales reserved)", s == 200 and len([l for l in ls if l["available"]]) == 4)
for path in ["/api/pmo/playbook", "/api/pmo/readiness", "/api/pmo/roadmap?archetype=bi", "/api/pmo/estimator", "/api/pmo/usecases",
             "/api/pmo/kpis", "/api/pmo/governance", "/api/pmo/team", "/api/stages", "/api/pursuit/stages/delivery"]:
    check(f"GET {path} as {M}", call(path, M)[0] == 200)
check("PMO blocked from win room", call("/api/winroom", M)[0] == 403)
check("PMO blocked from pursuit stage 6", call("/api/pursuit/stages/commercials", M)[0] == 403)
check("pursuit blocked from PMO readiness", call("/api/pmo/readiness", S)[0] == 403)
check("delivery reads the playbook, not the KPI scorecard", call("/api/pmo/playbook", D)[0] == 200 and call("/api/pmo/kpis", D)[0] == 403)
s, r = call("/api/pmo/raid", M, {"kind": "Risk", "title": "smoke test risk"})
Q = "qa_lead"
for path in ["/api/assurance/overview", "/api/assurance/design", "/api/assurance/execution", "/api/assurance/analytics", "/api/assurance/maintenance"]:
    check(f"GET {path} as {Q}", call(path, Q)[0] == 200)
check("assurance lens available after delivery", [l["code"] for l in ls if l["available"]] == ["pursuit", "delivery", "assurance", "pmo"])
s, tm = call("/api/assurance/testmap", Q)
check("lakehouse test map covers 39 test types in 9 layers", s == 200 and len(tm["types"]) == 39 and len({t["layer"] for t in tm["types"]}) == 9, str(tm and tm["counts"]))
s, r = call("/api/assurance/testmap/generate", Q, {"codes": ["L4.2"]})
check("test map generates cases for a test type", s == 200 and r and r.get("id"))
check("delivery reads assurance analytics, not design", call("/api/assurance/analytics", D)[0] == 200 and call("/api/assurance/design", D)[0] == 403)
check("pursuit blocked from assurance", call("/api/assurance/overview", S)[0] == 403)
s, r = call("/api/assurance/design/cases/generate", Q, {"source": "document", "doc_type": "API DOCS", "doc_text": "GET /shipments/{id}"})
check("assurance generates test cases from API docs", s == 200 and r and r.get("id"))
s, e = call("/api/assurance/execution", Q)
s, c = call(f"/api/assurance/execution/plans/{e['plans'][0]['id']}/run", Q, {}) if e else (0, None)
check("assurance runs a test plan", s == 200 and c and c["total"] > 0, f"{c and c['passed']} passed, {c and c['failed']} failed")
check("PMO adds a RAID item", s == 200 and r and call(f"/api/pmo/raid/{r['id']}", M, method="DELETE")[0] == 200)
# --- TAF data checks and failure triage (merged from the TAF operator app)
import time
s, cfg = call("/api/assurance/taf/config", Q)
check("TAF config lists Simulator, Snowflake and Databricks engines", s == 200 and [e["name"] for e in cfg["engines"]] == ["Simulator", "Snowflake", "Databricks"])
s, dash = call("/api/assurance/taf/dashboard", Q)
check("TAF dashboard counts scenarios and distinct checks per suite", s == 200 and {x["suite"] for x in dash["suites"]} == {"TAF", "EXTERNAL"} and all("distinct_checks" in x for x in dash["suites"]))
s, suite = call("/api/assurance/taf/suite", Q)
check("TAF suite seeded (22 TAF + 10 external)", s == 200 and len(suite["rows"]) >= 32)
t = next(x for x in suite["rows"] if x["suite"] == "TAF" and x["is_active"])
s, r = call(f"/api/assurance/taf/suite/TAF/{t['test_id']}/set-active", Q, {"is_active": False})
s2, _ = call(f"/api/assurance/taf/suite/TAF/{t['test_id']}/set-active", Q, {"is_active": True})
check("TAF activate/deactivate is verified", s == 200 and s2 == 200 and r and r.get("verified"))
check("TAF rejects LATEST_LOAD with CDF", call("/api/assurance/taf/execute", Q, {"filter_mode": "LATEST_LOAD", "date_source": "CDF"})[0] == 400)
check("TAF Databricks engine reports not configured", call("/api/assurance/taf/execute", Q, {"engine": "Databricks"})[0] in (400, 503))
s, run = call("/api/assurance/taf/execute", Q, {"engine": "Simulator", "test_scope": "All Active Test Cases"})
st = None
for _ in range(30):
    if not run: break
    _, st = call(f"/api/assurance/taf/run-status/{run['run_id']}", Q)
    if st and st.get("terminal"): break
    time.sleep(1)
check("TAF simulator run finishes with a manifest status", s == 200 and st and st["terminal"] and st["manifest"]["status"] in ("Passed", "Partial"), st and st["manifest"]["notes"])
s, res = call(f"/api/assurance/taf/results?run_id={run['run_id']}" if run else "/api/assurance/taf/results", Q)
check("TAF results use TAF statuses with executed SQL", s == 200 and res["rows"] and all(x["status"] in ("Pass", "Fail", "Warn", "Error", "Skipped", "Manual", "Info", "Not_Run", "Blocked") for x in res["rows"]))
check("TAF run log readable", call(f"/api/assurance/taf/run-log/{run['run_id']}", Q)[0] == 200 if run else False)
s, scn = call("/api/assurance/taf/scenarios/execute", Q, {})
check("TAF health scenarios run with caveats", s == 200 and len(scn["rows"]) >= 7 and all(x["status"] in ("PASS", "FAIL", "NO_DATA", "ERROR") for x in scn["rows"]))
s, tri = call("/api/assurance/triage?scope=latest", Q)
check("failure triage lists data checks and test cases", s == 200 and {x["source"] for x in tri["rows"]} >= {"Data check", "Test case"}, str(tri and tri["counts"]))
cand = [x for x in tri["rows"] if not x["defect_key"]] if tri else []
check("triage resolve needs a recommended fix", bool(cand) and call(f"/api/assurance/triage/{cand[0]['failure_id']}/resolve", Q, {"resolved": True, "recommended_fix": ""})[0] == 400)
s, d = call(f"/api/assurance/triage/{cand[-1]['failure_id']}/defect", Q, {}) if cand else (0, None)
check("triage raises a linked defect in one action", s == 200 and d and d.get("key", "").startswith("DEF-"))
s, r = call("/api/chat", Q, {"message": "How are the data checks?", "session_id": "smoke"})
check("guide answers data-check and triage questions", s == 200 and "TAF data checks" in r["reply"] and "Failure triage" in call("/api/chat", Q, {"message": "What needs triage?", "session_id": "smoke"})[1]["reply"])
# --- Settings: asset management and connections
s, sp = call("/api/assurance/settings/spec", Q)
check("settings spec lists LLM, ALM, storage, DB and parser connections", s == 200 and [k["code"] for k in sp["kinds"]] == ["llm", "alm", "storage", "db", "parser"])
s, av = call("/api/assurance/settings/assets", Q)
check("settings lists 13 assets with their connection needs", s == 200 and len(av["assets"]) == 13 and all(a["needs"] for a in av["assets"]))
s, cn = call("/api/assurance/settings/connections/parser", Q, {"provider": "llama", "name": "smoke parser", "config": {}, "secrets": {"api_key": "llx-smoke-0000000000"}})
check("settings adds a parser connection and masks the key", s == 200 and cn and cn["secrets"]["api_key"].startswith("••••") and "smoke" not in json.dumps(cn["secrets"]))
check("settings rejects a connection with missing required fields", call("/api/assurance/settings/connections/alm", Q, {"provider": "jira", "name": "x", "config": {}, "secrets": {}})[0] == 400)
s, asg = call("/api/assurance/settings/assign/parser", Q)
check("configure connection requires every asset when assigning per asset", call("/api/assurance/settings/assign/parser", Q, {"mode": "per_asset", "per_asset": {}}, method="PUT")[0] == 400)
check("configure connection assigns one parser to all assets", cn and call("/api/assurance/settings/assign/parser", Q, {"mode": "all", "all": cn["id"]}, method="PUT")[0] == 200)
s, t = call(f"/api/assurance/settings/connections/parser/{cn['id']}/test", Q, {}) if cn else (0, None)
check("settings test connection returns a status", s == 200 and t["status"] in ("ok", "failed", "unverified"), t and t["message"][:60])
check("settings asset toggle", call("/api/assurance/settings/assets/mobile_automation", Q, {"enabled": True}, method="PUT")[0] == 200)
check("settings deletes a connection", cn and call(f"/api/assurance/settings/connections/parser/{cn['id']}", Q, method="DELETE")[0] == 200)
check("settings is assurance-only", call("/api/assurance/settings/assets", D)[0] == 403 and call("/api/assurance/settings/assets", M)[0] == 403)
check("delivery reads triage but cannot run data checks", call("/api/assurance/triage", D)[0] == 200 and call("/api/assurance/taf/execute", D, {})[0] == 403)
for who, msg in [(S, "What does gate G5 need?"), (D, "Which skills build RBAC?"), (M, "How ready is Track A?"), ("qa_lead", "Which tests failed?")]:
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
s, cat = call("/api/skills", "qa_lead")
aw = [x["name"] for x in cat["skills"] if x["kind"] == "assurance"] if cat else []
check("assurance skills catalogue", len(aw) == 6, f"{len(aw)} assurance skills, {len(cat['skills']) if cat else 0} in the assurance lens")
for n in aw:
    s, r = call(f"/api/skills/{n}/run", "qa_lead", {"params": {}, "mode": "engine", "session_id": "smoke"})
    check(f"assurance skill {n}", s == 200 and r and r.get("files"), r.get("summary", "") if r else "")
check("assurance runs /reconcile", call("/api/skills/reconcile/run", "qa_lead", {"params": {}})[0] == 200)
check("PMO runs plan-waves", call("/api/skills/plan-waves/run", M, {"params": {}})[0] == 200)
check("PMO blocked from gen-grants", call("/api/skills/gen-grants/run", M, {"params": {}})[0] == 403)
check("pursuit blocked from delivery skill", call("/api/skills/gen-grants/run", S, {"params": {}})[0] == 403)

print(f"\n{'ALL CHECKS PASSED' if not fails else str(len(fails)) + ' FAILED: ' + ', '.join(fails)}")
sys.exit(1 if fails else 0)
