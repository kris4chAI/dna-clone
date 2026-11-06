---
name: "sf-gen-keypair"
description: "Produce the key generation script, the ALTER USER statements and a rotation procedure for service users (keys are generated locally, never by the app). Delivery skill /gen-keypair for the foundation stage; emits Snowflake-ready artefacts for human review."
---

# Generate key-pair auth (/gen-keypair)

**Stage:** foundation · **Agent:** Auth Designer · **Human gate:** Private keys never leave the vault; security owner witnesses rotation

Produce the key generation script, the ALTER USER statements and a rotation procedure for service users (keys are generated locally, never by the app).

## When to use

Use this skill when the delivery pod reaches the foundation stage and needs the artefacts below. The skill is deterministic: the same inputs always produce the same files. It never connects to Snowflake itself; people review the output and apply it.

## Inputs

| Key | Meaning | Kind |
|---|---|---|
| `user` | Service user | text |
| `encrypted` | Encrypt private key | choice |

`lines` = one item per line · `table` = CSV with a header row. A worked example is in `examples/params.json`.

## How to run

```bash
python scripts/run.py --params examples/params.json --out out/
snow sql -f out/<file>.sql -c dev        # apply in DEV only, after review
```

In the FlyHigh Navigator app: Skills studio → `/gen-keypair` → fill the form → Generate. Delivery personas with a configured connection can execute reviewed SQL in DEV from the app.

## Steps for the agent

1. Run gen_keys.sh on a secured workstation.
2. Store the private key in the vault.
3. Run set_key.sql with the public key body; verify the fingerprint.
4. Rotate with slot 2 before removing slot 1.

## Snowflake features used

- RSA_PUBLIC_KEY / RSA_PUBLIC_KEY_2 rotation
- RSA_PUBLIC_KEY_FP verification

## Outputs

- `gen_keys.sh`
- `set_key.sql`
- `connections.toml`

## Guardrails

- Agents draft; the human gate above approves. Nothing reaches STG or PRD without an approved pull request.
- Never write secrets, tokens or private keys into generated files or the repo.
- Stamp anything not validated with the client (ILLUSTRATIVE, INDICATIVE, FOR JOINT REVIEW).
- Parity is proven by reconciliation and tests, not by the generator.
