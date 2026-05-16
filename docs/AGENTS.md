# AGENTS.md

# ForgeMind

ForgeMind is an AI-powered emotional support and mental fitness platform for men under pressure.

The system is designed to help users:
- reduce overwhelm
- think clearly
- regulate emotions
- reflect safely
- process relationship stress
- improve emotional resilience

ForgeMind is NOT:
- a licensed therapist
- emergency mental-health care
- a medical diagnosis system

---

# AI Persona

Primary conversational identity:
- Forge

Forge is:
- calm
- grounded
- direct
- practical
- emotionally intelligent
- emotionally safe
- masculine-neutral
- non-judgmental

Forge avoids:
- fake positivity
- manipulative engagement
- toxic masculinity
- fake human backstories
- pretending to be human
- pretending to be a therapist

Forge does NOT:
- invent fake life experiences
- claim to have relationships or trauma
- emotionally manipulate users

Conversation style:
- conversational
- low-pressure
- calm pacing
- one thoughtful question at a time
- practical before theoretical

---

# Emotional Support Domains

ForgeMind supports:
- burnout
- loneliness
- anxiety
- overthinking
- anger
- emotional overwhelm
- breakup recovery
- divorce
- dating stress
- fiance and engagement pressure
- wedding stress
- fatherhood pressure
- family conflict
- work stress
- confidence rebuilding
- sleep issues

---

# System Architecture

## Mobile
- React Native CLI
- TypeScript

## Backend
- FastAPI
- Python
- uv package manager

## Database
- PostgreSQL
- pgvector extension

## AI
- OpenAI API
- OpenAI embeddings

## Authentication
- Google Auth
- Apple Auth
- JWT sessions

## Payments
- Apple StoreKit
- Google Play Billing

## Observability
- Prometheus
- Grafana

## Monitoring
- Sentry
- PostHog

---

# AI Agents

## Conversation Agent
Handles:
- emotional conversations
- guidance injection
- memory usage
- reflective questioning

## Memory Agent
Handles:
- memory extraction
- memory updates
- memory ranking
- vector retrieval
- memory archiving

## Guidance Agent
Handles:
- CBT/DBT guidance retrieval
- emotional support rules
- topic-based guidance injection

## Safety Agent
Handles:
- crisis classification
- self-harm detection
- abuse risk
- unsafe response prevention

## Tone Evaluation Agent
Handles:
- response scoring
- tone quality
- emotional consistency
- anti-robotic validation

---

# Memory System

Memories store:
- recurring emotional patterns
- stress triggers
- relationship context
- goals
- preferences
- recurring themes

Memory stack:
- PostgreSQL
- pgvector
- OpenAI embeddings

Memory retrieval flow:
1. Create embedding
2. Search pgvector
3. Retrieve top 20 candidates
4. Filter inactive/unsafe memories
5. Re-rank candidates
6. Inject top 3–5 memories

Ranking formula:

final_score =
  similarity * 0.50 +
  importance * 0.25 +
  recency * 0.15 +
  active_status * 0.10

---

# Voice Architecture

MVP voice mode:
- Tap-to-Talk
- AAC .m4a uploads
- POST API requests

No realtime streaming in MVP.

Realtime voice later:
- WebSocket
- turn detection
- interruption support
- streaming audio

Audio format:
- AAC
- .m4a
- mono
- 16kHz or 24kHz

Do NOT convert to WAV unless:
- transcription fallback required
- unsupported format
- audio processing required

---

# Python Standards

Use:
- uv
- pyproject.toml
- uv.lock

Do NOT use:
- poetry
- pipenv
