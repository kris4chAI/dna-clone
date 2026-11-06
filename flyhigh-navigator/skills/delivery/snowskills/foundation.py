"""Foundation build skills: zones, DDL conversion, migrations, RBAC, identity, auth, masking and row access."""
import re
from datetime import datetime

from . import Field, header, ident, lit, skill, to_yaml

ENV_F = Field("envs", "Environments (one per line)", "lines", "DEV\nSTG\nPRD\nSBX")
LAYER_F = Field("layers", "Layers (name | transient | retention days in PRD)", "lines", "BRONZE | yes | 1\nSILVER | no | 7\nGOLD | no | 30")
DOMAIN_F = Field("domains", "Domains / schemas (one per line)", "lines", "WAREHOUSE\nTRANSPORT\nCUSTOMER\nWORKFORCE")
PREFIX_F = Field("prefix", "Program prefix", "text", "FLYHIGH")


def _layers(p):
    out = []
    for l in p.lines("layers"):
        parts = [x.strip() for x in l.split("|")] + ["no", "1"]
        out.append({"name": ident(parts[0]), "transient": parts[1].lower() in ("yes", "y", "true"), "retention": int(parts[2] or 1)})
    return out


@skill(name="map-zones", stage="foundation", agent="Zone Mapper", title="Map data layers and zones",
       description="Generate the zone model (database per environment and layer, schema per domain) with retention and lifecycle rules from the standard.",
       snowflake=["Databases and managed-access schemas", "DATA_RETENTION_TIME_IN_DAYS", "Transient tables"],
       fields=[PREFIX_F, ENV_F, LAYER_F, DOMAIN_F],
       steps=["Agree environments, layers and domains with the platform standard.", "Generate zones.yaml and review naming.", "Pass the same inputs to /gen-zone-ddl."],
       gate="Platform engineer reviews the zone model in a PR")
def map_zones(p, sk):
    envs, layers, domains = [ident(e) for e in p.lines("envs")], _layers(p), [ident(d) for d in p.lines("domains")]
    model = {"prefix": ident(p.s("prefix")), "environments": []}
    for e in envs:
        model["environments"].append({"name": e, "databases": [
            {"name": f"{ident(p.s('prefix'))}_{e}_{l['name']}", "layer": l["name"], "transient": l["transient"],
             "retention_days": l["retention"] if e == "PRD" else min(l["retention"], 1), "schemas": domains} for l in layers]})
    md = ["# Zone model", "", "| Env | Database | Layer | Transient | Retention | Schemas |", "|---|---|---|---|---|---|"]
    for e in model["environments"]:
        for d in e["databases"]:
            md.append(f"| {e['name']} | {d['name']} | {d['layer']} | {d['transient']} | {d['retention_days']} d | {', '.join(domains)} |")
    md += ["", "Lifecycle: SBX objects expire after 30 days (see cleanup task in /gen-zone-ddl). Non-PRD retention is capped at 1 day to control storage."]
    return {"files": {"zones.yaml": to_yaml(model) + "\n", "zones.md": "\n".join(md) + "\n"},
            "summary": f"{len(envs) * len(layers)} databases × {len(domains)} schemas."}


@skill(name="gen-zone-ddl", stage="foundation", agent="Zone Mapper", title="Generate zone DDL",
       description="Emit idempotent Snowflake DDL and the equivalent Terraform for the zone model, with managed-access schemas, retention and a sandbox cleanup task.",
       snowflake=["CREATE DATABASE / SCHEMA ... WITH MANAGED ACCESS", "Object tags", "Tasks", "Terraform snowflake provider"],
       fields=[PREFIX_F, ENV_F, LAYER_F, DOMAIN_F, Field("owner_role", "Owning role", "text", "SYSADMIN")],
       steps=["Run with the same inputs as /map-zones.", "Review zones.sql; apply to DEV first with snow sql.", "Commit main.tf if the team manages Snowflake with Terraform instead."],
       gate="Peer review gate: no DDL reaches STG or PRD without an approved PR")
