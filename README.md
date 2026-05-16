# ForgeMind

ForgeMind is an AI-powered men's mental health mobile app focused on calm, private, practical support. The MVP uses React Native CLI, FastAPI, PostgreSQL with pgvector, OpenAI APIs, and a Next.js admin dashboard.

## Structure

- `backend/` FastAPI API, safety, guidance, memory ranking, auth and subscription stubs, prompts, tests, Alembic migrations
- `mobile/` React Native CLI TypeScript scaffold with onboarding-style app screens and bottom navigation
- `admin/` Next.js TypeScript dashboard scaffold for guidance, users, memories, safety events, prompts, and metrics
- `infra/` Prometheus and Grafana provisioning
- `docs/` source-of-truth product, agent, rules, design, and implementation docs

## Local Setup

Start infrastructure:

```bash
docker compose up -d postgres prometheus grafana
```

Install Python dependencies with `uv`. If `uv` is not installed yet:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

For LAN testing with a phone, use your machine's `192.168.0.x` address:

```bash
make backend HOST=192.168.0.x
make frontend HOST=192.168.0.x
make mobile
```

Default app ports:

- Backend: `8005`
- Admin: `3005`
- React Native Metro: `8085`

Separate test server ports are above `20000`:

- Backend test server: `28005`
- Admin test server: `23005`
- Metro test server: `28085`

Run backend:

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 192.168.0.x --port 8005
```

Run backend tests:

```bash
cd backend
uv run pytest
```

Run admin:

```bash
cd admin
npm install
npm run dev
```

The admin dashboard runs on `http://192.168.0.x:3005` when started through `make frontend`.

Run mobile:

```bash
cd mobile
npm install
npm run start -- --host 0.0.0.0 --port 8085
npm run android -- --port 8085
```

Metro runs on port `8085`. Use your actual `192.168.0.x` LAN IP so a physical Android phone can reach the backend and Metro server.

## API Highlights

- `GET /health`
- `POST /auth/login`
- `POST /chat`
- `POST /safety/classify`
- `GET/POST/PUT/DELETE /guidance/rules`
- `GET /memories`
- `POST /subscriptions/validate`
- `GET /metrics`

## Memory Retrieval

The MVP follows the required flow:

1. create an embedding from the user message
2. search pgvector for top 20 candidates
3. filter inactive, archived, unsafe, expired, or low-confidence memories
4. re-rank by `similarity * 0.50 + importance * 0.25 + recency * 0.15 + active_status * 0.10`
5. inject only the top 3-5 memories into prompts

The pure ranking/filtering code is implemented in `backend/app/services/memory.py`; database-backed vector search is represented in the migration and ready to connect to the OpenAI embedding call.

## Credential TODOs

- Add real Google identity-token verification credentials.
- Add real Apple identity-token verification credentials.
- Add StoreKit server API credentials.
- Add Google Play Billing API credentials.
- Add `OPENAI_API_KEY` for production AI and embedding calls.
- Add `SENTRY_DSN` and `POSTHOG_API_KEY` for production observability.

## MVP Boundaries

This repo intentionally does not use Expo, Supabase, RevenueCat, or S3. Voice UI is represented as a placeholder because voice is later scope in the product plan.
