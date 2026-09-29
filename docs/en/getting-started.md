# Getting Started

The platform can run entirely locally, and its isolated incident demo does not require an external LLM key.

## Fastest path

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

Open:

- Web Console: `http://127.0.0.1:8000/`
- API docs: `http://127.0.0.1:8000/docs`

## Docker

```bash
cp .env.example .env
docker compose up --build
```

The Compose setup includes a readiness health check and persistent data volume.

## Offline Multi-Agent demo

Run:

```bash
python scripts/demo_incident.py
```

The scenario asks why recent import jobs failed and executes the real Data, Knowledge, Ops and Supervisor code paths using isolated data and a deterministic Fake LLM.

Use JSON output when you want machine-readable results:

```bash
python scripts/demo_incident.py --json
```

## Model runtime

Natural-language features use an OpenAI-compatible endpoint:

```text
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=
LLM_MODEL=
EMBEDDING_MODEL=
```

Local compatible endpoints can leave `LLM_API_KEY` empty.

## Authentication

For a shared demo environment:

```text
AUTH_ENABLED=true
AUTH_TOKENS={"user-token":"alice:user","operator-token":"operator:operator","approver-token":"reviewer:approver","admin-token":"admin:admin"}

CONSOLE_USERNAME=demo
CONSOLE_PASSWORD=demo
CONSOLE_ROLE=admin
SESSION_MAX_AGE_SECONDS=43200
```

The Web Console uses an HttpOnly session cookie. API clients may still use Bearer tokens.

## Next

- [Architecture](/en/ARCHITECTURE)
- [Demo Guide](/en/DEMO)
- [Interview Guide](/en/INTERVIEW)
