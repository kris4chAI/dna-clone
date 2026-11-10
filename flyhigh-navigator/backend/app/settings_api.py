"""Assurance workbench settings: asset management and connections.

Assets are the workbench components (test case generator, test data generator, self-healing ...).
Each asset needs one or more connection kinds (LLM, ALM, Storage, DB, Parser) and can be switched on
or off. Connections are added per kind; LLM and parser connections are then assigned to all assets
at once or per asset ("Configure connection").

Credentials never leave the server in clear text: secret fields are encrypted with Fernet before
they are stored and the API only returns a masked hint. The key comes from SETTINGS_SECRET_KEY,
then /srv/secrets/settings.key (read-only mount), then a key generated once in the data folder
(a separate volume, never the database). LLM, Snowflake and Databricks settings that come from
.env are shown as read-only "from .env" connections.
"""
from __future__ import annotations

import base64
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from . import llm
from .access import screen

router = APIRouter(prefix="/api/assurance/settings")
SETTINGS = screen("aw_settings")
KINDS = ("llm", "alm", "storage", "db", "parser")
KIND_LABEL = {"llm": "LLM", "alm": "ALM", "storage": "Storage", "db": "DB", "parser": "Parser"}

# ---------------------------------------------------------------------------
# Assets: (code, name, colour, needs, description, screen, tab)
# ---------------------------------------------------------------------------
ASSETS = [
    ("test_data_generator", "Test Data Generator", "#1f4b4f", ["llm", "db", "storage"],
     "Builds scenario-specific synthetic test data (valid, boundary, invalid and masked rows) from the data model, a live database or a schema file.", "aw_design", "data"),
    ("keyword_framework", "Keyword Driven Framework", "#e8b931", ["llm"],
     "Lets testers compose reusable test cases from business-friendly keywords instead of hand-written scripts.", "aw_design", "scripts"),
    ("execution_report", "Test Execution Report", "#d94b4b", ["llm"],
     "Near-real-time execution visibility: results, status, failures and coverage for every cycle.", "aw_execution", "report"),
    ("high_impact_cases", "High Impacted Test Cases", "#9b2fae", ["llm", "storage"],
     "Compares changed source code with the test suite to find the cases most affected by a change and the coverage that is missing.", "aw_maintenance", ""),
    ("test_case_generator", "Test Case Generator", "#3b3b44", ["llm", "alm", "storage", "parser"],
     "Generates functional, edge and negative test cases with steps and expected results from user stories, ALM items and requirement documents.", "aw_design", "cases"),
    ("report_summarizer", "Test Report Summarizer", "#2f2f8f", ["llm"],
     "Turns large volumes of results into concise quality insights: trends, failures, defects and release readiness.", "aw_analytics", "feature"),
    ("failure_analyzer", "Test Failure Analyzer", "#2b6cb0", ["llm"],
     "Finds the likely root cause of each failure and recommends the fix that goes into failure triage.", "aw_analytics", "triage"),
    ("api_automation", "API Automation", "#0f766e", ["llm"],
     "Automated functional, integration, regression and negative API tests with reusable validations.", "aw_execution", "manage"),
    ("mobile_automation", "Mobile Automation", "#b45309", ["llm"],
     "Generates and runs automated tests for mobile apps across devices and platforms.", "aw_execution", "devices"),
    ("script_capture", "Test Script Capture", "#475569", ["llm", "alm", "storage", "parser"],
     "Records application workflows and turns the captured steps into automation-ready scripts.", "aw_design", "scripts"),
    ("self_healing", "Self-Healing", "#16a34a", ["llm"],
     "Adapts scripts when UI elements or locators change, so cosmetic changes do not fail the run.", "aw_execution", "manage"),
    ("requirement_analyzer", "Requirement Analyzer", "#7c3aed", ["llm", "alm", "storage", "parser"],
     "Reviews user stories and requirements for ambiguity, gaps and inconsistencies, with a clarity score and suggested rewrites.", "aw_design", "stories"),
    ("data_checks", "Data Checks (TAF)", "#0e7490", ["db"],
     "TAF column, template and SQL assertions on the lakehouse; runs on the Simulator, Snowflake or Databricks engine.", "aw_execution", "taf"),
]
ASSET_NAMES = {a[0]: a[1] for a in ASSETS}