def gen_zone_ddl(p, sk):
    pre, own = ident(p.s("prefix")), ident(p.s("owner_role"))
    envs, layers, domains = [ident(e) for e in p.lines("envs")], _layers(p), [ident(d) for d in p.lines("domains")]
    sql = [header(sk, "zone databases and schemas"), f"USE ROLE {own};"]
    tf = ['terraform {\n  required_providers {\n    snowflake = { source = "Snowflake-Labs/snowflake" }\n  }\n}\n']
    for e in envs:
        sql.append(f"\n-- ===== {e} =====")
        for l in layers:
            db = f"{pre}_{e}_{l['name']}"
            ret = l["retention"] if e == "PRD" else min(l["retention"], 1)
            kw = "TRANSIENT " if l["transient"] else ""
            sql.append(f"CREATE {kw}DATABASE IF NOT EXISTS {db} DATA_RETENTION_TIME_IN_DAYS = {ret} COMMENT = {lit(f'{l['name']} layer · {e}')};")
            tf.append(f'resource "snowflake_database" "{db.lower()}" {{\n  name = "{db}"\n  data_retention_time_in_days = {ret}\n  is_transient = {str(l["transient"]).lower()}\n}}\n')
            for d in domains:
                sql.append(f"CREATE SCHEMA IF NOT EXISTS {db}.{d} WITH MANAGED ACCESS;")
                tf.append(f'resource "snowflake_schema" "{db.lower()}_{d.lower()}" {{\n  database = snowflake_database.{db.lower()}.name\n  name = "{d}"\n  with_managed_access = true\n}}\n')
    if "SBX" in envs:
        sql.append(f"""
-- Sandbox lifecycle: drop tables untouched for 30 days
CREATE SCHEMA IF NOT EXISTS {pre}_SBX_BRONZE.ADMIN;
CREATE OR REPLACE PROCEDURE {pre}_SBX_BRONZE.ADMIN.SP_SANDBOX_CLEANUP()
RETURNS VARCHAR LANGUAGE SQL EXECUTE AS CALLER AS
$$
DECLARE
  c CURSOR FOR SELECT table_catalog || '.' || table_schema || '.' || table_name AS fq
               FROM SNOWFLAKE.ACCOUNT_USAGE.TABLES
               WHERE table_catalog LIKE '{pre}_SBX_%' AND deleted IS NULL
                 AND last_altered < DATEADD(day, -30, CURRENT_TIMESTAMP());
  n INTEGER DEFAULT 0;
BEGIN
  FOR r IN c DO
    EXECUTE IMMEDIATE 'DROP TABLE IF EXISTS ' || r.fq;
    n := n + 1;
  END FOR;
  RETURN n || ' sandbox tables dropped';
END;
$$;
CREATE OR REPLACE TASK {pre}_SBX_BRONZE.ADMIN.T_SANDBOX_CLEANUP
  WAREHOUSE = WH_ADMIN SCHEDULE = 'USING CRON 0 3 * * SUN UTC'
AS CALL {pre}_SBX_BRONZE.ADMIN.SP_SANDBOX_CLEANUP();
-- ALTER TASK {pre}_SBX_BRONZE.ADMIN.T_SANDBOX_CLEANUP RESUME;  -- after review""")
    return {"files": {"zones.sql": "\n".join(x for x in sql if x) + "\n", "main.tf": "\n".join(tf)},
            "summary": f"DDL for {len(envs) * len(layers)} databases and {len(envs) * len(layers) * len(domains)} schemas."}


TYPE_MAP = [
    (r"\bVARCHAR2\s*\((\d+)\s*(?:BYTE|CHAR)?\)", r"VARCHAR(\1)"), (r"\bNVARCHAR2\s*\((\d+)\)", r"VARCHAR(\1)"),
    (r"\bNCHAR\s*\((\d+)\)", r"CHAR(\1)"), (r"\bCLOB\b|\bNCLOB\b|\bLONG\b(?!\s+RAW)", "VARCHAR"),
    (r"\bBLOB\b|\bLONG\s+RAW\b", "BINARY"), (r"\bRAW\s*\((\d+)\)", r"BINARY(\1)"),
    (r"\bTIMESTAMP\s*(\(\d\))?\s+WITH\s+LOCAL\s+TIME\s+ZONE\b", r"TIMESTAMP_LTZ\1"),
    (r"\bTIMESTAMP\s*(\(\d\))?\s+WITH\s+TIME\s+ZONE\b", r"TIMESTAMP_TZ\1"),
    (r"\bDATE\b", "TIMESTAMP_NTZ(0)"), (r"\bBINARY_DOUBLE\b|\bBINARY_FLOAT\b", "FLOAT"),
    (r"\bNUMBER\b(?!\s*\()", "NUMBER(38,10)"), (r"\bXMLTYPE\b", "VARIANT"), (r"\bSYSDATE\b", "CURRENT_TIMESTAMP()"),
    (r"\bSYSTIMESTAMP\b", "CURRENT_TIMESTAMP()"),
]
STRIP = [r"\bTABLESPACE\s+\w+", r"\bPCTFREE\s+\d+", r"\bPCTUSED\s+\d+", r"\bINITRANS\s+\d+", r"\bMAXTRANS\s+\d+",
         r"\bSTORAGE\s*\([^)]*\)", r"\b(NO)?LOGGING\b", r"\b(NO)?COMPRESS(\s+FOR\s+\w+)?\b", r"\bUSING\s+INDEX(\s+TABLESPACE\s+\w+)?",
         r"\bENABLE\b", r"\bSEGMENT\s+CREATION\s+\w+", r"\b(NO)?CACHE(\s+\d+)?\b", r"\bNOPARALLEL\b|\bPARALLEL\s*\d*"]


