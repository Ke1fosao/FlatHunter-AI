# FlatHunter AI Stage 1 Foundation Design

## Scope

Stage 1 creates the production-oriented platform foundation only: monorepo layout, containerized services, Django API, PostgreSQL/PostGIS, Redis, Celery wiring, Telegram bot shell, Telegram Mini App shell, secure Telegram initData session authentication, and health/readiness endpoints.

The following product domains are intentionally deferred to their dedicated stages: search profiles, listing ingestion, matching, maps, duplicates, AI analysis, notifications, shared search, billing, and the custom administration application.

## Architecture

The monorepo contains a Django backend and a Next.js Mini App. PostgreSQL is the source of truth, Redis provides cache/replay protection and future Celery transport, and a gateway routes browser traffic to the frontend and API. Telegram bot logic lives inside the backend codebase but runs as a separate process in polling mode locally or through a Django webhook endpoint in production. Polling and webhook modes are mutually exclusive by configuration.

## Authentication

The Mini App sends the raw `Telegram.WebApp.initData` string to `POST /api/v1/auth/telegram/`. The backend validates the HMAC signature, checks `auth_date`, rejects replayed payloads, upserts a Telegram profile, starts a Django session, and returns a CSRF token. The frontend never receives the bot token. Full initData and secrets are excluded from logs.

## Health Model

`/health/live/` proves the process is running. `/health/ready/` verifies database and cache access and returns HTTP 503 when dependencies are unavailable. `/api/v1/health/` exposes the same safe status for the Mini App. The Mini App has its own `/api/health` endpoint.

## Security Baseline

Secrets are environment-only. CORS is allowlisted, cookies are HttpOnly and secure outside debug mode, webhook requests require Telegram's secret header, replay keys are cached, and no real listing source is enabled. The stage establishes safe defaults without claiming production deployment is complete.

## Testing

Backend tests cover Telegram signature validation, stale data, tampering, replay protection, authentication, webhook secret checks, and health behavior. Frontend tests cover API URL normalization and Telegram shell helpers. CI runs lint, type checks, tests, builds, and Docker image builds.
