# FlyHigh Navigator

A conversational, persona-aware workspace for the **FlyHigh** initiative: **ABC Retail**'s Snowflake modernization, delivered by **Niche Consulting**. It covers the whole lifecycle:

- **Pursuit lifecycle (sales lens):** nine gated stages from RFP signal to orals, with templates, a win room, response scoring and 9 pursuit skills.
- **Implementation lifecycle (delivery lens):** ten steps from Discover to Operate & monitor, with agents, tools and 46 Snowflake delivery skills.
- **Shared solution content:** persona journeys, insights dashboards and the logistics data model.

Everything is in this folder: the application, the skills, the templates, the seed content, the tools and the docs.

## Quick start

1. Install **Docker Desktop** (Mac, Windows or Linux) and start it.
2. Optional: copy `.env.example` to `.env` and add your LLM key (`LLM_PROVIDER` and `LLM_API_KEY`).
3. Start the app:

   ```bash
   ./start.sh            # macOS / Linux   (or: docker compose up -d --build)
   ./start.ps1           # Windows PowerShell
   ```

4. Open **http://localhost:8080** and pick a persona. Sales personas see the pursuit; delivery personas see the implementation.

On the first start, Docker builds one image (UI + API + skills + assets), starts PostgreSQL and loads all content. This takes a few minutes. Later starts take seconds and keep your edits.

```bash
docker compose logs -f app       # follow the logs
docker compose down              # stop (data is kept in the pgdata volume)
docker compose down -v           # stop and delete all data
python3 tools/smoke_test.py      # 31 end-to-end checks (all 55 skills included)
```

## The only setting you may need: your LLM

The app runs fully without an LLM. Every engine, generator and the chat guide work deterministically. With an LLM, the chat guide phrases its answers and every skill gets a **Draft with LLM** button. Set two lines in `.env`:

| Provider | `LLM_PROVIDER` | `LLM_API_KEY` | Also set |
|---|---|---|---|
| Anthropic Claude | `anthropic` | your key | `LLM_MODEL` optional (default `claude-sonnet-4-5`) |
| OpenAI | `openai` | your key | `LLM_MODEL` optional (default `gpt-4o-mini`) |
| Azure OpenAI | `azure` | your key | `LLM_BASE_URL=https://<resource>.openai.azure.com`, `LLM_MODEL=<deployment>` |
| Google Gemini | `gemini` | your key | `LLM_MODEL` optional (default `gemini-2.0-flash`) |
| Local or other (Ollama, vLLM, LM Studio, Groq…) | `openai_compatible` | blank or key | `LLM_BASE_URL=http://host.docker.internal:11434/v1`, `LLM_MODEL=llama3.1` |

Then run `docker compose up -d`. The skills studio shows the active provider. See [docs/configuration.md](docs/configuration.md) for every setting, including the optional Snowflake DEV connection.

## What's in the folder

```
flyhigh-navigator/
├── README.md                 ← you are here
├── docker-compose.yml        ← db (PostgreSQL 16) + app (UI, API, skills, assets) · one command
├── Dockerfile                ← multi-stage: builds the React UI, then the Python runtime
├── .env.example              ← LLM of choice, port, optional Snowflake connection
├── start.sh · start.ps1      ← one-click start (creates .env, builds, waits, opens the browser)
├── backend/                  ← FastAPI API: lens enforcement, pursuit, skills studio, chat, seed content
│   ├── app/                  ← main.py, access.py, pursuit_api.py, skills_api.py, chat.py, llm.py, schema.sql, seed*.py
│   └── requirements.txt      ← pinned Python dependencies (wheels for amd64 and arm64)
├── frontend/                 ← React 18 + Vite UI (fonts bundled; no external calls at runtime)
├── skills/                   ← everything the app can *do*
│   ├── README.md             ← skills catalog (55 skills)
│   ├── pursuit/              ← 9 pursuit skills (SKILL.md, source of truth)
│   ├── delivery/snowskills/  ← generator library for the 46 Snowflake delivery skills (stdlib only)
│   ├── delivery/catalog/     ← readable SKILL.md + example params per delivery skill
│   └── packages/             ← .skill packages (upload to Claude, or run standalone)
├── assets/
│   ├── templates/01…09/      ← pursuit stage templates (Word, Excel), downloadable in the app
│   └── seed/                 ← extracted template sheets and win-room sample data (pursuit_kit.json)
├── docker/entrypoint.sh      ← waits for the db, loads content on first run or upgrade, starts the server
├── tools/                    ← smoke_test.py · package_skills.py · extract_kit.py
├── docs/                     ← features · architecture · configuration · operations · persona lens
└── secrets/                  ← optional Snowflake private key (mounted read-only, never in the image)
```

## Learn more

- [docs/features.md](docs/features.md): every screen, the skills studio and the API
- [docs/persona-lens.md](docs/persona-lens.md): who sees what, and how it is enforced
- [docs/architecture.md](docs/architecture.md): components, data model and request flow
- [docs/configuration.md](docs/configuration.md): all `.env` settings (LLM, port, Snowflake, reset)
- [docs/operations.md](docs/operations.md): run, reset, upgrade, back up, troubleshoot, develop locally
- [skills/README.md](skills/README.md): the 55-skill catalog