@skill(name="convert-ddl", stage="foundation", agent="DDL Converter", title="Convert legacy DDL",
       description="Translate Oracle DDL (tables, sequences, indexes) to Snowflake: type mapping, storage clauses removed, constraints kept as informational, with a warning per manual decision.",
       snowflake=["Snowflake data types", "Informational constraints", "Sequences / IDENTITY", "SnowConvert AI for full estates"],
       fields=[Field("ddl", "Oracle DDL", "textarea",
                     "CREATE TABLE WMS_DW.FACT_WAREHOUSE_TASK (\n  TASK_ID NUMBER(18) NOT NULL,\n  SITE_KEY NUMBER(10),\n  TASK_TYPE VARCHAR2(30 BYTE),\n  TASK_START DATE,\n  TASK_END DATE,\n  UNITS NUMBER,\n  NOTES CLOB,\n  CONSTRAINT PK_FWT PRIMARY KEY (TASK_ID) USING INDEX TABLESPACE IDX ENABLE\n) TABLESPACE DW_DATA PCTFREE 10 NOLOGGING COMPRESS;\n"
                     "CREATE INDEX IX_FWT_SITE ON WMS_DW.FACT_WAREHOUSE_TASK (SITE_KEY) TABLESPACE IDX;\n"
                     "CREATE SEQUENCE WMS_DW.SEQ_TASK START WITH 1 INCREMENT BY 1 CACHE 20;"),
               Field("target", "Target database.schema (replaces the Oracle owner)", "text", "FLYHIGH_DEV_SILVER.WAREHOUSE")],
       steps=["Paste DDL or point at an extract from /discover.", "Review every warning; numbers without precision default to NUMBER(38,10).",
              "Use SnowConvert AI (Snowflake AIM) for full-estate conversion; use this skill for targeted objects and fixes.", "Hand the output to /gen-migration."],
       gate="DDL converter output is peer-reviewed; parity proven later by /reconcile")
def convert_ddl(p, sk):
    src, tgt, warn = p.s("ddl"), p.s("target"), []
    out = []
    for stmt in [s.strip() for s in src.split(";") if s.strip()]:
        s = stmt
        if re.match(r"CREATE\s+(UNIQUE\s+)?(BITMAP\s+)?INDEX", s, re.I):
            warn.append(f"Index skipped ({s.split()[2] if len(s.split())>2 else ''}): Snowflake has no secondary indexes; consider a clustering key or search optimization.")
            out.append("-- " + s.replace("\n", "\n-- ") + ";")
            continue
        for pat, rep in TYPE_MAP:
            if re.search(pat, s, re.I) and pat.startswith(r"\bDATE"):
                warn.append("Oracle DATE carries time; mapped to TIMESTAMP_NTZ(0). Use DATE only where time is always midnight.")
            s = re.sub(pat, rep, s, flags=re.I)
        for pat in STRIP:
            s = re.sub(pat, "", s, flags=re.I)
        s = re.sub(r"(CREATE\s+(?:TABLE|SEQUENCE|VIEW)\s+)(\w+)\.(\w+)", lambda m: f"{m.group(1)}{tgt}.{m.group(3)}", s, flags=re.I)
        s = re.sub(r"(CREATE\s+)(TABLE)", r"\1OR REPLACE \2", s, count=1, flags=re.I) if re.match(r"CREATE\s+TABLE", s, re.I) else s
        if re.search(r"NUMBER\(38,10\)", s):
            warn.append("NUMBER without precision mapped to NUMBER(38,10); confirm scale from the data profile.")
        if re.search(r"PRIMARY KEY|FOREIGN KEY|UNIQUE", s, re.I):
            warn.append("Primary, unique and foreign keys are informational in Snowflake (not enforced); add /gen-unit-tests checks.")
        s = re.sub(r"[ \t]+\n", "\n", re.sub(r"[ \t]{2,}", " ", s))
        out.append(s.strip() + ";")
    warn = list(dict.fromkeys(warn))
    sql = header(sk, f"converted DDL → {tgt}") + "\n\n".join(out) + "\n"
    return {"files": {"converted.sql": sql, "warnings.md": "# Conversion warnings\n\n" + "\n".join(f"- {w}" for w in warn) + "\n"},
            "summary": f"{len(out)} statements converted, {len(warn)} warnings.", "notes": warn}


@skill(name="gen-migration", stage="foundation", agent="DDL Converter", title="Generate schemachange migration",
       description="Wrap reviewed SQL into a versioned schemachange script with a matching rollback note and change-history check.",
       snowflake=["schemachange (versioned V__ / repeatable R__ scripts)", "Time Travel for rollback"],
       fields=[Field("version", "Version", "text", "1.3.0"), Field("description", "Description", "text", "create fact warehouse task"),
               Field("kind", "Script kind", "choice", "V", options=["V", "R", "A"]),
               Field("sql", "Reviewed SQL", "textarea", "CREATE OR REPLACE TABLE FLYHIGH_DEV_SILVER.WAREHOUSE.FACT_WAREHOUSE_TASK (TASK_ID NUMBER(18) NOT NULL);"),
               Field("objects", "Objects created or changed (one per line)", "lines", "FLYHIGH_DEV_SILVER.WAREHOUSE.FACT_WAREHOUSE_TASK")],
       steps=["Use V scripts for one-off changes, R for views and procedures, A for always-run grants.", "Commit under migrations/ and let /promote deploy it.", "Keep rollback.sql with the PR."],
       gate="Release manager approves the migration PR")
def gen_migration(p, sk):
    desc = re.sub(r"[^a-z0-9]+", "_", p.s("description").lower()).strip("_")
    k = p.s("kind")
    fname = f"migrations/{k}{p.s('version')}__{desc}.sql" if k == "V" else f"migrations/{k}__{desc}.sql"
    body = f"-- schemachange {k} script · {p.s('description')}\n-- Objects: {', '.join(p.lines('objects'))}\n\n{p.s('sql').rstrip(';')};\n"
    rb = [header(sk, "rollback for " + fname), f"-- Release timestamp: set before deploy, e.g. SET release_ts = '{datetime.utcnow():%Y-%m-%d %H:%M:%S}';"]
    for o in p.lines("objects"):
        rb.append(f"-- {o}\nCREATE OR REPLACE TABLE {o} CLONE {o} AT (TIMESTAMP => $release_ts::TIMESTAMP_LTZ);  -- table restore via Time Travel\n-- or, if the object was new: DROP TABLE IF EXISTS {o};")
    check = "SELECT version, script, status, installed_on FROM METADATA.SCHEMACHANGE.CHANGE_HISTORY ORDER BY installed_on DESC LIMIT 10;\n"
    return {"files": {fname: body, "rollback.sql": "\n".join(rb) + "\n", "check_history.sql": check}, "summary": f"{fname} ready."}


