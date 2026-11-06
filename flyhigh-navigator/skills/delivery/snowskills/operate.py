"""Operate and monitor skills: ADRs, runbooks with Snowflake alerts, training and knowledge transfer."""
import re
from datetime import date

from . import Field, header, ident, lit, skill


@skill(name="gen-adr", stage="monitor", agent="Docs Agent", title="Architecture decision record",
       description="Write an ADR (MADR style) with context, options, decision, consequences and the Snowflake features involved.",
       snowflake=["Decision records next to Snowflake code"],
       fields=[Field("number", "ADR number", "text", "007"), Field("title", "Title", "text", "Use dynamic tables for near-real-time Silver"),
               Field("context", "Context", "textarea", "Warehouse task data must reach Silver within 30 minutes; dbt runs every hour today."),
               Field("options", "Options (one per line)", "lines", "dbt incremental every 15 minutes\nStreams + tasks with MERGE\nDynamic tables with TARGET_LAG = 30 minutes"),
               Field("decision", "Decision", "text", "Dynamic tables with TARGET_LAG = 30 minutes"),
               Field("consequences", "Consequences (one per line)", "lines", "Less orchestration code\nRefresh cost visible in DYNAMIC_TABLE_REFRESH_HISTORY\nComplex non-deterministic logic stays in dbt")],
       steps=["Draft when a decision is taken, not after.", "Link it from the design and the PR."],
       gate="Architecture lead accepts the ADR")
def gen_adr(p, sk):
    slug = re.sub(r"[^a-z0-9]+", "-", p.s("title").lower()).strip("-")
    md = [f"# ADR-{p.s('number')}: {p.s('title')}", "", f"- Status: proposed · {date.today()}", "- Deciders: [names]", "",
          "## Context", p.s("context"), "", "## Options", *[f"{i}. {o}" for i, o in enumerate(p.lines("options"), 1)], "",
          "## Decision", p.s("decision"), "", "## Consequences", *[f"- {c}" for c in p.lines("consequences")], ""]
    return {"files": {f"docs/adr/{p.s('number')}-{slug}.md": "\n".join(md)}, "summary": f"ADR-{p.s('number')} drafted."}


@skill(name="gen-runbook", stage="monitor", agent="Docs Agent", title="Runbook with alerts",
       description="Write a runbook for a pipeline or warehouse (set up, configure, run, troubleshoot, monitor) with Snowflake diagnostic queries and alerts that email the on-call team.",
       snowflake=["CREATE ALERT", "SYSTEM$SEND_EMAIL", "TASK_HISTORY / COPY_HISTORY / QUERY_HISTORY", "Event tables (optional)"],
       fields=[Field("component", "Component", "text", "WMS tasks ingestion"),
               Field("task", "Task to watch", "text", "FLYHIGH_PRD_BRONZE.WAREHOUSE.TSK_MERGE_WMS_TASKS"),
               Field("table", "Table + freshness column", "text", "FLYHIGH_PRD_SILVER.WAREHOUSE.WAREHOUSE_TASK | TASK_END"),
               Field("sla_minutes", "Freshness SLA (minutes)", "number", "30"),
               Field("email", "On-call email", "text", "data-oncall@abcretail.example"),
               Field("integration", "Email notification integration", "text", "NI_EMAIL")],
       steps=["Generate per component at build time.", "Apply alerts.sql and resume the alerts.", "Rehearse the troubleshooting steps during hypercare."],
       gate="Platform operations accepts the runbook at handover")
def gen_runbook(p, sk):
    tbl, col = [x.strip() for x in p.s("table").split("|")]
    sla, ni, email, task = int(p.n("sla_minutes", 30)), ident(p.s("integration")), p.s("email"), p.s("task")
    sch = ".".join(task.split(".")[:2])
    alerts = f"""{header(sk, f'alerts for {p.s("component")}')}CREATE OR REPLACE ALERT {sch}.ALR_FRESHNESS_{ident(tbl.split('.')[-1])}
  WAREHOUSE = WH_ADMIN SCHEDULE = '15 MINUTE'
  IF (EXISTS (SELECT 1 FROM {tbl} HAVING DATEDIFF(minute, MAX({col}), CURRENT_TIMESTAMP()) > {sla}))
  THEN CALL SYSTEM$SEND_EMAIL({lit(ni)}, {lit(email)}, {lit(p.s('component') + ': freshness SLA breached')},
       {lit(f'{tbl} is more than {sla} minutes behind. See the runbook, section Troubleshoot.')});

CREATE OR REPLACE ALERT {sch}.ALR_TASK_FAILED_{ident(task.split('.')[-1])}
  WAREHOUSE = WH_ADMIN SCHEDULE = '15 MINUTE'
  IF (EXISTS (SELECT 1 FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(TASK_NAME => {lit(task.split('.')[-1])},
              SCHEDULED_TIME_RANGE_START => DATEADD(minute, -15, CURRENT_TIMESTAMP()))) WHERE state = 'FAILED'))
  THEN CALL SYSTEM$SEND_EMAIL({lit(ni)}, {lit(email)}, {lit(p.s('component') + ': task failed')}, 'Check TASK_HISTORY for the error message.');

ALTER ALERT {sch}.ALR_FRESHNESS_{ident(tbl.split('.')[-1])} RESUME;
ALTER ALERT {sch}.ALR_TASK_FAILED_{ident(task.split('.')[-1])} RESUME;
"""
    md = f"""# Runbook: {p.s('component')}

## Set up
- Objects: `{task}`, `{tbl}`; owner role FR_DATA_ENG; warehouse WH_INGEST.
- Deployed by schemachange; see the release notes for the version.

## Configure
- Schedule and target lag live in the migration scripts; change them by PR only.
- Freshness SLA: {sla} minutes.

## Run
- Normal running needs no action. Manual run: `EXECUTE TASK {task};`
- Suspend for maintenance: `ALTER TASK {task} SUSPEND;` then `RESUME`.

## Troubleshoot
1. Task errors: `SELECT name, state, error_message, scheduled_time FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(TASK_NAME => '{task.split('.')[-1]}')) ORDER BY scheduled_time DESC LIMIT 20;`
2. Load errors: `SELECT * FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(TABLE_NAME => '<bronze table>', START_TIME => DATEADD(hour, -6, CURRENT_TIMESTAMP()))) WHERE error_count > 0;`
3. Missed files: run /replay-load (refresh, then force for named files).
4. Stale stream: recreate the stream and backfill from Time Travel; record the window.
5. Slow runs: check QUERY_HISTORY for spill and queueing; see /tune-warehouse.

## Monitor
- Alerts in `alerts.sql` email {email} on freshness breach and task failure.
- Weekly: credits from WAREHOUSE_METERING_HISTORY against the resource monitor.

## Escalation
- L1 platform operations → L2 data engineering → Snowflake support (account locator, query ID).
"""
    return {"files": {"runbook.md": md, "alerts.sql": alerts}, "summary": f"Runbook and 2 alerts for {p.s('component')}."}


