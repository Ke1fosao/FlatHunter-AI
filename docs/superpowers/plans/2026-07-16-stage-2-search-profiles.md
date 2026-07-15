# Stage 2 Search Profiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add user-owned search profiles, onboarding, deterministic natural-language parsing, notification preferences, and a mobile Mini App creation wizard.

**Architecture:** A dedicated `searches` Django app owns profile criteria, important places, and notification rules. DRF exposes scoped CRUD and parser endpoints. aiogram FSM provides short onboarding, while the Mini App handles advanced configuration.

**Tech Stack:** Django 6, Django REST Framework, aiogram 3, Next.js 16, React 19, TypeScript 6.

## Global Constraints

- Every search profile is scoped to the authenticated user.
- Missing natural-language criteria are reported, never invented.
- No external AI provider is required for the fallback parser.
- Telegram bot onboarding always provides cancel, back, and advanced-settings routes.
- Notification rules are stored now but delivered in Stage 10.

---

### Task 1: Search domain
- [x] Add `SearchProfile`, `ImportantPlace`, and `NotificationPreference`.
- [x] Add constraints, indexes, migration, and admin registration.

### Task 2: REST API
- [x] Add paginated user-scoped CRUD.
- [x] Add activate and pause actions.
- [x] Add nested important-place and notification preference writes.

### Task 3: Natural-language parser
- [x] Extract city, rooms, price, pets, floor, building, and commission criteria.
- [x] Return per-field confidence and missing required fields.

### Task 4: Telegram onboarding
- [x] Add FSM steps for city, budget, rooms, confirmation, back, cancel, and advanced settings.
- [x] Persist a profile for authenticated Telegram users.

### Task 5: Mini App wizard
- [x] Add step-based and natural-language modes.
- [x] Add responsive bottom sheet, confirmation, notification defaults, and API submission.

### Task 6: Verification
- [x] Add parser, ownership, creation, and price validation tests.
- [ ] Run CI lint, type checking, migrations, tests, audits, and Docker builds.