RBAC_FIELDS = [PREFIX_F, Field("env", "Environment", "text", "PRD"), Field("layers", "Layers", "lines", "SILVER\nGOLD"), DOMAIN_F,
               Field("functional", "Functional roles (role | access: layer.schema:level, ...)", "lines",
                     "FR_DC_OPS | GOLD.WAREHOUSE:R, GOLD.WORKFORCE:R\nFR_TRANSPORT | GOLD.TRANSPORT:R\nFR_EXEC | GOLD.WAREHOUSE:R, GOLD.TRANSPORT:R, GOLD.CUSTOMER:R, GOLD.WORKFORCE:R\nFR_DATA_ENG | SILVER.WAREHOUSE:RW, SILVER.TRANSPORT:RW, GOLD.WAREHOUSE:RW, GOLD.TRANSPORT:RW\nFR_CUSTOMER_PORTAL | GOLD.CUSTOMER:R")]


@skill(name="design-rbac", stage="foundation", agent="RBAC Designer", title="Design role-based access",
       description="Design a two-tier role hierarchy: database roles for object access (read, write, own per schema) granted to functional account roles per persona.",
       snowflake=["Database roles", "Functional account roles", "Future grants", "Role hierarchy under SYSADMIN"],
       fields=RBAC_FIELDS,
       steps=["List personas as functional roles and the schemas each needs.", "Generate rbac.yaml and the diagram; review least privilege.", "Feed the same inputs to /gen-grants."],
       gate="Security reviews the role design; access review evidence kept")
def design_rbac(p, sk):
    model = _rbac(p)
    mer = ["graph LR"]
    for fr, acc in model["functional"].items():
        for a in acc:
            mer.append(f"  {fr} --> {a['db_role'].split('.')[-1]}")
    return {"files": {"rbac.yaml": to_yaml(model) + "\n", "rbac.mmd": "\n".join(mer) + "\n"},
            "summary": f"{len(model['functional'])} functional roles over {len(model['database_roles'])} database roles."}


def _rbac(p):
    pre, env = ident(p.s("prefix")), ident(p.s("env"))
    dbroles, functional = [], {}
    for l in [ident(x) for x in p.lines("layers")]:
        db = f"{pre}_{env}_{l}"
        for d in [ident(x) for x in p.lines("domains")]:
            for lvl in ("R", "RW", "OWN"):
                dbroles.append({"name": f"{db}.{d}_{lvl}", "database": db, "schema": d, "level": lvl})
    for line in p.lines("functional"):
        fr, _, spec = line.partition("|")
        acc = []
        for item in [x.strip() for x in spec.split(",") if x.strip()]:
            path, _, lvl = item.partition(":")
            layer, _, schema = path.partition(".")
            acc.append({"db_role": f"{pre}_{env}_{ident(layer)}.{ident(schema)}_{ident(lvl or 'R')}"})
        functional[ident(fr)] = acc
    return {"environment": env, "database_roles": dbroles, "functional": functional}


@skill(name="gen-grants", stage="foundation", agent="RBAC Designer", title="Generate grants",
       description="Emit database roles, schema and future grants, and functional-role bindings from the RBAC design, plus an access-review query.",
       snowflake=["CREATE DATABASE ROLE", "GRANT ... ON FUTURE TABLES / VIEWS", "GRANT DATABASE ROLE TO ROLE", "SHOW GRANTS"],
       fields=RBAC_FIELDS,
       steps=["Run with the inputs agreed in /design-rbac.", "Apply grants.sql with SECURITYADMIN after review.", "Run access_review.sql each quarter and file the output as evidence."],
       gate="Security approves grants; access review evidence stored per gate")
