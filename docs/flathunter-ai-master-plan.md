# FlatHunter AI Master Plan

## Product Vision

FlatHunter AI is a production-oriented Telegram bot, Telegram Mini App, backend API, and data-processing system for long-term rental search in Ukraine.

Positioning:

- Product name: FlatHunter AI.
- Ukrainian interface name: FlatHunter AI - розумний пошук житла.
- Main slogan: Ми знаходимо хороші квартири раніше, ніж їх встигають орендувати інші.
- Secondary slogan: Один пошук замість десятків вкладок, сайтів і Telegram-каналів.

The product solves the problem of apartment seekers manually checking many sites and Telegram channels, comparing repeated listings, contacting owners, validating districts, and missing good options.

## Core System

FlatHunter AI must include:

- Telegram bot.
- Telegram Mini App.
- Backend API.
- Listing ingestion and normalization.
- Smart search profiles.
- AI-assisted evaluation.
- Map and geospatial filters.
- Instant notifications.
- Personal user cabinet.
- Admin panel.
- Analytics.
- Subscriptions.
- Shared apartment search.
- Duplicate detection.
- Risk detection for suspicious listings.

## Critical Source Rules

The system must not bypass third-party protections.

Forbidden:

- CAPTCHA bypass.
- Browser fingerprint spoofing.
- Unauthorized API usage.
- Stolen cookies or private APIs.
- Proxy-based blocking bypass.
- Ignoring robots.txt or rate limits.
- Hidden personal data collection.
- Unauthorized phone/contact extraction.
- Excessive load on third-party resources.

Supported source modes:

- Official API.
- Partner API.
- Official RSS/feed.
- Allowed HTML adapter.
- User-imported URL.
- Telegram-forwarded listing.
- Manual admin listing.
- JSON import.
- CSV import.
- Synthetic demo source.

Every source must expose legal, health, capability, and rate-limit metadata. If legal access is not confirmed, the source remains disabled and demo/manual adapters are used.

## Architecture Principles

Use a monorepo with separated backend, miniapp, infrastructure, and docs. Keep domain logic behind clear service and adapter boundaries.

Required principles:

- Separation of concerns.
- Dependency inversion.
- Typed interfaces.
- Domain services.
- Adapter pattern for sources, AI, geocoding, routing, and notifications.
- Idempotent background tasks.
- Centralized error handling.
- Structured logs and correlation IDs.

## Roles

Required roles:

- User.
- Premium user.
- Moderator.
- Administrator.
- Developer.

Each role must have clear permission boundaries, object-level authorization, and audit logging for sensitive actions.

## Implementation Stages

1. Foundation: monorepo, Docker, Django, PostgreSQL/PostGIS, Redis, Next.js, Telegram bot, Mini App, health checks.
2. Users and searches: onboarding, SearchProfile, filters, natural-language search input, notification preferences.
3. Demo data pipeline: demo source, raw listings, normalization, listings, seed data, feed.
4. Matching: deterministic Match Score, explanations, filtering, sorting.
5. Mini App UI: dashboard, listing feed, listing detail, filters, favorites, comparison.
6. Map: PostGIS, geocoding provider, map, markers, important places.
7. Duplicates: exact/fuzzy matching, image hashing hooks, ListingCluster.
8. AI: AIProvider abstraction, structured parser, summaries, comparison, owner questions, cost/error tracking, fallback.
9. Risk and market analysis: price statistics, Risk Score, price history, warning UI.
10. Notifications: Celery scheduling, Telegram notifications, quiet hours, duplicate protection.
11. Shared search: invitations, deep links, reactions, comments, consensus.
12. Admin panel: dashboard, users, sources, listings, jobs, AI center, logs.
13. Security and tests: permissions, SSRF protection, rate limiting, unit/integration/E2E tests.
14. Production: webhook, HTTPS, monitoring, backups, deployment documentation.

## Stage 8 Scope For Current Work

The next implementation slice starts Stage 8 safely without requiring a paid AI key.

Deliverables:

- `AIProvider` interface with structured completion contract.
- Local deterministic provider for demo and tests.
- Settings-driven provider selection.
- AI disabled/fallback path that keeps search usable.
- Structured natural-language search output with confidence.
- AI request audit model for prompt version, provider, latency, status, token/cost placeholders, and sanitized output.
- Tests for provider behavior, fallback, endpoint response, and audit logging.
- Environment documentation for future real provider keys.

Out of scope for this first Stage 8 slice:

- Real paid AI provider calls.
- Automatic messaging to landlords.
- Real source integrations without approved access.
- Full AI comparison UI.

## MVP Readiness Criteria

The MVP is not complete unless:

- The Telegram bot responds to `/start`.
- The Mini App authenticates through Telegram initData.
- Demo data is generated through a command.
- Search profiles persist.
- Filters change real backend results.
- Match Score is explainable.
- Listings support favorite, hide, compare, map, and detail flows.
- Demo duplicates are detected.
- Notifications are idempotent.
- Admin can inspect sources and jobs.
- Tests pass.
- No secrets are committed.
- README allows another developer to run the system.

## Security And Privacy Baseline

Required:

- Telegram initData validation.
- Telegram webhook secret validation.
- CORS allowlist.
- CSRF where applicable.
- Secure, HttpOnly cookies.
- Rate limiting.
- Object-level permissions.
- Audit log.
- Input validation.
- URL importer SSRF protection.
- Secret-free logs.
- No full bot tokens, cookies, initData, phone numbers, or payment data in logs.

## AI Rules

AI may assist with:

- Natural-language profile parsing.
- Listing description normalization.
- Feature extraction.
- Match/Risk explanations.
- Apartment comparison.
- Owner question generation.
- Daily reports.
- Contradiction detection.

AI must not:

- Invent exact addresses or amenities.
- Call someone a fraudster.
- Invent contacts.
- Hide uncertainty.
- Make legal decisions.
- Send messages to landlords without explicit user action.

All business-impacting AI output must be structured, validated, logged safely, and have deterministic fallback.
