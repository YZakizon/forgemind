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

MVP:
- Tap-to-Talk
- AAC .m4a uploads
- POST APIs

Do not implement realtime websocket voice yet.

Future:
- websocket streaming
- turn detection
- interruption support

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
