"""Persona lens enforcement.

Every request carries the persona in the `X-Persona` header. The persona maps to a lens
(sales or delivery) in `lens_role`; `access_rule` decides which screens and pursuit stages
each lens can open. Rules live in the database so they can be tuned without code changes.

Note: this is a role lens, not authentication. Put SSO in front of the API and derive the
persona from the identity provider's group claim in production.
"""
from fastapi import Depends, Header, HTTPException

from .db import one, q


def persona(x_persona: str | None = Header(default=None)) -> dict:
    if not x_persona:
        raise HTTPException(401, "Choose a persona first (X-Persona header).")
    row = one("SELECT * FROM lens_role WHERE code=%s", (x_persona,))
    if not row:
        raise HTTPException(401, f"Unknown persona '{x_persona}'.")
    return row


def allowed(resource: str, code: str, lens: str) -> bool:
    r = one(f"SELECT {lens} AS ok FROM access_rule WHERE resource=%s AND code=%s", (resource, code)) if lens in ("sales", "delivery") else None
    return bool(r and r["ok"])


def allowed_codes(resource: str, lens: str) -> set[str]:
    return {r["code"] for r in q(f"SELECT code FROM access_rule WHERE resource=%s AND {lens}", (resource,))}


def deny(what: str, lens: str):
    other = "delivery" if lens == "sales" else "sales"
    raise HTTPException(403, f"{what} is not available in the {lens} lens. It belongs to the {other} lens.")


def screen(code: str):
    """Dependency factory: the persona's lens must be allowed to open this screen."""
    def dep(p: dict = Depends(persona)) -> dict:
        if not allowed("screen", code, p["lens"]):
            label = one("SELECT label FROM access_rule WHERE resource='screen' AND code=%s", (code,))
            deny(label["label"] if label else code, p["lens"])
        return p
    return dep


def require_stage(code: str, p: dict):
    if not allowed("pursuit_stage", code, p["lens"]):
        label = one("SELECT label FROM access_rule WHERE resource='pursuit_stage' AND code=%s", (code,))
        deny(f"Pursuit stage {label['label'] if label else code}", p["lens"])


def stage_code_for_num(num: int) -> str | None:
    r = one("SELECT code FROM pursuit_stage WHERE num=%s", (num,))
    return r["code"] if r else None
