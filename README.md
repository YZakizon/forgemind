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

For LAN testing with a phone, use your machine's `192.168.0.106` address as the public backend/admin host.
The backend listener defaults to `0.0.0.0` so both LAN access and Android USB reverse can reach it.
For a USB-connected Android demo, `make android-tunnel` forwards both Metro `8085` and backend `8005`, and the mobile app calls `http://127.0.0.1:8005`.
Set `API_BASE_URL` in `mobile/.env.local`, root `.env.local`, or the shell when the mobile app should call a different backend URL. Reinstall the Android app after changing it because the value is compiled into native build config.
The root `.env` is the highest-priority local development file. Service-local files such as `backend/.env.local`, `admin/.env.local`, and `mobile/.env.local` can exist, but duplicate keys in root `.env` win.

```bash
make backend BACKEND_BIND_HOST=0.0.0.0 BACKEND_HOST=192.168.0.106
make frontend ADMIN_HOST=192.168.0.106
make mobile
make android-install API_BASE_URL=http://192.168.0.106:8005
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
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8005
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

The admin dashboard runs on `http://192.168.0.106:3005` when started through `make frontend`.

Run mobile:

```bash
cd mobile
npm install
npm run start -- --host 0.0.0.0 --port 8085
npm run android -- --port 8085
```

Metro runs on port `8085`. `make android-install` runs the USB tunnel before installing the app.
The mobile UI uses React Navigation bottom tabs and mock preview state for Home, Talk, Tap-to-Talk Voice, Reset, Progress, Profile, mode selection, and voice-state cards. For LAN testing, rebuild/reinstall the Android app after changing `API_BASE_URL`.

## API Highlights

- `GET /health`
- `POST /auth/login`
- `POST /chat`
- `POST /voice-chat`
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

The pure ranking/filtering code is implemented in `backend/app/services/memory.py`; `/chat` now creates embeddings, retrieves pgvector memory candidates, saves chat messages, and extracts durable memories when Postgres is available. If Postgres is unavailable, the demo falls back to in-memory guidance and template responses instead of failing.

## AI and Voice

`/chat` uses the OpenAI provider when `OPENAI_API_KEY` is set, with local fallback responses when it is not. `/voice-chat` accepts an uploaded audio file, transcribes it through the configured OpenAI transcription model, then routes the transcript through the same chat, safety, guidance, and memory flow. The Android app includes a native recorder module for `.m4a` voice capture.

## Credential TODOs

- Add real Google identity-token verification credentials.
- Add real Apple identity-token verification credentials.
- Add StoreKit server API credentials.
- Add Google Play Billing API credentials.
- Add `OPENAI_API_KEY` for AI responses, embeddings, and voice transcription.
- Add `SENTRY_DSN` and `POSTHOG_API_KEY` for production observability.

## MVP Boundaries

This repo intentionally does not use Expo, Supabase, RevenueCat, or S3.