def gen_grants(p, sk):
    model = _rbac(p)
    sql = [header(sk, f"RBAC grants · {model['environment']}"), "USE ROLE SECURITYADMIN;"]
    for r in model["database_roles"]:
        db, sch, lvl, name = r["database"], r["schema"], r["level"], r["name"]
        sql.append(f"\n-- {name}\nCREATE DATABASE ROLE IF NOT EXISTS {name};")
        sql.append(f"GRANT USAGE ON DATABASE {db} TO DATABASE ROLE {name};")
        sql.append(f"GRANT USAGE ON SCHEMA {db}.{sch} TO DATABASE ROLE {name};")
        if lvl in ("R", "RW"):
            for obj in ("TABLES", "VIEWS", "DYNAMIC TABLES", "MATERIALIZED VIEWS"):
                sql.append(f"GRANT SELECT ON ALL {obj} IN SCHEMA {db}.{sch} TO DATABASE ROLE {name};")
                sql.append(f"GRANT SELECT ON FUTURE {obj} IN SCHEMA {db}.{sch} TO DATABASE ROLE {name};")
        if lvl == "RW":
            sql.append(f"GRANT INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA {db}.{sch} TO DATABASE ROLE {name};")
            sql.append(f"GRANT INSERT, UPDATE, DELETE, TRUNCATE ON FUTURE TABLES IN SCHEMA {db}.{sch} TO DATABASE ROLE {name};")
            sql.append(f"GRANT DATABASE ROLE {name.replace('_RW', '_R')} TO DATABASE ROLE {name};")
        if lvl == "OWN":
            sql.append(f"GRANT CREATE TABLE, CREATE VIEW, CREATE DYNAMIC TABLE, CREATE PROCEDURE, CREATE TASK, CREATE STREAM ON SCHEMA {db}.{sch} TO DATABASE ROLE {name};")
            sql.append(f"GRANT DATABASE ROLE {name.replace('_OWN', '_RW')} TO DATABASE ROLE {name};")
    sql.append("\n-- Functional roles")
    for fr, acc in model["functional"].items():
        sql.append(f"CREATE ROLE IF NOT EXISTS {fr};\nGRANT ROLE {fr} TO ROLE SYSADMIN;")
        for a in acc:
            sql.append(f"GRANT DATABASE ROLE {a['db_role']} TO ROLE {fr};")
    review = header(sk, "access review") + "".join(f"SHOW GRANTS TO ROLE {fr};\n" for fr in model["functional"])
    review += ("SELECT grantee_name, role AS granted_role, granted_by, created_on\nFROM SNOWFLAKE.ACCOUNT_USAGE.GRANTS_TO_ROLES\n"
               "WHERE deleted_on IS NULL AND granted_on = 'DATABASE_ROLE' ORDER BY grantee_name;\n")
    return {"files": {"grants.sql": "\n".join(sql) + "\n", "access_review.sql": review},
            "summary": f"{len(model['database_roles'])} database roles and {len(model['functional'])} functional roles."}


@skill(name="map-groups", stage="foundation", agent="Identity Mapper", title="Map IdP groups to roles",
       description="Map identity-provider groups to Snowflake functional roles for SCIM provisioning, with default roles, warehouses and a validation query.",
       snowflake=["SCIM-provisioned roles", "DEFAULT_ROLE / DEFAULT_WAREHOUSE", "GRANT ROLE"],
       fields=[Field("mapping", "Mapping CSV (idp_group,snowflake_role,default_warehouse)", "table",
                     "idp_group,snowflake_role,default_warehouse\nSF-DC-OPS,FR_DC_OPS,WH_BI\nSF-TRANSPORT,FR_TRANSPORT,WH_BI\nSF-EXEC,FR_EXEC,WH_BI\nSF-DATA-ENG,FR_DATA_ENG,WH_TRANSFORM")],
       steps=["Agree group names with the identity team.", "Provision groups via /gen-scim; SCIM creates a role per group.", "Apply role_bindings.sql to grant functional roles to the SCIM roles."],
       gate="Identity owner confirms the mapping")
def map_groups(p, sk):
    rows = p.table("mapping")
    sql = [header(sk, "bind SCIM group roles to functional roles"), "USE ROLE SECURITYADMIN;"]
    for r in rows:
        g, fr = ident(r["idp_group"]).replace("-", "_"), ident(r["snowflake_role"])
        sql.append(f'-- SCIM creates role "{r["idp_group"]}" for the IdP group')
        sql.append(f'GRANT ROLE {fr} TO ROLE "{r["idp_group"]}";')
    val = "".join(f'SHOW GRANTS OF ROLE "{r["idp_group"]}";\n' for r in rows)
    m = {"groups": [{"idp_group": r["idp_group"], "role": ident(r["snowflake_role"]), "default_warehouse": ident(r.get("default_warehouse", ""))} for r in rows]}
    return {"files": {"group_mapping.yaml": to_yaml(m) + "\n", "role_bindings.sql": "\n".join(sql) + "\n", "validate.sql": val},
            "summary": f"{len(rows)} groups mapped."}


@skill(name="gen-scim", stage="foundation", agent="Identity Mapper", title="Generate SCIM provisioning",
       description="Create the SCIM security integration and provisioner role for Okta or Microsoft Entra ID, and the token for the IdP app.",
       snowflake=["CREATE SECURITY INTEGRATION TYPE = SCIM", "SYSTEM$GENERATE_SCIM_ACCESS_TOKEN"],
       fields=[Field("idp", "Identity provider", "choice", "azure", options=["azure", "okta"]),
               Field("network_policy", "Network policy for the SCIM endpoint (optional)", "text", "")],
       steps=["Run as ACCOUNTADMIN after approval.", "Generate the token and paste it into the IdP provisioning app (valid 6 months).", "Set a reminder to rotate the token."],
       gate="Account admin and identity owner approve; token stored in the vault, never in the repo")
