"""Render a SKILL.md for a delivery skill from its registry entry."""
import json

from . import run


def render(sk) -> str:
    sample = run(sk.name, {})
    inputs = "\n".join(f"| `{f.key}` | {f.label} | {f.kind} |" for f in sk.fields)
    files = "\n".join(f"- `{n}`" for n in sample["files"])
    steps = "\n".join(f"{i}. {s}" for i, s in enumerate(sk.steps, 1))
    feats = "\n".join(f"- {x}" for x in sk.snowflake)
    return f"""---
name: "{sk.package}"
description: "{sk.description} Delivery skill /{sk.name} for the {sk.stage} stage; emits Snowflake-ready artefacts for human review."
---

# {sk.title} (/{sk.name})

**Stage:** {sk.stage} · **Agent:** {sk.agent} · **Human gate:** {sk.gate}

{sk.description}

## When to use

Use this skill when the delivery pod reaches the {sk.stage} stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
{inputs}

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/{sk.name}` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

{steps}

## Snowflake features used

{feats}

## Outputs

{files}

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
"""


def example_params(sk) -> str:
    return json.dumps(sk.defaults(), indent=2)
