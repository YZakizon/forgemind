# CODEX_PLAN.md

# ForgeMind Codex Instructions

Codex must treat these files as the source of truth:
- AGENTS.md
- AGENTS_PLAN.md
- AGENTS_RULES.md
- DESIGN.md

Do not reinterpret requirements unless files conflict.

---

# Confirmed Stack

## Mobile
- React Native CLI
- TypeScript

## Backend
- FastAPI
- Python
- uv

## Database
- PostgreSQL
- pgvector

## AI
- OpenAI API
- OpenAI embeddings

## Auth
- Google Auth
- Apple Auth
- JWT

## Payments
- StoreKit
- Google Play Billing

## Observability
- Prometheus
- Grafana

## Monitoring
- Sentry
- PostHog

---

# Do NOT Use

- Expo
- Supabase
- RevenueCat
- S3 for MVP
- poetry
- pipenv

---

# Build Order

1. Inspect repository
2. Create monorepo structure
3. Build FastAPI backend
4. Add PostgreSQL + pgvector
5. Build React Native CLI app
6. Build Next.js admin dashboard
7. Implement auth
8. Implement AI chat
9. Implement memory extraction
10. Implement guidance retrieval
11. Implement safety classification
12. Add observability
13. Add tests
14. Add documentation

---

# Required Deliverables

- mobile app
- backend API
- admin dashboard
- Docker Compose
- migrations
- README
- .env.example
- tests
- prompt templates

---

# Memory Requirements

Use:
- OpenAI embeddings
- pgvector retrieval
- top 20 candidate retrieval
- filtering
- custom reranking
- inject top 3–5 memories

---

# Voice Requirements

Current direction:
- WebSocket voice transport.
- Mobile records continuous audio, runs VAD, and creates speech segments.
- VAD silence threshold: 1.0 second.
- Preferred segment length: 3-8 seconds.
- Max segment length: 10-12 seconds.
- Segment audio format: AAC `.m4a`.
- Add mobile audio pre-roll of 300-500 ms, post-roll of 700-1200 ms, and 500-1000 ms overlap.
- Backend sends each segment to STT.
- Backend stores transcript segments with timestamps for the active voice session.
- Backend merges and deduplicates overlapping transcript text before sending the final transcript to chat.
- Backend may clean punctuation after the full paragraph is merged.

Implementation note:
- The existing Android `MediaRecorder` chunk rotation can emit valid `.m4a` segments and timestamps, but true pre-roll and overlap require an `AudioRecord` ring buffer plus AAC/M4A encoding.

---

# Python Requirements

Use:
- uv
- pyproject.toml
- uv.lock

Commands:
- uv add
- uv sync
- uv run

---

# Completion Criteria

Task is not complete until:
- backend runs locally
- migrations work
- mobile app builds
- admin dashboard runs
- tests pass or failures explained
- README exists
- TODOs documented

---

# Mobile Test Plan

- Home quick check-in must never stay stuck on "Saving check-in..." when the backend is slow, unreachable, or returning `5xx`.
- Rapid repeated quick check-in taps must produce at most one in-flight request.
- After one successful quick check-in, tapping a different quick check-in should save without a false fallback timeout.
- Burned out quick check-in should either show success feedback and set Talk mode to Vent, or show a clear sync failure message within the backend fallback timeout.
- Production user-facing errors must hide technical/dev wording. For backend connection failures, use copy like "Forge is unable to connect. Please try again." instead of "Check the server and try again."
- Talk page chat messages should show a humanized date/time in the chat box.

---

# Codex Checkpoint

Saved: 2026-05-23 02:55:30 PDT

Branch: `plan-9-runtime-hardening`

Current validated work:
- Backend voice WebSocket keeps the session open after `done` and closes only when Talk is left/cleared or an error path closes it.
- Backend sends AI response text parts over `/voice/ws`, then sends `tts_audio` events with base64 audio for each body/question part.
- TTS provider can be OpenAI or Deepgram. Current local config uses `TTS_PROVIDER=deepgram` and `DEEPGRAM_TTS_ENCODING=mp3`; OpenAI TTS remains `aac`.
- Android mobile app can enqueue backend-pushed WebSocket audio via `ForgeMindTts.enqueueAudioBase64`.
- Android mobile app still uses `/speech` as fallback/replay/typed-chat TTS.
- Backend AI guardrails still run before TTS: input safety classification, crisis/high-risk bypass, generated response safety validation, then response split/TTS.
- Home quick check-in fallback/cache and async backend DB handler fixes are in this working tree.
- Long-pause/silent VAD chunks are cut on mobile and prompt-echo STT hallucinations are dropped on the backend.
- Voice WebSocket uses the active backend base URL selected by HTTP fallback when available.

Validation completed:
- `backend/.venv/bin/python -m pytest backend/tests` -> 61 passed
- `cd mobile && npm run typecheck` -> passed
- `cd mobile/android && GRADLE_USER_HOME=/tmp/forgemind-gradle ./gradlew assembleDebug` -> BUILD SUCCESSFUL

Restart/reinstall required:
- Restart backend after env or backend code changes.
- Rebuild/reinstall Android app because native `ForgeMindTtsModule.kt` changed.

Dirty tracked files:
- `.env.example`
- `AGENTS.md`
- `CODEX_PLAN.md`
- `README.md`
- `backend/.env.example`
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/prompts/conversation_agent.md`
- `backend/app/schemas.py`
- `backend/app/services/ai.py`
- `backend/app/services/openai_provider.py`
- `backend/tests/test_chat_orchestration.py`
- `backend/tests/test_data_controls.py`
- `backend/tests/test_progress.py`
- `mobile/android/app/src/main/java/com/forgemind/ForgeMindAudioModule.kt`
- `mobile/android/app/src/main/java/com/forgemind/ForgeMindTtsModule.kt`
- `mobile/src/api.ts`
- `mobile/src/components.tsx`
- `mobile/src/preferences.ts`
- `mobile/src/screens.tsx`

Untracked files:
- `backend/tests/test_speech.py`

Next recommended manual check:
- Restart backend and reinstall Android app, then verify Talk voice flow: record -> transcript appears -> Forge thinking -> body audio plays first -> follow-up audio plays second -> pressing hold-to-talk again stops current read-aloud immediately.