def gen_scim(p, sk):
    idp = p.s("idp")
    role = "AAD_PROVISIONER" if idp == "azure" else "OKTA_PROVISIONER"
    integ = "AAD_PROVISIONING" if idp == "azure" else "OKTA_PROVISIONING"
    np_ = f"\n  NETWORK_POLICY = {ident(p.s('network_policy'))}" if p.s("network_policy") else ""
    sql = f"""{header(sk, f'SCIM for {idp}')}USE ROLE ACCOUNTADMIN;
CREATE ROLE IF NOT EXISTS {role};
GRANT CREATE USER ON ACCOUNT TO ROLE {role};
GRANT CREATE ROLE ON ACCOUNT TO ROLE {role};
GRANT ROLE {role} TO ROLE ACCOUNTADMIN;

CREATE OR REPLACE SECURITY INTEGRATION {integ}
  TYPE = SCIM
  SCIM_CLIENT = '{idp.upper()}'
  RUN_AS_ROLE = '{role}'{np_};

-- Generate the bearer token for the IdP provisioning app (store it in the vault)
SELECT SYSTEM$GENERATE_SCIM_ACCESS_TOKEN('{integ}');
"""
    return {"files": {"scim.sql": sql}, "summary": f"SCIM integration {integ} for {idp}.",
            "notes": ["The token is shown once; rotate it before expiry."]}


@skill(name="design-auth", stage="foundation", agent="Auth Designer", title="Design authentication and encryption",
       description="Design SSO, network rules and policies, password and session policies, and key-pair auth for service users.",
       snowflake=["SAML2 security integration", "Network rules + network policies", "Authentication / password / session policies", "Service users (TYPE = SERVICE)"],
       fields=[Field("idp", "IdP", "choice", "azure", options=["azure", "okta"]),
               Field("allowed_ips", "Allowed IPv4 ranges (one per line)", "lines", "10.20.0.0/16\n203.0.113.10/32"),
               Field("service_users", "Service users (one per line)", "lines", "SVC_DBT\nSVC_TABLEAU\nSVC_INGEST"),
               Field("idle_minutes", "Session idle timeout (minutes)", "number", "60")],
       steps=["Complete the SAML values from the IdP metadata.", "Apply in DEV, test a login per persona, then STG and PRD.", "Generate keys for service users with /gen-keypair."],
       gate="Security architect approves; FOR JOINT REVIEW with the client security team")
def design_auth(p, sk):
    ips = ", ".join(lit(x) for x in p.lines("allowed_ips"))
    sql = f"""{header(sk, 'authentication and network controls')}USE ROLE ACCOUNTADMIN;
CREATE DATABASE IF NOT EXISTS GOVERNANCE;
CREATE SCHEMA IF NOT EXISTS GOVERNANCE.POLICIES;

-- SSO (fill from IdP metadata)
CREATE SECURITY INTEGRATION IF NOT EXISTS SSO_{p.s('idp').upper()}
  TYPE = SAML2
  ENABLED = TRUE
  SAML2_ISSUER = '[idp entity id]'
  SAML2_SSO_URL = '[idp sso url]'
  SAML2_PROVIDER = 'CUSTOM'
  SAML2_X509_CERT = '[base64 certificate]'
  SAML2_SNOWFLAKE_ACS_URL = 'https://[account].snowflakecomputing.com/fed/login'
  SAML2_SNOWFLAKE_ISSUER_URL = 'https://[account].snowflakecomputing.com';

-- Network rule + policy
CREATE OR REPLACE NETWORK RULE GOVERNANCE.POLICIES.NR_CORPORATE
  MODE = INGRESS TYPE = IPV4 VALUE_LIST = ({ips});
CREATE OR REPLACE NETWORK POLICY NP_CORPORATE ALLOWED_NETWORK_RULE_LIST = ('GOVERNANCE.POLICIES.NR_CORPORATE');
-- ALTER ACCOUNT SET NETWORK_POLICY = NP_CORPORATE;   -- only after testing from every allowed range

-- Humans: SSO + MFA; service users: key-pair only
CREATE OR REPLACE AUTHENTICATION POLICY GOVERNANCE.POLICIES.AP_HUMANS
  AUTHENTICATION_METHODS = ('SAML', 'PASSWORD') MFA_ENROLLMENT = REQUIRED CLIENT_TYPES = ('SNOWFLAKE_UI', 'DRIVERS', 'SNOWSQL');
CREATE OR REPLACE AUTHENTICATION POLICY GOVERNANCE.POLICIES.AP_SERVICES AUTHENTICATION_METHODS = ('KEYPAIR');
CREATE OR REPLACE PASSWORD POLICY GOVERNANCE.POLICIES.PP_STANDARD PASSWORD_MIN_LENGTH = 14 PASSWORD_MAX_AGE_DAYS = 90 PASSWORD_MAX_RETRIES = 5;
CREATE OR REPLACE SESSION POLICY GOVERNANCE.POLICIES.SP_STANDARD SESSION_IDLE_TIMEOUT_MINS = {int(p.n('idle_minutes', 60))} SESSION_UI_IDLE_TIMEOUT_MINS = {int(p.n('idle_minutes', 60))};
ALTER ACCOUNT SET AUTHENTICATION POLICY GOVERNANCE.POLICIES.AP_HUMANS;
ALTER ACCOUNT SET PASSWORD POLICY GOVERNANCE.POLICIES.PP_STANDARD;
ALTER ACCOUNT SET SESSION POLICY GOVERNANCE.POLICIES.SP_STANDARD;
"""
    for u in p.lines("service_users"):
        u = ident(u)
        sql += f"\nCREATE USER IF NOT EXISTS {u} TYPE = SERVICE COMMENT = 'service user';\nALTER USER {u} SET AUTHENTICATION POLICY GOVERNANCE.POLICIES.AP_SERVICES;"
    md = ["# Authentication design", "", "| Control | Setting |", "|---|---|", f"| SSO | SAML2 with {p.s('idp')} |",
          f"| Network | {len(p.lines('allowed_ips'))} allowed ranges via network rule |", "| Humans | SSO, MFA required |",
          "| Services | Key-pair only, TYPE = SERVICE |", f"| Session | idle timeout {int(p.n('idle_minutes', 60))} min |",
          "| Encryption | Snowflake-managed keys; Tri-Secret Secure if the client requires customer-managed keys [FOR JOINT REVIEW] |"]
    return {"files": {"auth.sql": sql + "\n", "auth_design.md": "\n".join(md) + "\n"}, "summary": "Auth policies, network rule and service users."}


