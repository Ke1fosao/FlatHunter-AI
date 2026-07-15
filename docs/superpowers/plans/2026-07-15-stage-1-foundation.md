# FlatHunter AI Stage 1 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a testable, secure monorepo foundation for the Django API, Telegram bot, Telegram Mini App, PostgreSQL/PostGIS, Redis, Celery, gateway, and health checks.

**Architecture:** Django owns identity, sessions, Telegram validation, bot webhook handling, and system health. Next.js provides a mobile-first Telegram-aware shell and authenticates by sending raw initData to Django. Docker Compose runs infrastructure and each process independently.

**Tech Stack:** Python 3.14, Django 6, Django REST Framework, PostgreSQL/PostGIS, Redis, Celery, aiogram, Next.js 16, React 19, TypeScript, Tailwind CSS, Docker Compose, Nginx, pytest, Ruff, mypy, Vitest, ESLint.

## Global Constraints

- No real source integration is enabled in Stage 1.
- Bot token and secrets never enter frontend code or repository history.
- Polling and webhook modes must not run simultaneously.
- Telegram initData must be validated server-side with freshness and replay protection.
- Health endpoints must distinguish liveness from readiness.
- Ukrainian is the primary UI language and Europe/Kyiv is the application timezone.

---

### Task 1: Repository and dependency foundation

**Files:** root configuration, `backend/pyproject.toml`, `miniapp/package.json`, lock files, Dockerfiles.

- [x] Create monorepo directories and environment template.
- [x] Pin direct dependency versions and generate lock files.
- [x] Add Docker Compose services and health checks.

### Task 2: Backend health and settings

**Files:** `backend/config/*`, `backend/apps/core/*`, backend tests.

- [x] Write failing health endpoint tests.
- [x] Implement environment-driven settings and structured logging.
- [x] Implement liveness/readiness endpoints and verify tests.

### Task 3: Telegram identity and session authentication

**Files:** `backend/apps/accounts/*`, migrations, tests.

- [x] Write failing tests for valid, tampered, stale, malformed, and replayed initData.
- [x] Implement HMAC validation and Telegram user parsing.
- [x] Implement session login, `/me/`, and logout endpoints.
- [x] Verify object creation, session state, and CSRF token response.

### Task 4: Telegram bot and webhook foundation

**Files:** `backend/apps/telegram_bot/*`, tests.

- [x] Implement `/start` with Mini App and demo actions.
- [x] Add polling management command guarded by `TELEGRAM_MODE`.
- [x] Add webhook secret validation and duplicate update protection.

### Task 5: Mini App shell

**Files:** `miniapp/src/*`, frontend tests.

- [x] Build Telegram-aware responsive shell and theme integration.
- [x] Add backend health and initData authentication client.
- [x] Add loading, browser-preview, authenticated, and error states.
- [x] Add bottom navigation placeholders for later stages.

### Task 6: Quality gates and documentation

**Files:** CI workflow, README, architecture and deployment docs.

- [x] Run backend lint, type checking, and tests.
- [x] Run frontend lint, type checking, tests, and production build.
- [x] Validate Compose configuration structurally when Docker is unavailable.
- [x] Document local setup, Telegram setup, security decisions, and next stage.