# ---------------------------------------------------------------------------
# Connection form specification (served to the UI, also used to validate)
# ---------------------------------------------------------------------------
def F(key, label, type="text", required=False, placeholder="", options=None, when=None, default=None, secret=False, help=""):
    return {k: v for k, v in dict(key=key, label=label, type=type, required=required, placeholder=placeholder, options=options,
                                   when=when, default=default, secret=secret or type in ("password", "secret_text"), help=help).items() if v not in (None, "")}

CLAUDE = ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5", "claude-fable-5-1", "claude-opus-5", "claude-sonnet-5"]
GPT = ["gpt-5.4", "gpt-5.2", "gpt-5.1", "gpt-5", "gpt-5-mini", "o3", "o1", "gpt-4.1-mini"]
MODEL = lambda opts: F("model", "Model", "model", options=opts, placeholder="Select or type a model")
KEY = F("api_key", "API Key", "password", True, "Add API key")

SPEC: Dict[str, Dict[str, Any]] = {
    "llm": {"label": "LLM Connections", "add": "Add New LLM Connection", "configurable": True, "providers": {
        "anthropic": {"label": "Anthropic", "fields": [MODEL(CLAUDE), KEY]},
        "openai": {"label": "Open AI", "fields": [MODEL(GPT), KEY]},
        "azure_openai": {"label": "Azure Open AI", "fields": [MODEL(GPT), F("endpoint", "Azure Endpoint", required=True, placeholder="https://<resource>.openai.azure.com"),
                                                           F("api_version", "API Version", placeholder="e.g. 2025-04-01-preview"), KEY,
                                                           F("deployment", "Deployment Name", required=True, placeholder="Add deployment name")]},
        "gemini": {"label": "Google - Gemini", "fields": [MODEL(["gemini-3-pro", "gemini-2.5-pro", "gemini-2.5-flash"]), KEY]},
        "groq": {"label": "Groq", "fields": [MODEL(["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "qwen/qwen3-32b"]), KEY]},
        "vertex": {"label": "Google - Vertex AI", "fields": [MODEL(["gemini-3-pro", "gemini-2.5-pro", "claude-opus-5-5", "claude-sonnet-5-5"]),
                                                            F("project_id", "Project ID", required=True, placeholder="GCP project id"),
                                                            F("location", "Location", required=True, placeholder="e.g. us-central1"),
                                                            F("service_account_json", "Service account key (JSON)", "secret_text", True, "Paste the service account JSON")]},
        "bedrock": {"label": "AWS - Bedrock", "fields": [MODEL(["us.anthropic.claude-opus-5-5", "us.anthropic.claude-sonnet-5-5", "us.anthropic.claude-haiku-5-5", "amazon.nova-pro-v1:0"]),
                                                        F("auth_type", "Authentication Type", "select", True, options=[["access_key", "Access Key / Secret Key"], ["bearer", "Bearer Token"]], default="access_key"),
                                                        F("region", "Region Name", required=True, placeholder="e.g. us-east-1"),
                                                        F("access_key_id", "AWS Access Key ID", "password", True, "Add AWS access key id", when={"auth_type": "access_key"}),
                                                        F("secret_key", "AWS Secret Key", "password", True, "Add AWS secret key", when={"auth_type": "access_key"}),
                                                        F("bearer_token", "Bearer Token", "password", True, "Add Bedrock API key", when={"auth_type": "bearer"})]},
        "self_hosted": {"label": "Self Hosted LLM", "fields": [MODEL(["llama3.3", "qwen3", "mistral-large"]),
                                                              F("base_url", "Base URL", required=True, placeholder="e.g. http://host.docker.internal:11434/v1"),
                                                              F("api_key", "API Key", "password", False, "Optional")]},
    }},
    "alm": {"label": "ALM Connections", "add": "Add New ALM Connection", "providers": {
        p: {"label": l, "fields": [F("project", "Project", required=True, placeholder=ph), F("base_url", "Base URL", required=True, placeholder=url),
                                   F("username", "Username", required=True, placeholder="Add username"), KEY]}
        for p, l, ph, url in [("jira", "Jira", "Project key, e.g. FLY", "https://<site>.atlassian.net"),
                              ("rally", "Rally", "Project name", "https://rally1.rallydev.com"),
                              ("azure_devops", "Azure DevOps", "Project name", "https://dev.azure.com/<organization>")]}},
    "storage": {"label": "Storage Connections", "add": "Add New Storage Connection", "providers": {
        "local": {"label": "Local", "fields": [F("target_asset", "Target Asset", "asset", True), F("file", "Upload file", "file", True, help="Requirement documents, schema files, recordings or source archives")]},
        "s3": {"label": "S3", "fields": [F("target_asset", "Target Asset", "asset", True), F("bucket", "Bucket", required=True, placeholder="bucket name"),
                                         F("prefix", "Prefix", placeholder="optional/folder/"), F("region", "Region", required=True, placeholder="e.g. us-east-1"),
                                         F("access_key_id", "Access Key ID", "password", True), F("secret_key", "Secret Key", "password", True)]},
    }},
    "db": {"label": "DB Connections", "add": "Add New DB Connection", "providers": {
        "postgresql": {"label": "PostgreSQL", "fields": [F("host", "Host", required=True, placeholder="e.g. localhost"), F("port", "Port", required=True, default="5432", placeholder="e.g. 5432"),
                                                        F("database", "Database", required=True, placeholder="Database name"), F("username", "Username", required=True, placeholder="DB user"),
                                                        F("password", "Password", "password", True, "DB password"), F("schema", "Schema", placeholder="e.g. public (optional)")]},
        "mysql": {"label": "MySQL", "fields": [F("host", "Host", required=True, placeholder="e.g. localhost"), F("port", "Port", required=True, default="3306", placeholder="e.g. 3306"),
                                              F("database", "Database", required=True, placeholder="Database name"), F("username", "Username", required=True, placeholder="DB user"),
                                              F("password", "Password", "password", True, "DB password")]},
        "snowflake": {"label": "Snowflake", "fields": [F("account", "Account", required=True, placeholder="orgname-account"), F("warehouse", "Warehouse", required=True),
                                                      F("database", "Database", required=True), F("schema", "Schema", placeholder="optional"), F("role", "Role", placeholder="optional"),
                                                      F("username", "Username", required=True), F("password", "Password", "password", True,
                                                      help="For key-pair auth use the .env connection (key file in ./secrets)")]},
    }},
    "parser": {"label": "Parser Connections", "add": "Add New Parser Connection", "configurable": True, "providers": {
        "llama": {"label": "Llama", "fields": [KEY]},
    }},
}


def _fields(kind: str, provider: str) -> List[dict]:
    try:
        return SPEC[kind]["providers"][provider]["fields"]
    except KeyError:
        raise HTTPException(400, f"Unknown {kind} provider {provider!r}")


def _active(fields: List[dict], values: Dict[str, Any]) -> List[dict]:
    return [f for f in fields if not f.get("when") or all(str(values.get(k, "")) == v for k, v in f["when"].items())]


# ---------------------------------------------------------------------------
# Data folder and secret encryption
# ---------------------------------------------------------------------------
def data_dir() -> Path:
    d = Path(os.environ.get("FLYHIGH_DATA") or Path(os.environ.get("FLYHIGH_HOME", Path(__file__).resolve().parents[2])) / "data")
    d.mkdir(parents=True, exist_ok=True)
    return d


_fernet = None


def fernet():
    global _fernet
    if _fernet is None:
        from cryptography.fernet import Fernet  # installed with snowflake-connector-python
        key = (os.environ.get("SETTINGS_SECRET_KEY") or "").strip()
        src = "SETTINGS_SECRET_KEY"
        mounted = Path(os.environ.get("FLYHIGH_SECRETS", "/srv/secrets")) / "settings.key"
        if not key and mounted.exists():
            key, src = mounted.read_text().strip(), str(mounted)
        if not key:
            p = data_dir() / "settings.key"
            if not p.exists():
                p.write_bytes(Fernet.generate_key())
                os.chmod(p, 0o600)
            key, src = p.read_text().strip(), "data/settings.key"
        try:
            _fernet = (Fernet(key.encode()), src)
        except ValueError:
            raise HTTPException(500, f"The settings secret key from {src} is not a valid Fernet key")
    return _fernet


def encrypt(d: Dict[str, str]) -> Optional[str]:
    return fernet()[0].encrypt(json.dumps(d).encode()).decode() if d else None


def decrypt(token: Optional[str]) -> Dict[str, str]:
    if not token:
        return {}
    try:
        return json.loads(fernet()[0].decrypt(token.encode()))
    except Exception:
        return {}


def mask(v: str) -> str:
    v = str(v or "")
    return "••••" + v[-4:] if len(v) > 8 else "••••"


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------
def seed_settings(x):
    for i, (code, name, color, needs, desc, scr, tab) in enumerate(ASSETS):
        x.one("""INSERT INTO aw_asset(code,name,color,needs,description,screen,tab,enabled,seq) VALUES (%s,%s,%s,%s,%s,%s,%s,true,%s)
                 ON CONFLICT (code) DO UPDATE SET name=EXCLUDED.name, color=EXCLUDED.color, needs=EXCLUDED.needs,
                 description=EXCLUDED.description, screen=EXCLUDED.screen, tab=EXCLUDED.tab, seq=EXCLUDED.seq""", (code, name, color, needs, desc, scr, tab, i + 1))
    if llm.status().get("ready") and not x.q("SELECT 1 FROM aw_conn_assign WHERE kind='llm'"):  # an LLM from .env serves every asset until the assurance team configures its own
        x.one("INSERT INTO aw_conn_assign(kind,asset,conn_ref) VALUES ('llm','*','env:llm') ON CONFLICT DO NOTHING")


# ---------------------------------------------------------------------------
# Read models
# ---------------------------------------------------------------------------
def _env_connections() -> List[dict]:
    """Connections configured in .env: shown read-only so the settings page tells the whole story."""
    out = []
    st = llm.status()
    if st.get("ready"):
        out.append({"id": "env:llm", "kind": "llm", "name": f"{st.get('provider')} (from .env)", "provider": st.get("provider"),
                    "provider_label": str(st.get("provider")), "config": {"model": st.get("model")}, "secrets": {"api_key": "set in .env"}, "origin": "env"})
    if os.environ.get("SNOWFLAKE_ACCOUNT"):
        out.append({"id": "env:snowflake", "kind": "db", "name": "Snowflake DEV (from .env)", "provider": "snowflake", "provider_label": "Snowflake",
                    "config": {"account": os.environ.get("SNOWFLAKE_ACCOUNT"), "warehouse": os.environ.get("SNOWFLAKE_WAREHOUSE"), "role": os.environ.get("SNOWFLAKE_ROLE"),
                               "database": os.environ.get("SNOWFLAKE_DATABASE"), "username": os.environ.get("SNOWFLAKE_USER")},
                    "secrets": {"password": "key pair in ./secrets" if os.environ.get("SNOWFLAKE_PRIVATE_KEY_FILE") else "set in .env"}, "origin": "env"})
    if os.environ.get("DATABRICKS_HOST"):
        out.append({"id": "env:databricks", "kind": "db", "name": "Databricks TAF (from .env)", "provider": "databricks", "provider_label": "Databricks",
                    "config": {"host": os.environ.get("DATABRICKS_HOST"), "catalog": os.environ.get("APP_TAF_CATALOG") or "taf_<env>"},
                    "secrets": {"token": "set in .env"}, "origin": "env"})
    return out


def _row(r: dict) -> dict:
    spec = SPEC[r["kind"]]["providers"].get(r["provider"], {"label": r["provider"], "fields": []})
    secrets = decrypt(r.pop("secret_enc", None))
    cfg = r.get("config") or {}
    r.update(id=str(r["id"]), provider_label=spec["label"], origin="app",
             secrets={k: mask(v) for k, v in secrets.items() if v},
             target_asset_name=ASSET_NAMES.get(cfg.get("target_asset", ""), ""))
    return r


def connections(x, kind: Optional[str] = None) -> List[dict]:
    rows = [_row(dict(r)) for r in x.q(f"SELECT * FROM aw_conn {'WHERE kind=%s' if kind else ''} ORDER BY kind, provider, name", (kind,) if kind else ())]
    env = [e for e in _env_connections() if not kind or e["kind"] == kind]
    return env + rows


def assignments(x) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {k: {} for k in KINDS}
    for r in x.q("SELECT kind, asset, conn_ref FROM aw_conn_assign"):
        out[r["kind"]][r["asset"]] = r["conn_ref"]
    return out


def asset_status(x) -> List[dict]:
    conns = connections(x)
    ids = {c["id"] for c in conns}
    asg = assignments(x)
    have = {k: [c for c in conns if c["kind"] == k] for k in KINDS}
    out = []
    for a in x.q("SELECT * FROM aw_asset ORDER BY seq"):
        ok = {}
        for k in a["needs"]:
            if k in ("llm", "parser"):
                ref = asg[k].get(a["code"]) or asg[k].get("*")
                ok[k] = {"ok": bool(ref and ref in ids), "via": next((c["name"] for c in conns if c["id"] == ref), None)}
            elif k == "storage":
                hit = [c for c in have[k] if (c.get("config") or {}).get("target_asset") == a["code"]]
                ok[k] = {"ok": bool(hit), "via": hit[0]["name"] if hit else None}
            else:
                ok[k] = {"ok": bool(have[k]), "via": have[k][0]["name"] if have[k] else None}
        out.append({**a, "connections": ok, "ready": all(v["ok"] for v in ok.values())})
    return out


def disabled_assets(x) -> List[str]:
    return [r["name"] for r in x.q("SELECT name FROM aw_asset WHERE NOT enabled")]


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
def _db():
    from .assurance_api import DB
    return DB


@router.get("/spec")
def get_spec(p: dict = Depends(SETTINGS)):
    return {"kinds": [{"code": k, **{kk: vv for kk, vv in SPEC[k].items() if kk != "providers"},
                       "providers": [{"code": pc, **pv} for pc, pv in SPEC[k]["providers"].items()]} for k in KINDS],
            "assets": [{"code": a[0], "name": a[1], "needs": a[3]} for a in ASSETS],
            "key_source": fernet()[1]}


@router.get("/assets")
def get_assets(p: dict = Depends(SETTINGS)):
    return {"assets": asset_status(_db())}


class AssetIn(BaseModel):
    enabled: bool


@router.put("/assets/{code}")
def put_asset(code: str, body: AssetIn, p: dict = Depends(SETTINGS)):
    r = _db().one("UPDATE aw_asset SET enabled=%s WHERE code=%s RETURNING code, enabled", (body.enabled, code))
    if not r:
        raise HTTPException(404, "Unknown asset")
    return r


@router.get("/connections")
def get_connections(kind: Optional[str] = None, p: dict = Depends(SETTINGS)):
    if kind and kind not in KINDS:
        raise HTTPException(400, "Unknown connection kind")
    x = _db()
    counts = {k: len(connections(x, k)) for k in KINDS}
    return {"rows": connections(x, kind), "counts": counts, "assignments": assignments(x)}


def _validate(kind: str, provider: str, name: str, config: Dict[str, Any], secrets: Dict[str, Any], existing: Optional[dict] = None, has_file: bool = False):
    if not name.strip():
        raise HTTPException(400, "Connection name is required")
    if not re.fullmatch(r"[\w .\-()]{1,80}", name.strip()):
        raise HTTPException(400, "Use letters, digits, spaces, dot, dash, underscore or brackets in the connection name (max 80)")
    fields = _active(_fields(kind, provider), {**config})
    known = {f["key"] for f in _fields(kind, provider)}
    for k in list(config) + list(secrets):
        if k not in known:
            raise HTTPException(400, f"Unexpected field {k!r} for {provider}")
    old = decrypt(existing.get("secret_enc")) if existing else {}
    missing = []
    for f in fields:
        if not f.get("required"):
            continue
        if f["type"] == "file":
            if not has_file and not (existing and existing.get("file_name")):
                missing.append(f["label"])
        elif f.get("secret"):
            if not (secrets.get(f["key"]) or old.get(f["key"])):
                missing.append(f["label"])
        elif not str(config.get(f["key"]) or "").strip():
            missing.append(f["label"])
    if missing:
        raise HTTPException(400, "Required: " + ", ".join(missing))
    if config.get("target_asset") and config["target_asset"] not in ASSET_NAMES:
        raise HTTPException(400, "Unknown target asset")
    if "port" in config and not str(config["port"]).isdigit():
        raise HTTPException(400, "Port must be a number")
    for k in ("base_url", "endpoint"):
        if config.get(k) and not re.match(r"https?://", str(config[k])):
            raise HTTPException(400, f"{k.replace('_', ' ').title()} must start with http:// or https://")
    if secrets.get("service_account_json"):
        try:
            json.loads(secrets["service_account_json"])
        except ValueError:
            raise HTTPException(400, "Service account key must be valid JSON")
    # keep previous secret values when a field was left blank on edit; drop secrets no longer active
    active_keys = {f["key"] for f in fields}
    merged = {k: v for k, v in {**old, **{k: v for k, v in secrets.items() if v}}.items() if k in active_keys}
    return {k: v for k, v in config.items() if k in active_keys}, merged


async def _save(kind, provider, name, config, secrets, user, conn_id=None, upload: Optional[UploadFile] = None):
    x = _db()
    existing = None
    if conn_id:
        existing = x.one("SELECT * FROM aw_conn WHERE id=%s AND kind=%s", (conn_id, kind))
        if not existing:
            raise HTTPException(404, "Connection not found")
    config, secrets = _validate(kind, provider, name, config, secrets, existing, has_file=bool(upload and upload.filename))
    if x.one("SELECT id FROM aw_conn WHERE kind=%s AND lower(name)=lower(%s) AND id <> %s", (kind, name.strip(), conn_id or 0)):
        raise HTTPException(409, f"A {KIND_LABEL[kind]} connection named {name.strip()!r} already exists")
    row = x.one("""INSERT INTO aw_conn(kind,provider,name,config,secret_enc,created_by) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id""",
                (kind, provider, name.strip(), json.dumps(config), encrypt(secrets), user)) if not conn_id else \
        x.one("""UPDATE aw_conn SET provider=%s, name=%s, config=%s, secret_enc=%s, updated_at=now(), test_status=NULL, test_message=NULL WHERE id=%s RETURNING id""",
              (provider, name.strip(), json.dumps(config), encrypt(secrets), conn_id))
    cid = row["id"]
    if upload and upload.filename:
        body = await upload.read()
        if len(body) > 25 * 1024 * 1024:
            raise HTTPException(413, "File is larger than 25 MB")
        safe = re.sub(r"[^\w.\-]+", "_", Path(upload.filename).name)[:120]
        d = data_dir() / "storage" / str(cid)
        d.mkdir(parents=True, exist_ok=True)
        for old in d.iterdir():
            old.unlink()
        (d / safe).write_bytes(body)
        x.one("UPDATE aw_conn SET file_name=%s, file_size=%s WHERE id=%s RETURNING id", (safe, len(body), cid))
    return _row(dict(x.one("SELECT * FROM aw_conn WHERE id=%s", (cid,))))


class ConnIn(BaseModel):
    provider: str
    name: str
    config: Dict[str, Any] = Field(default_factory=dict)
    secrets: Dict[str, str] = Field(default_factory=dict)


@router.post("/connections/{kind}")
async def add_connection(kind: str, body: ConnIn, p: dict = Depends(SETTINGS)):
    if kind not in KINDS or kind == "storage" and body.provider == "local":
        raise HTTPException(400, "Use the multipart form for local storage" if kind == "storage" else "Unknown connection kind")
    return await _save(kind, body.provider, body.name, body.config, body.secrets, p["code"])


@router.put("/connections/{kind}/{conn_id}")
async def edit_connection(kind: str, conn_id: int, body: ConnIn, p: dict = Depends(SETTINGS)):
    return await _save(kind, body.provider, body.name, body.config, body.secrets, p["code"], conn_id)


@router.post("/connections/storage/local")
async def add_local_storage(name: str = Form(...), target_asset: str = Form(...), conn_id: Optional[int] = Form(None),
                            file: Optional[UploadFile] = File(None), p: dict = Depends(SETTINGS)):
    return await _save("storage", "local", name, {"target_asset": target_asset}, {}, p["code"], conn_id, file)


@router.delete("/connections/{kind}/{conn_id}")
def delete_connection(kind: str, conn_id: int, p: dict = Depends(SETTINGS)):
    x = _db()
    r = x.one("DELETE FROM aw_conn WHERE id=%s AND kind=%s RETURNING id", (conn_id, kind))
    if not r:
        raise HTTPException(404, "Connection not found")
    x.one("DELETE FROM aw_conn_assign WHERE conn_ref=%s RETURNING kind", (str(conn_id),))
    d = data_dir() / "storage" / str(conn_id)
    if d.exists():
        for f in d.iterdir():
            f.unlink()
        d.rmdir()
    return {"deleted": conn_id}


class AssignIn(BaseModel):
    mode: str  # all | per_asset
    all: Optional[str] = None
    per_asset: Dict[str, str] = Field(default_factory=dict)


@router.get("/assign/{kind}")
def get_assign(kind: str, p: dict = Depends(SETTINGS)):
    if kind not in ("llm", "parser"):
        raise HTTPException(400, "Only LLM and parser connections are assigned to assets")
    x = _db()
    a = assignments(x)[kind]
    targets = [{"code": r["code"], "name": r["name"]} for r in x.q("SELECT code, name FROM aw_asset WHERE enabled AND %s = ANY(needs) ORDER BY seq", (kind,))]
    return {"mode": "all" if "*" in a or not a else "per_asset", "all": a.get("*"), "per_asset": {k: v for k, v in a.items() if k != "*"},
            "assets": targets, "options": [{"id": c["id"], "name": c["name"], "provider": c["provider_label"]} for c in connections(x, kind)]}


@router.put("/assign/{kind}")
def put_assign(kind: str, body: AssignIn, p: dict = Depends(SETTINGS)):
    if kind not in ("llm", "parser"):
        raise HTTPException(400, "Only LLM and parser connections are assigned to assets")
    x = _db()
    ids = {c["id"] for c in connections(x, kind)}
    targets = [r["code"] for r in x.q("SELECT code FROM aw_asset WHERE enabled AND %s = ANY(needs)", (kind,))]
    if body.mode == "all":
        if body.all not in ids:
            raise HTTPException(400, "Choose a connection for all assets")
        pairs = [("*", body.all)]
    elif body.mode == "per_asset":
        missing = [ASSET_NAMES[t] for t in targets if body.per_asset.get(t) not in ids]
        if missing:
            raise HTTPException(400, "All assets must have a connection configured before saving: " + ", ".join(missing))
        pairs = [(t, body.per_asset[t]) for t in targets]
    else:
        raise HTTPException(400, "mode must be all or per_asset")
    x.one("DELETE FROM aw_conn_assign WHERE kind=%s RETURNING kind", (kind,))
    for asset, ref in pairs:
        x.one("INSERT INTO aw_conn_assign(kind,asset,conn_ref) VALUES (%s,%s,%s) RETURNING kind", (kind, asset, ref))
    return get_assign(kind, p)


# ---------------------------------------------------------------------------
# Test connection
# ---------------------------------------------------------------------------
def _http(method: str, url: str, **kw) -> httpx.Response:
    with httpx.Client(timeout=8.0, follow_redirects=False) as c:
        return c.request(method, url, **kw)


def _ok(r: httpx.Response, what: str) -> tuple:
    if r.status_code < 300:
        return True, f"{what}: reachable and authorised (HTTP {r.status_code})"
    if r.status_code in (401, 403):
        return False, f"{what}: the credentials were rejected (HTTP {r.status_code})"
    return False, f"{what}: HTTP {r.status_code} {r.text[:160]}"


def run_test(kind: str, provider: str, cfg: Dict[str, Any], sec: Dict[str, str], file_name: Optional[str] = None, conn_id: Optional[str] = None) -> tuple:
    if kind == "llm":
        k = sec.get("api_key", "")
        if provider == "anthropic":
            return _ok(_http("GET", "https://api.anthropic.com/v1/models", headers={"x-api-key": k, "anthropic-version": "2023-06-01"}), "Anthropic")
        if provider == "openai":
            return _ok(_http("GET", "https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {k}"}), "OpenAI")
        if provider == "groq":
            return _ok(_http("GET", "https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {k}"}), "Groq")
        if provider == "gemini":
            return _ok(_http("GET", "https://generativelanguage.googleapis.com/v1beta/models", headers={"x-goog-api-key": k}), "Gemini")
        if provider == "azure_openai":
            url = f"{cfg['endpoint'].rstrip('/')}/openai/deployments/{cfg['deployment']}/chat/completions?api-version={cfg.get('api_version') or '2024-10-21'}"
            r = _http("POST", url, headers={"api-key": k}, json={"messages": [{"role": "user", "content": "ping"}], "max_completion_tokens": 1})
            return (True, f"Azure OpenAI deployment {cfg['deployment']} answered") if r.status_code < 300 or r.status_code == 400 and "max_completion_tokens" in r.text else _ok(r, "Azure OpenAI")
        if provider == "self_hosted":
            return _ok(_http("GET", cfg["base_url"].rstrip("/") + "/models", headers={"Authorization": f"Bearer {k}"} if k else {}), "Self-hosted LLM")
        if provider == "bedrock":
            if cfg.get("auth_type") == "bearer":
                r = _http("GET", f"https://bedrock.{cfg['region']}.amazonaws.com/foundation-models", headers={"Authorization": f"Bearer {sec.get('bearer_token', '')}"})
                return _ok(r, "Bedrock")
            return None, "Saved. Access key / secret key auth is verified on first use (SigV4 signing needs the AWS SDK, which this image does not include)."
        if provider == "vertex":
            sa = json.loads(sec.get("service_account_json") or "{}")
            ok = sa.get("type") == "service_account" and sa.get("private_key") and sa.get("client_email")
            return (None, f"Service account {sa.get('client_email')} looks valid. The token exchange happens on first use.") if ok else (False, "The JSON is not a service account key")
    if kind == "alm":
        base = cfg["base_url"].rstrip("/")
        user, key = cfg.get("username", ""), sec.get("api_key", "")
        if provider == "jira":
            return _ok(_http("GET", f"{base}/rest/api/2/project/{cfg['project']}", auth=(user, key)), f"Jira project {cfg['project']}")
        if provider == "rally":
            return _ok(_http("GET", f"{base}/slm/webservice/v2.0/subscription", headers={"ZSESSIONID": key}), "Rally")
        if provider == "azure_devops":
            return _ok(_http("GET", f"{base}/_apis/projects/{cfg['project']}?api-version=7.1", auth=(user or "", key)), f"Azure DevOps project {cfg['project']}")
    if kind == "db":
        if provider == "postgresql":
            import psycopg
            with psycopg.connect(host=cfg["host"], port=int(cfg["port"]), dbname=cfg["database"], user=cfg["username"], password=sec.get("password"), connect_timeout=6) as c:
                v = c.execute("SELECT version()").fetchone()[0]
                n = c.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema=%s", (cfg.get("schema") or "public",)).fetchone()[0]
            return True, f"Connected: {v.split(',')[0]}; {n} tables in {cfg.get('schema') or 'public'}"
        if provider == "mysql":
            try:
                import pymysql  # optional
            except ImportError:
                return None, "Saved. Install pymysql in the image to test MySQL connections from the app."
            c = pymysql.connect(host=cfg["host"], port=int(cfg["port"]), database=cfg["database"], user=cfg["username"], password=sec.get("password"), connect_timeout=6)
            c.close()
            return True, "Connected to MySQL"
        if provider == "snowflake":
            import snowflake.connector
            with snowflake.connector.connect(account=cfg["account"], user=cfg["username"], password=sec.get("password"), warehouse=cfg["warehouse"],
                                             database=cfg["database"], schema=cfg.get("schema") or None, role=cfg.get("role") or None, login_timeout=10,
                                             session_parameters={"QUERY_TAG": "flyhigh-navigator"}) as c:
                v = c.cursor().execute("SELECT CURRENT_VERSION()").fetchone()[0]
            return True, f"Connected to Snowflake {v}"
    if kind == "storage":
        if provider == "local":
            f = data_dir() / "storage" / str(conn_id) / (file_name or "")
            return (True, f"{file_name} is stored ({f.stat().st_size:,} bytes)") if file_name and f.exists() else (False, "The uploaded file is missing")
        if provider == "s3":
            r = _http("HEAD", f"https://{cfg['bucket']}.s3.{cfg['region']}.amazonaws.com/")
            if r.status_code == 404:
                return False, f"Bucket {cfg['bucket']} does not exist in {cfg['region']}"
            return None, f"Bucket {cfg['bucket']} exists (HTTP {r.status_code}). Read access is verified on first use (SigV4 signing needs the AWS SDK)."
    if kind == "parser" and provider == "llama":
        return _ok(_http("GET", "https://api.cloud.llamaindex.ai/api/v1/projects", headers={"Authorization": f"Bearer {sec.get('api_key', '')}"}), "LlamaParse")
    return None, "No test available for this connection type"


@router.post("/connections/{kind}/{conn_id}/test")
def test_connection(kind: str, conn_id: str, p: dict = Depends(SETTINGS)):
    x = _db()
    if conn_id.startswith("env:"):
        e = next((c for c in _env_connections() if c["id"] == conn_id), None)
        if not e:
            raise HTTPException(404, "Not configured in .env")
        if conn_id == "env:llm":
            ok, msg = (True, f"{e['name']} is configured; the skills studio uses it for 'Draft with LLM'")
        else:
            ok, msg = None, "Configured in .env; tested when a data-check run starts on this engine"
        return {"id": conn_id, "status": {True: "ok", False: "failed", None: "unverified"}[ok], "message": msg}
    r = x.one("SELECT * FROM aw_conn WHERE id=%s AND kind=%s", (int(conn_id), kind)) if conn_id.isdigit() else None
    if not r:
        raise HTTPException(404, "Connection not found")
    t0 = time.perf_counter()
    try:
        ok, msg = run_test(kind, r["provider"], r["config"] or {}, decrypt(r["secret_enc"]), r.get("file_name"), conn_id)
    except httpx.HTTPError as e:
        ok, msg = False, f"Could not reach the service: {type(e).__name__} {str(e)[:160]}"
    except Exception as e:  # driver errors: show the message, never the secret
        ok, msg = False, f"{type(e).__name__}: {str(e)[:200]}"
    status = {True: "ok", False: "failed", None: "unverified"}[ok]
    msg = f"{msg} · {int((time.perf_counter() - t0) * 1000)} ms"
    x.one("UPDATE aw_conn SET test_status=%s, test_message=%s, tested_at=now() WHERE id=%s RETURNING id", (status, msg, int(conn_id)))
    return {"id": conn_id, "status": status, "message": msg}
