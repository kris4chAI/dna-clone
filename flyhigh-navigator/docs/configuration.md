# Configuration

All settings are optional and live in `.env` at the root of the folder. `docker compose` reads that file automatically. Copy `.env.example` to `.env` to start. After any change, run `docker compose up -d`, which recreates the app with the new settings.

## LLM of choice

| Variable | Meaning | Default |
|---|---|---|
| `LLM_PROVIDER` | `anthropic`, `openai`, `azure`, `gemini` or `openai_compatible` | detected from the key variables |
| `LLM_API_KEY` | API key for the provider (blank is fine for a local `openai_compatible` server) | none |
| `LLM_MODEL` | Model, or the deployment name for Azure | per provider: `claude-sonnet-4-5`, `gpt-4o-mini`, `gemini-2.0-flash`, `llama3.1` |
| `LLM_BASE_URL` | Azure endpoint, or the base URL of an OpenAI-compatible server | none |
| `AZURE_OPENAI_API_VERSION` | Azure API version | `2024-06-01` |
| `CHAT_USE_LLM` | `false` keeps the chat guide rule-based even when an LLM is set | `true` |

You can also use the provider-specific variables, which are detected automatically: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `AZURE_OPENAI_API_KEY` with `AZURE_OPENAI_ENDPOINT`.

**What the LLM is used for:**

- **Chat guide:** it rephrases the rule-based answer. It only sees context already filtered to your persona lens.
- **Skills studio:** **Draft with LLM** sends the skill's SKILL.md as the system prompt, plus the inputs and the deterministic draft.

**Without an LLM:** use **Copy prompt for your LLM** to paste the same prompt into any assistant.

**Local models:** run Ollama on your machine and set `LLM_PROVIDER=openai_compatible` and `LLM_BASE_URL=http://host.docker.internal:11434/v1`. The compose file already maps `host.docker.internal`.

## App

| Variable | Meaning | Default |
|---|---|---|
| `FLYHIGH_PORT` | Port on your machine | `8080` |
| `POSTGRES_PASSWORD` | Database password. It is set when the volume is first created: change it before the first start, or run `docker compose down -v` to recreate | `flyhigh` |
| `RESET_DB` | `true` reloads all seed content on the next start and drops curated edits. Set it back to `false` afterwards | `false` |

## Snowflake DEV connection (optional)

The skills studio generates Snowflake SQL without any connection. To let delivery personas execute reviewed SQL from the app:

1. Generate a key pair with the `/gen-keypair` skill. Register the public key on a DEV service user. Save the private key as `secrets/rsa_key.p8`. The `secrets/` folder is mounted read-only and is never copied into the image.
2. Set these variables in `.env`:
   - `SNOWFLAKE_ACCOUNT`
   - `SNOWFLAKE_USER`
   - `SNOWFLAKE_ROLE`
   - `SNOWFLAKE_WAREHOUSE`
   - optionally `SNOWFLAKE_DATABASE`
   - `SNOWFLAKE_PRIVATE_KEY_FILE=/srv/secrets/rsa_key.p8` (and `SNOWFLAKE_PRIVATE_KEY_FILE_PWD` if the key is encrypted), or `SNOWFLAKE_PASSWORD`
   - `SNOWFLAKE_ALLOW_EXECUTE=true`
3. Run `docker compose up -d`.

Every execution needs a "a person reviewed this SQL" confirmation, runs with `QUERY_TAG = 'flyhigh-navigator'`, and is logged in the `skill_execution` table. Point the connection at a DEV account only.

## TAF data checks: Snowflake and Databricks engines (optional)

The assurance workbench runs TAF data checks on three engines (Execution > Data checks run):

- **Simulator**: no setup. Compiles the real Snowflake SQL and returns deterministic outcomes.
- **Snowflake**: uses the DEV connection above, including `SNOWFLAKE_ALLOW_EXECUTE=true`. Only assurance personas can start runs.
- **Databricks**: submits the TAF notebook chain as a one-time job and reads the Unity Catalog report views ([view contract](taf/taf_app_views.sql)). Set in `.env`:
  - `DATABRICKS_HOST` and either `DATABRICKS_TOKEN` or `DATABRICKS_CLIENT_ID` and `DATABRICKS_CLIENT_SECRET`
  - optionally `APP_TAF_ENVIRONMENT` (dev, tst, stg, prd; otherwise detected from the host or `APP_UC_CREDENTIAL_NAME`), `APP_TAF_CATALOG` (default `taf_<env>`), `APP_TAF_CATALOG_PREFIX`, `APP_TAF_SCHEMA` (default `raw`), `APP_TAF_HTTP_PATH` (SQL warehouse; auto-discovered when blank), `APP_TAF_NOTEBOOK_DIR`, `APP_TAF_LOG_DIR`, `APP_TAF_RUN_AS_SP`
  - health thresholds `APP_TAF_MASS_FAIL_PCT` (default 25) and `APP_TAF_STRANDED_HOURS` (default 12)
  - `TAF_SCENARIOS_FILE`: a JSON file of extra read-only health scenarios (each must be one SELECT or WITH and state a caveat)

Blank values and `__PLACEHOLDER__` values fall back to the dev defaults. For deactivated cases to load as `Not_Run` on Databricks, apply the [loader change](taf/loader-integration.md).

## Assurance settings: connection credentials

Settings > Connections stores LLM, ALM, storage, DB and parser connections in the database. Secret fields (API keys, passwords, tokens, service-account JSON) are encrypted with a Fernet key before they are stored, and the API only ever returns a masked hint such as `••••7890`. The key comes from, in order:

1. `SETTINGS_SECRET_KEY` in `.env`;
2. `secrets/settings.key` (the read-only `./secrets` mount);
3. a key generated on first use in the `appdata` volume (`/srv/data/settings.key`).

Back the key up with the database: without it, saved credentials cannot be decrypted and have to be re-entered. Files uploaded to local storage connections are also kept in the `appdata` volume. Settings tables are not dropped when the content is reseeded, so connections survive upgrades and `RESET_DB=true`.

Test Connection calls the service with the saved credentials (for example `GET /v1/models` for an LLM, the project endpoint for Jira or Azure DevOps, `SELECT version()` for PostgreSQL). AWS access-key and S3 checks need the AWS SDK, which the image does not include, so those are saved and reported as not verified. MySQL tests need `pymysql`.

## Corporate networks

The image build downloads base images (Docker Hub), npm packages and Python wheels. Behind a proxy or a registry mirror:

```bash
docker compose build --build-arg PYTHON_IMAGE=<mirror>/python:3.12-slim --build-arg NODE_IMAGE=<mirror>/node:20-slim \
  --build-arg HTTPS_PROXY=http://proxy:port --build-arg HTTP_PROXY=http://proxy:port
docker compose up -d
```

For PostgreSQL, change `image:` under `db` in `docker-compose.yml` to your mirror's `postgres:16-alpine`.

Once the image is built, the app makes no outbound calls of its own. The UI fonts are bundled. The only outbound calls are to the LLM and to Snowflake, and only when you configure them.
