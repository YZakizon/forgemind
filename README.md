# ForgeMind

ForgeMind is an AI-powered men's mental health mobile app focused on calm, private, practical support. The MVP uses React Native CLI, FastAPI, PostgreSQL with pgvector, OpenAI APIs, and a Next.js admin dashboard.

## Structure

- `backend/` FastAPI API, safety, guidance, memory ranking, auth/JWT contracts, subscription validation, prompts, tests, Alembic migrations
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
For a USB-connected Android demo, `make android-tunnel` forwards both Metro `8085` and backend `8005`, and `make android-install-usb` builds the mobile app against `http://127.0.0.1:8005`.
Set `API_BASE_URL` in `mobile/.env.local`, root `.env.local`, or the shell when the mobile app should call a different backend URL. Reinstall the Android app after changing it because the value is compiled into native build config.
The root `.env` is the highest-priority local development file. Service-local files such as `backend/.env.local`, `admin/.env.local`, and `mobile/.env.local` can exist, but duplicate keys in root `.env` win.

```bash
make backend BACKEND_BIND_HOST=0.0.0.0 BACKEND_HOST=192.168.0.106
make frontend ADMIN_HOST=192.168.0.106
make mobile
make android-install
```

Default app ports:

- Postgres host port: `5435`
- Backend: `8005`
- Admin: `3008`
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

The admin dashboard runs on `http://192.168.0.106:3008` when started through `make frontend`.

Run mobile:

```bash
cd mobile
npm install
npm run start -- --host 0.0.0.0 --port 8085
npm run android -- --port 8085
```

Metro runs on port `8085`. Use `make android-install` for LAN installs that keep working after unplugging USB. Use `make android-install-usb` only when you want the app to depend on Android USB reverse.
The mobile UI uses React Navigation bottom tabs and mock preview state for Home, Talk, Tap-to-Talk Voice, Reset, Progress, Profile, mode selection, and voice-state cards. For LAN testing, rebuild/reinstall the Android app after changing `API_BASE_URL`.

## AI Voice Providers

Chat and embeddings use OpenAI by default. STT uses OpenAI by default. TTS can use OpenAI or Deepgram:

```bash
TTS_PROVIDER=deepgram
DEEPGRAM_API_KEY=...
DEEPGRAM_TTS_MODEL=aura-2-thalia-en
DEEPGRAM_TTS_ENCODING=mp3
DEEPGRAM_TTS_SPEED=1.0
```

The mobile app still calls the backend `/speech` endpoint. The backend chooses the provider, so changing TTS provider or voice only requires a backend restart.

## API Highlights

- `GET /health`
- `POST /auth/login`
- `GET /auth/me`
- `POST /chat`
- `POST /voice-chat`
- `POST /voice-transcribe`
- `POST /speech`
- `POST /safety/classify`
- `GET/POST/PUT/DELETE /guidance/rules`
- `GET /memories`
- `POST /memories/archive`
- `GET /users/{user_id}/export`
- `DELETE /users/{user_id}/data`
- `POST /mood-checkins`
- `GET /progress/summary`
- `POST /reset-sessions`
- `POST /reset-sessions/{reset_id}/complete`
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

## Auth, Safety, and Guidance

`/auth/login` accepts Google or Apple provider tokens and issues ForgeMind JWT sessions. Development keeps a deterministic local verifier and the mobile demo token maps to the stable demo user. In production, demo tokens are rejected and provider config must be present; provider verification fails closed until real public-key validation is implemented. `/auth/me` verifies bearer tokens and returns the current user id.

The safety gate now stops normal coaching for crisis and high-risk safety messages before prompt generation. Guidance coverage includes burnout, anxiety, anger, breakup, divorce, dating, wedding or fiance stress, loneliness, fatherhood, family conflict, and sleep support.

## Progress and Reset Tracking

Home quick check-ins persist to `mood_checkins`, Reset tools create and complete `reset_sessions`, and Progress reads `/progress/summary` for weekly check-in counts, completed resets, and top emotional themes. If the backend is unavailable, the mobile app keeps the calm preview state and shows a compact sync message.

## Privacy Controls

Profile privacy rows call backend data controls. Memory controls archive active memories, export returns stored memories, check-ins, reset sessions, and recent chat messages, and delete removes user-owned chat, memory, safety, subscription, check-in, and reset records while keeping the user account shell.

## AI and Voice

`/chat` uses the OpenAI provider when `OPENAI_API_KEY` is set, with local fallback responses when it is not. `/voice/ws` accepts WebSocket `.m4a` voice segments, sends each segment to STT, stores timestamped transcript segments for the active voice session, merges and deduplicates overlapping text, then routes the final transcript through the same chat, safety, guidance, and memory flow. `/voice-chat` and `/voice-transcribe` remain available as POST fallbacks. `/speech` uses the configured backend TTS provider to synthesize Forge responses as audio. The Android app includes a native recorder module for `.m4a` voice capture and asks the backend for AI speech before falling back to device text-to-speech.

Voice segmentation targets:

- VAD silence threshold: 1.0 second
- Preferred segment length: 3-8 seconds
- Max segment length: 10-12 seconds
- Pre-roll target: 300-500 ms
- Post-roll target: 700-1200 ms
- Overlap target: 500-1000 ms
- Format: mono AAC `.m4a`

The current Android recorder can rotate valid `.m4a` chunks and send segment timestamps. True pre-roll and overlap require replacing `MediaRecorder` chunk rotation with an `AudioRecord` ring buffer and AAC/M4A segment encoder.

Default provider settings:

- `AI_PROVIDER=openai`
- `STT_PROVIDER=openai`
- `TTS_PROVIDER=openai`
- `OPENAI_STT_MODEL=whisper-1`
- `OPENAI_TTS_MODEL=gpt-4o-mini-tts`
- `OPENAI_TTS_VOICE=cedar`
- `OPENAI_TTS_RESPONSE_FORMAT=aac`

## Credential TODOs

- Set `GOOGLE_AUTH_AUDIENCE` for production Google identity-token verification.
- Set `APPLE_AUTH_AUDIENCE` and `APPLE_AUTH_ISSUER` for production Apple identity-token verification. `APPLE_AUTH_AUDIENCE` is also used as the StoreKit bundle id.
- Set `STOREKIT_ISSUER_ID`, `STOREKIT_KEY_ID`, `STOREKIT_PRIVATE_KEY`, and `STOREKIT_ROOT_CA_PEM` before enabling production StoreKit validation.
- Set `GOOGLE_PLAY_PACKAGE_NAME` and `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` before implementing production Play Billing validation.
- Add `OPENAI_API_KEY` for AI responses, embeddings, voice transcription, and backend text-to-speech.
- Add `SENTRY_DSN` and `POSTHOG_API_KEY` for production observability.

## MVP Boundaries

This repo intentionally does not use Expo, Supabase, RevenueCat, or S3.
