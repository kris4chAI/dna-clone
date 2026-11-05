"""Load the pursuit lifecycle, kit, rubric and persona lens. Called from seed.py."""
import json
from pathlib import Path

from . import pursuit_data as P

DATA = Path(__file__).parent / "data"


def seed_pursuit(c):
    for i, (code, name, lens, owns, sup) in enumerate(P.LENS_ROLES):
        c.execute("INSERT INTO lens_role VALUES (%s,%s,%s,%s,%s,%s)", (code, name, lens, owns, sup, i))

    for code, label, s, d, reason in P.SCREEN_ACCESS:
        c.execute("INSERT INTO access_rule VALUES ('screen',%s,%s,%s,%s,%s)", (code, label, s, d, reason))

    for st in P.P_STAGES:
        shared = st["audience"] == "shared"
        reason = st.get("shared_reason") or "Pursuit stage owned by the sales team."
        c.execute("INSERT INTO access_rule VALUES ('pursuit_stage',%s,%s,TRUE,%s,%s)",
                  (st["code"], f"{st['num']}. {st['name']}", shared, reason))
        extra = {k: st[k] for k in ("links", "handover", "shared_reason") if k in st}
        extra["audience"] = st["audience"]
        c.execute("""INSERT INTO pursuit_stage(code,num,name,loop,gate_code,gate,approvers,purpose,critical,lane,
                     artefacts,skills,tools,questions,inputs,samples,extra)
                     VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                  (st["code"], st["num"], st["name"], st["loop"], st["gate_code"], st["gate"], st["approvers"], st["purpose"],
                   st["critical"], st["lane"], *[json.dumps(st[k]) for k in ("artefacts", "skills", "tools", "questions", "inputs", "samples")],
                   json.dumps(extra)))

    for a in P.P_ARTEFACTS:
        c.execute("INSERT INTO pursuit_artefact(name,stages,owner,format,drafted_by,system_of_record) VALUES (%s,%s,%s,%s,%s,%s)", a)
    for s in P.P_SKILLS:
        c.execute("INSERT INTO pursuit_skill(name,type,contributes,stages) VALUES (%s,%s,%s,%s)", s)
    refs = [("dependency", P.P_DEPENDENCIES), ("human_input", P.HUMAN_INPUTS), ("objection", P.OBJECTIONS)]
    for kind, rows in refs:
        for i, r in enumerate(rows):
            c.execute("INSERT INTO pursuit_ref(kind,seq,data) VALUES (%s,%s,%s)", (kind, i, json.dumps(r)))
    c.execute("INSERT INTO pursuit_ref(kind,seq,data) VALUES ('method',0,%s)", (json.dumps(P.METHOD),))

    # Kit: templates and editable sheets
    kit = json.loads((DATA / "pursuit_kit.json").read_text())
    for t in kit:
        dl = None if t["sample"] else f"{t['stage']}/{t['file']}"
        tid = c.execute("""INSERT INTO kit_template(stage_num,folder,file,format,sample,download)
                           VALUES (%s,%s,%s,%s,%s,%s) RETURNING id""",
                        (P.STAGE_FOLDER[t["stage"]], t["stage"], t["file"], t["format"], t["sample"], dl)).fetchone()["id"]
        for i, sh in enumerate(t["sheets"]):
            sid = c.execute("""INSERT INTO kit_sheet(template_id,seq,name,title,guidance,columns)
                               VALUES (%s,%s,%s,%s,%s,%s) RETURNING id""",
                            (tid, i, sh["name"], sh["title"], sh["guidance"], json.dumps(sh["columns"]))).fetchone()["id"]
            for j, r in enumerate(sh["rows"]):
                row = {col: (r[k] if k < len(r) else "") for k, col in enumerate(sh["columns"])}
                c.execute("INSERT INTO kit_row(sheet_id,seq,data) VALUES (%s,%s,%s)", (sid, j, json.dumps(row, default=str)))
    # Samples referenced on stages but not extracted (client-confidential files stay in the pursuit folder)
    have = {t["file"] for t in kit}
    for st in P.P_STAGES:
        for smp in st["samples"]:
            if smp not in have and "(" not in smp:
                c.execute("INSERT INTO kit_template(stage_num,folder,file,format,sample,download) VALUES (%s,%s,%s,%s,TRUE,NULL)",
                          (st["num"], None, smp, smp.rsplit(".", 1)[-1]))
                have.add(smp)

    for i, (code, name, w, full) in enumerate(P.RUBRIC):
        c.execute("INSERT INTO rubric_criterion VALUES (%s,%s,%s,%s,%s)", (code, i, name, w, full))
    for s in P.SECTIONS:
        num, name, slides, cnt, proves, mh, base, missing, fixes, blocked, weight, lens = s
        c.execute("""INSERT INTO response_section(num,name,slides,slide_count,proves,must_haves,baseline,missing,fixes,blocked_by,weight,owner_lens)
                     VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                  (num, name, slides, cnt, proves, json.dumps(mh), base, missing, fixes, blocked, weight, lens))
