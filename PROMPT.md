You are Codex. Build the ForgeMind app from start to finish.

Read these files first and treat them as the source of truth:
- AGENTS.md
- AGENTS_PLAN.md
- AGENTS_RULES.md
- DESIGN.md
- CODEX_PLAN.md

Do not ask me to repeat requirements already written in those files.

Confirmed stack:
- Mobile: React Native CLI + TypeScript
- Backend: FastAPI + Python
- Database: PostgreSQL + pgvector
- AI: OpenAI API
- Embeddings: OpenAI embeddings
- Memory search: pgvector
- Re-ranking: custom backend ranking formula
- Auth: Google Auth + Apple Auth + backend-issued JWT
- Payments: Apple StoreKit + Google Play Billing
- Admin: Next.js + TypeScript
- Observability: Prometheus + Grafana
- Error tracking: Sentry
- Analytics: PostHog

Do not use:
- Expo
- Supabase
- RevenueCat
- S3 for MVP

Work autonomously until the MVP is complete.

Process:
1. Inspect the repository.
2. Read all project docs.
3. Create or update the monorepo structure.
4. Implement backend, mobile app, admin dashboard, database schema, prompts, tests, and setup files.
5. Run formatting, linting, type checks, migrations, and tests.
6. Fix all errors you can fix.
7. Do not stop after planning.
8. Do not stop after scaffolding.
9. Do not stop after partial implementation.
10. Continue until the project is runnable end-to-end.

Required deliverables:
- mobile/ React Native CLI app
- backend/ FastAPI app
- admin/ Next.js dashboard
- PostgreSQL + pgvector migrations
- Docker Compose for Postgres, Prometheus, and Grafana
- auth flow with Google/Apple token verification stubs where credentials are required
- chat API
- memory extraction
- memory retrieval
- embedding generation
- memory re-ranking
- guidance rules CRUD
- safety classification
- subscription validation stubs for Apple/Google
- prompt templates
- observability metrics
- README.md
- .env.example files
- tests for memory ranking, guidance retrieval, and safety classification

Implementation rules:
- Prefer working code over placeholders.
- Use TODO comments only for external credentials, app-store setup, or platform secrets.
- Do not hardcode secrets.
- Add clear error handling.
- Keep code modular.
- Follow the product tone and safety rules in AGENTS_RULES.md.
- Crisis safety must override normal chat.
- The AI must never claim to be a licensed therapist.
- Use top 20 vector candidates, filter them, re-rank them, then inject only top 3–5 memories into prompts.
- Add setup instructions so a developer can run the project locally.

Completion criteria:
The task is not complete until:
- backend starts locally
- database migrations exist
- mobile app scaffold builds
- admin dashboard starts
- tests pass or failures are clearly explained
- README explains how to run everything
- remaining TODOs are listed clearly

Begin now. Do not stop until the MVP implementation is complete.