@skill(name="gen-keypair", stage="foundation", agent="Auth Designer", title="Generate key-pair auth",
       description="Produce the key generation script, the ALTER USER statements and a rotation procedure for service users (keys are generated locally, never by the app).",
       snowflake=["RSA_PUBLIC_KEY / RSA_PUBLIC_KEY_2 rotation", "RSA_PUBLIC_KEY_FP verification"],
       fields=[Field("user", "Service user", "text", "SVC_DBT"), Field("encrypted", "Encrypt private key", "choice", "yes", options=["yes", "no"])],
       steps=["Run gen_keys.sh on a secured workstation.", "Store the private key in the vault.", "Run set_key.sql with the public key body; verify the fingerprint.", "Rotate with slot 2 before removing slot 1."],
       gate="Private keys never leave the vault; security owner witnesses rotation")
def gen_keypair(p, sk):
    u = ident(p.s("user"))
    enc = p.s("encrypted") == "yes"
    sh = ["#!/usr/bin/env bash", "set -euo pipefail", f"# Key pair for {u}",
          ("openssl genrsa 2048 | openssl pkcs8 -topk8 -v2 aes256 -inform PEM -out rsa_key.p8" if enc else
           "openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_key.p8 -nocrypt"),
          "openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub",
          "# Public key body without header/footer for ALTER USER:",
          "grep -v -- '-----' rsa_key.pub | tr -d '\\n' > rsa_key.pub.body",
          "# Fingerprint to compare with DESC USER:",
          "openssl rsa -pubin -in rsa_key.pub -outform DER | openssl dgst -sha256 -binary | openssl enc -base64"]
    sql = f"""{header(sk, f'key-pair for {u}')}USE ROLE SECURITYADMIN;
ALTER USER {u} SET RSA_PUBLIC_KEY = '<contents of rsa_key.pub.body>';
DESC USER {u};   -- RSA_PUBLIC_KEY_FP must equal SHA256:<fingerprint from gen_keys.sh>

-- Rotation: load the new key into slot 2, switch clients, then clear slot 1
-- ALTER USER {u} SET RSA_PUBLIC_KEY_2 = '<new key body>';
-- ALTER USER {u} UNSET RSA_PUBLIC_KEY;
"""
    conn = f"[connections.{u.lower()}]\naccount = \"[account]\"\nuser = \"{u}\"\nauthenticator = \"SNOWFLAKE_JWT\"\nprivate_key_file = \"/secure/rsa_key.p8\"\n"
    return {"files": {"gen_keys.sh": "\n".join(sh) + "\n", "set_key.sql": sql, "connections.toml": conn}, "summary": f"Key-pair kit for {u}."}


@skill(name="gen-masking", stage="foundation", agent="Policy Author", title="Generate masking policies",
       description="Create tag-based masking: a PII category tag, one tag-bound masking policy that masks each category its own way, and tags applied to classified columns.",
       snowflake=["Object tagging", "Tag-based masking policies", "IS_ROLE_IN_SESSION", "SYSTEM$CLASSIFY (optional discovery)"],
       fields=[Field("columns", "Classified columns CSV (column,category)", "table",
                     "column,category\nFLYHIGH_PRD_GOLD.CUSTOMER.DIM_CUSTOMER.CONTACT_EMAIL,email\nFLYHIGH_PRD_GOLD.CUSTOMER.DIM_CUSTOMER.CONTACT_PHONE,phone\nFLYHIGH_PRD_GOLD.WORKFORCE.DIM_EMPLOYEE.EMPLOYEE_NAME,name\nFLYHIGH_PRD_GOLD.WORKFORCE.DIM_EMPLOYEE.NATIONAL_ID,national_id"),
               Field("unmask_roles", "Roles that see clear values (one per line)", "lines", "FR_DATA_STEWARD\nFR_HR_ADMIN"),
               Field("policy_schema", "Policy schema", "text", "GOVERNANCE.POLICIES")],
       steps=["Optionally run SYSTEM$CLASSIFY to propose categories.", "Confirm categories with the data owner.", "Apply masking.sql; test with /test-rls style role checks."],
       gate="Data owner approves categories; FOR JOINT REVIEW with privacy")