@skill(name="gen-training", stage="monitor", agent="Enablement Agent", title="Role-based training plan",
       description="Build a role-based curriculum with Snowflake hands-on labs, shadow and reverse-shadow weeks and completion checks.",
       snowflake=["Snowsight", "Cortex Analyst", "Semantic views", "Task and alert operations"],
       fields=[Field("roles", "Roles (role | modules comma)", "lines",
                     "Platform operations | Run book drills, Alerts and task history, Resource monitors, Rollback with Time Travel\n"
                     "Data engineer | dbt and dynamic tables, Streams and tasks, Data metric functions, Reconciliation\n"
                     "BI developer | Semantic views, Tableau live connections, Row access testing\n"
                     "Business analyst | Cortex Analyst questions, Certified KPIs, Dashboard navigation"),
               Field("weeks", "Shadow weeks / reverse-shadow weeks", "text", "2 / 2")],
       steps=["Agree roles and names with the client.", "Run labs in the SBX environment with cloned data.", "Track completion before the handover gate."],
       gate="Client role owners confirm readiness")
def gen_training(p, sk):
    sh, rs = [x.strip() for x in p.s("weeks").split("/")]
    md = ["# Training plan", "", f"Shadow {sh} weeks, then reverse shadow {rs} weeks. Labs run in FLYHIGH_SBX_* on cloned data.", ""]
    for l in p.lines("roles"):
        r, _, mods = l.partition("|")
        md += [f"## {r.strip()}", "| Module | Lab | Done when |", "|---|---|---|"]
        md += [f"| {m.strip()} | Hands-on in Snowsight / repo | Learner completes the lab unaided |" for m in mods.split(",") if m.strip()]
        md.append("")
    return {"files": {"training_plan.md": "\n".join(md)}, "summary": f"{len(p.lines('roles'))} role curricula."}


@skill(name="kt-checklist", stage="monitor", agent="Enablement Agent", title="Knowledge transfer and handover",
       description="Handover checklist with ownership transfer SQL so the client's roles own every Snowflake object, plus sign-off steps.",
       snowflake=["GRANT OWNERSHIP ... COPY CURRENT GRANTS", "Service user and key handover", "Resource monitor ownership"],
       fields=[Field("schemas", "Schemas to hand over", "lines", "FLYHIGH_PRD_GOLD.WAREHOUSE\nFLYHIGH_PRD_GOLD.TRANSPORT\nFLYHIGH_PRD_SILVER.WAREHOUSE"),
               Field("from_role", "Current owner role (vendor)", "text", "FR_VENDOR_BUILD"),
               Field("to_role", "New owner role (client)", "text", "FR_ABC_PLATFORM_OWNER")],
       steps=["Walk the checklist in the last two hypercare weeks.", "Run ownership.sql with SECURITYADMIN.", "Sign the handover with the client platform owner."],
       gate="Formal handover sign-off by the client")
def kt_checklist(p, sk):
    to, fr = ident(p.s("to_role")), ident(p.s("from_role"))
    sql = [header(sk, "ownership transfer"), "USE ROLE SECURITYADMIN;"]
    for s in p.lines("schemas"):
        for obj in ("TABLES", "VIEWS", "DYNAMIC TABLES", "TASKS", "PROCEDURES", "STREAMS"):
            sql.append(f"GRANT OWNERSHIP ON ALL {obj} IN SCHEMA {s} TO ROLE {to} COPY CURRENT GRANTS;")
        sql.append(f"GRANT OWNERSHIP ON SCHEMA {s} TO ROLE {to} COPY CURRENT GRANTS;")
    sql.append(f"\n-- Remove build-time access\nREVOKE ROLE {fr} FROM ROLE SYSADMIN;\n-- DROP ROLE {fr};  -- after confirmation")
    md = ["# Handover checklist", "", "- [ ] Runbooks walked through and rehearsed (/gen-runbook)", "- [ ] ADRs and design docs in the client repo",
          "- [ ] CI/CD secrets rotated to client-owned service users (/gen-keypair)", "- [ ] Object ownership transferred (ownership.sql)",
          "- [ ] Resource monitors and alerts recipients updated", "- [ ] Training completion confirmed (/gen-training)",
          "- [ ] Open defects and risks handed over with owners", "- [ ] Handover sign-off: client platform owner · date"]
    return {"files": {"kt_checklist.md": "\n".join(md) + "\n", "ownership.sql": "\n".join(sql) + "\n"}, "summary": f"Ownership of {len(p.lines('schemas'))} schemas to {to}."}