def gen_masking(p, sk):
    sch, rows = p.s("policy_schema"), p.table("columns")
    roles = " OR ".join(f"IS_ROLE_IN_SESSION({lit(ident(r))})" for r in p.lines("unmask_roles")) or "FALSE"
    masks = {"email": "REGEXP_REPLACE(val, '^[^@]+', '*****')", "phone": "'***-***-' || RIGHT(val, 4)",
             "name": "LEFT(val, 1) || '****'", "national_id": "'***-**-' || RIGHT(val, 4)", "default": "'*** MASKED ***'"}
    cats = sorted({r["category"].lower() for r in rows})
    whens = "\n".join(f"       WHEN SYSTEM$GET_TAG_ON_CURRENT_COLUMN('{sch}.PII_TYPE') = {lit(c)} THEN {masks.get(c, masks['default'])}" for c in cats)
    sql = [header(sk, "tag-based masking"), "USE ROLE SECURITYADMIN;",
           f"CREATE DATABASE IF NOT EXISTS {sch.split('.')[0]};", f"CREATE SCHEMA IF NOT EXISTS {sch};",
           f"CREATE TAG IF NOT EXISTS {sch}.PII_TYPE ALLOWED_VALUES {', '.join(lit(c) for c in cats)} COMMENT = 'PII category';",
           f"""
-- One STRING policy per tag: a tag can carry one masking policy per data type, so the category is read from the tag value
CREATE OR REPLACE MASKING POLICY {sch}.MP_PII_STRING AS (val STRING) RETURNS STRING ->
  CASE WHEN {roles} THEN val
{whens}
       ELSE {masks['default']} END;

ALTER TAG {sch}.PII_TYPE SET MASKING POLICY {sch}.MP_PII_STRING;"""]
    sql.append("\n-- Tag the classified columns")
    for r in rows:
        parts = r["column"].split(".")
        tbl, col = ".".join(parts[:-1]), parts[-1]
        sql.append(f"ALTER TABLE {tbl} MODIFY COLUMN {col} SET TAG {sch}.PII_TYPE = {lit(r['category'].lower())};")
    test = header(sk, "verify masking") + "".join(
        f"SELECT * FROM TABLE(INFORMATION_SCHEMA.POLICY_REFERENCES(REF_ENTITY_NAME => {lit('.'.join(r['column'].split('.')[:-1]))}, REF_ENTITY_DOMAIN => 'table'));\n" for r in rows[:2])
    return {"files": {"masking.sql": "\n".join(sql) + "\n", "verify_masking.sql": test},
            "summary": f"{len(rows)} columns tagged across {len(cats)} categories.",
            "notes": ["One tag-bound STRING policy evaluates the category, because a tag can hold only one masking policy per data type."]}


@skill(name="gen-rls", stage="foundation", agent="Policy Author", title="Generate row access policies",
       description="Create an entitlement mapping table and a row access policy so each role sees only its own customers or sites (e.g. the customer portal).",
       snowflake=["Row access policies", "Entitlement mapping table", "IS_ROLE_IN_SESSION / CURRENT_ROLE", "POLICY_CONTEXT for testing"],
       fields=[Field("table", "Protected table", "text", "FLYHIGH_PRD_GOLD.CUSTOMER.FACT_ORDER_RELEASE"),
               Field("column", "Entitlement column", "text", "CUSTOMER_ID"),
               Field("policy_schema", "Policy schema", "text", "GOVERNANCE.POLICIES"),
               Field("admin_roles", "Roles that see all rows", "lines", "FR_EXEC\nFR_DATA_ENG"),
               Field("entitlements", "Entitlements CSV (role,value)", "table", "role,value\nFR_PORTAL_ACME,C-1001\nFR_PORTAL_GLOBEX,C-2002\nFR_DC_OPS,*")],
       steps=["Load entitlements from the source of truth (CRM / contract system).", "Apply rls.sql; test every persona with /test-rls.", "Use the same policy on every table carrying the column."],
       gate="Data owner signs off each persona's visible rows")
def gen_rls(p, sk):
    sch, col, tbl = p.s("policy_schema"), ident(p.s("column")), p.s("table")
    admins = " OR ".join(f"IS_ROLE_IN_SESSION({lit(ident(r))})" for r in p.lines("admin_roles")) or "FALSE"
    pol = f"{sch}.RAP_{col}"
    rows = p.table("entitlements")
    sql = f"""{header(sk, f'row access on {col}')}USE ROLE SECURITYADMIN;
CREATE SCHEMA IF NOT EXISTS {sch};
CREATE TABLE IF NOT EXISTS {sch}.ENTITLEMENT_{col} (ROLE_NAME VARCHAR, ENTITLED_VALUE VARCHAR, UPDATED_AT TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP());
INSERT INTO {sch}.ENTITLEMENT_{col} (ROLE_NAME, ENTITLED_VALUE) VALUES
  {(','+chr(10)+'  ').join(f"({lit(ident(r['role']))}, {lit(r['value'])})" for r in rows)};

CREATE OR REPLACE ROW ACCESS POLICY {pol} AS ({col.lower()} VARCHAR) RETURNS BOOLEAN ->
  {admins}
  OR EXISTS (SELECT 1 FROM {sch}.ENTITLEMENT_{col} e
             WHERE IS_ROLE_IN_SESSION(e.ROLE_NAME)
               AND (e.ENTITLED_VALUE = {col.lower()} OR e.ENTITLED_VALUE = '*'));

ALTER TABLE {tbl} ADD ROW ACCESS POLICY {pol} ON ({col});
"""
    return {"files": {"rls.sql": sql}, "summary": f"Row access on {tbl}.{col} for {len(rows)} entitlements."}
