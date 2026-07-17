# Stage 9 Risk and Market Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an autonomous, deterministic Stage 9 analytics layer with versioned listing snapshots, real price history, cluster-deduplicated market statistics, explainable Risk Score, API endpoints, Mini App UI, demo scenarios, and safe integration with Stage 8 AI.

**Architecture:** Add a focused Django app `apps.analysis` with separate snapshot, comparable-selection, market-statistics, risk-scoring, orchestration, task, API, and persistence boundaries. The local deterministic provider is the default and only uses active listings from enabled approved sources; every result is versioned, idempotent, explainable, and safely nullable when data is insufficient. Frontend consumers receive compact summaries in listing payloads and detailed data from dedicated endpoints.

**Tech Stack:** Python 3.14, Django 6, Django REST Framework, PostgreSQL/PostGIS, Celery, Redis, Pydantic-compatible typed dataclasses, Next.js, React, TypeScript, Vitest, CSS.

## Global Constraints

- Stage 9 must work without paid APIs and without external scraping.
- Risk Score ranges from 0 to 100 and must never label a person or listing as fraudulent.
- Market statistics must expose sample size and confidence; insufficient data returns null statistics instead of invented precision.
- Comparable samples exclude the target listing and every listing in the same duplicate cluster.
- Only active listings from enabled sources with legal status `approved` or `approved_demo` are eligible.
- Snapshot and assessment writes must be idempotent and versioned.
- Stage 9 can be disabled without breaking feed, detail, map, duplicate, matching, or AI fallback flows.
- UI communicates risk with icon and text, not color alone, and preserves 44 px touch targets and mobile safe areas.
- Stage 8 may consume only persisted validated Stage 9 output and may not recompute Risk Score or market statistics.
- Full completion requires Ruff, mypy, migrations, pytest, pip-audit, ESLint, TypeScript, Vitest, production build, npm audit, both Docker builds, Gitleaks, and deployment verification.

---

### Task 1: Analysis app, models, migration, and admin

**Files:**
- Create: `backend/apps/analysis/__init__.py`
- Create: `backend/apps/analysis/apps.py`
- Create: `backend/apps/analysis/models.py`
- Create: `backend/apps/analysis/admin.py`
- Create: `backend/apps/analysis/migrations/0001_initial.py`
- Modify: `backend/config/settings.py`
- Test: `backend/tests/test_stage9_models.py`

**Interfaces:**
- Produces `ListingSnapshot`, `ListingPriceHistory`, `ListingMarketAssessment`, and `ListingRiskAssessment`.
- All assessment models expose `latest_for_listing(listing_id)` through normal ordered querysets rather than hidden global state.

- [ ] Write tests that assert model constraints, ordering, score bounds, unique `(listing, content_hash)`, unique `(listing, snapshot)` price events, and JSON defaults.
- [ ] Run `pytest tests/test_stage9_models.py -q`; expect failures because `apps.analysis` does not exist.
- [ ] Implement the models with UUID primary keys, indexed timestamps, explicit status/level choices, algorithm versions, input hashes, JSON evidence, and check constraints.
- [ ] Add `apps.analysis` to `INSTALLED_APPS`, create the migration, and register read-only useful admin list displays.
- [ ] Run model tests, `python manage.py makemigrations --check --dry-run`, Ruff, and mypy; expect all pass.
- [ ] Commit `feat: add Stage 9 analysis models`.

### Task 2: Canonical snapshots and real price history

**Files:**
- Create: `backend/apps/analysis/snapshots.py`
- Create: `backend/apps/analysis/services.py`
- Modify: `backend/apps/listings/services.py`
- Test: `backend/tests/test_stage9_snapshots.py`

**Interfaces:**
- Produces `canonical_snapshot_payload(listing: Listing) -> dict[str, Any]`.
- Produces `capture_listing_snapshot(listing: Listing, *, captured_at: datetime | None = None) -> SnapshotCaptureResult`.
- `SnapshotCaptureResult` contains `snapshot`, `created`, and optional `price_event`.

- [ ] Write failing tests for allowlisted canonical payload, stable SHA-256 hash, duplicate capture idempotency, baseline capture without fake price event, real increase/decrease events, and unchanged ingestion behavior.
- [ ] Run the focused tests and verify red state.
- [ ] Implement canonical payload normalization, hash generation, transactional `get_or_create`, previous-snapshot comparison, Decimal-safe percentage change, and one price event per snapshot.
- [ ] Hook capture after normalized listing persistence through `transaction.on_commit`; do not create snapshots in the unchanged ingestion path.
- [ ] Run snapshot tests plus existing ingestion and duplicate tests.
- [ ] Commit `feat: capture listing snapshots and price history`.

### Task 3: Cluster-aware comparable selection and market statistics

**Files:**
- Create: `backend/apps/analysis/contracts.py`
- Create: `backend/apps/analysis/comparables.py`
- Create: `backend/apps/analysis/market.py`
- Create: `backend/apps/analysis/providers.py`
- Modify: `backend/config/settings.py`
- Test: `backend/tests/test_stage9_market.py`

**Interfaces:**
- Produces `ComparableListing`, `ComparableSet`, and `MarketAssessmentResult` immutable dataclasses.
- Produces `select_local_comparables(listing: Listing) -> ComparableSet`.
- Produces `calculate_market_assessment(listing: Listing, comparables: ComparableSet) -> MarketAssessmentResult`.
- Produces `get_market_provider() -> MarketAnalysisProvider` with `LocalDeterministicMarketProvider` default.

- [ ] Write failing tests that exclude target/same-cluster/inactive/unapproved/stale rows and verify bounded cascade stages.
- [ ] Write failing tests for median, inclusive Q1/Q3, price-per-square-meter, IQR outlier reporting, deviation, deterministic ordering, confidence, and insufficient data.
- [ ] Implement settings for provider, enable flag, min/max sample, freshness, radius, area tolerance, and TTL.
- [ ] Implement bounded database candidate selection with one representative per cluster and stable tie ordering.
- [ ] Implement Decimal-safe robust statistics and confidence scoring from sample size, geography, freshness, area completeness, dispersion, and location accuracy.
- [ ] Run focused tests, query-count assertions, Ruff, and mypy.
- [ ] Commit `feat: add deterministic market analysis`.

### Task 4: Explainable deterministic Risk Score

**Files:**
- Create: `backend/apps/analysis/risk.py`
- Modify: `backend/apps/analysis/contracts.py`
- Test: `backend/tests/test_stage9_risk.py`

**Interfaces:**
- Produces `RiskSignal` and `RiskAssessmentResult` immutable dataclasses.
- Produces `calculate_risk_assessment(listing: Listing, market: ListingMarketAssessment | None) -> RiskAssessmentResult`.

- [ ] Write failing boundary tests for below-market price, price volatility, repost metadata, trusted image reuse across cities, duplicate hard conflicts, city-description mismatch, short/template text, prepayment language, unsafe external links, missing required fields, commission inconsistency, coordinate/address mismatch, and cluster source conflicts.
- [ ] Verify every positive score contribution carries stable `code`, positive `weight`, severity, evidence, label, and recommendation.
- [ ] Implement deterministic signal functions with fixed ordering, score cap 100, protective signals, neutral wording, and `insufficient_data` independent of numeric zero.
- [ ] Add invariant tests forbidding words that categorically accuse an author of fraud.
- [ ] Run focused tests and existing duplicate/AI tests.
- [ ] Commit `feat: add explainable Risk Score`.

### Task 5: Assessment orchestration, persistence, and background wrappers

**Files:**
- Modify: `backend/apps/analysis/services.py`
- Create: `backend/apps/analysis/tasks.py`
- Create: `backend/apps/analysis/management/commands/backfill_listing_snapshots.py`
- Create: `backend/apps/analysis/management/commands/refresh_listing_analyses.py`
- Test: `backend/tests/test_stage9_services.py`

**Interfaces:**
- Produces `refresh_listing_market_assessment(listing_id: UUID, *, force: bool = False) -> ListingMarketAssessment`.
- Produces `refresh_listing_risk_assessment(listing_id: UUID, *, force: bool = False) -> ListingRiskAssessment`.
- Produces `refresh_listing_analysis(listing_id: UUID, *, force: bool = False) -> AnalysisRefreshResult`.
- Celery tasks are thin wrappers that accept serialized UUID strings and optional correlation IDs.

- [ ] Write failing tests for input-hash idempotency, TTL reuse, stale replacement, failed/disabled provider status, market-before-risk ordering, safe failure persistence, and bounded command batches.
- [ ] Implement transactional persistence and deterministic input hashes tied to listing snapshot, comparable IDs, algorithm versions, and relevant settings.
- [ ] Add Celery retry/backoff/time limits and queue routing without making correctness depend on Celery Beat.
- [ ] Implement baseline backfill and bounded refresh commands with dry-run support and stable summaries.
- [ ] Run service tests, migration checks, and Celery task import tests.
- [ ] Commit `feat: orchestrate Stage 9 assessments`.

### Task 6: Authenticated API and compact listing summary

**Files:**
- Create: `backend/apps/analysis/serializers.py`
- Create: `backend/apps/analysis/views.py`
- Create: `backend/apps/analysis/urls.py`
- Modify: `backend/config/urls.py`
- Modify: `backend/apps/listings/serializers.py`
- Test: `backend/tests/test_stage9_api.py`

**Interfaces:**
- Adds `GET /api/v1/listings/{id}/price-history/`.
- Adds `GET /api/v1/listings/{id}/market-analysis/`.
- Adds `GET /api/v1/listings/{id}/risk-analysis/`.
- Adds `POST /api/v1/listings/{id}/analysis/refresh/`.
- Adds compact `analysis_summary` to `ListingSerializer` with nullable market/risk/price-change data.

- [ ] Write failing tests for anonymous rejection, approved-active listing filtering, missing listing 404, ready/insufficient/stale/failed serialization, refresh throttling, idempotency key reuse, and no frontend-controlled provider/weights.
- [ ] Implement serializers with stable schemas and no raw internal errors/evidence secrets.
- [ ] Implement object-safe views using the same approved listing queryset as Stage 8.
- [ ] Implement refresh response as current `200` or accepted `202`, and add DRF throttle scope/config.
- [ ] Add compact summary with query-efficient prefetch/subquery behavior and null-safe defaults.
- [ ] Run API tests, OpenAPI generation, query-count tests, Ruff, and mypy.
- [ ] Commit `feat: expose Stage 9 analysis API`.

### Task 7: Deterministic demo scenarios and Stage 8 context

**Files:**
- Modify: `backend/apps/listings/demo_source.py`
- Modify: `backend/apps/ai_analysis/services.py`
- Modify: `backend/apps/ai_analysis/rules.py`
- Test: `backend/tests/test_stage9_demo.py`
- Test: `backend/tests/test_stage9_ai_context.py`

**Interfaces:**
- Demo source emits deterministic revision/risk metadata without real people, contacts, or copyrighted images.
- `listing_context()` includes validated compact market/risk data only when persisted and usable.

- [ ] Write failing tests for deterministic price drops/increases, below-market listing, prepayment phrase, short description, cross-city trusted demo image hash, inconsistent cluster, and low-risk control.
- [ ] Extend demo data while preserving the same default seed and idempotent imports.
- [ ] Add a documented command path to import a second deterministic revision for price history demonstrations.
- [ ] Add Stage 8 context tests proving AI consumes persisted values, returns unknown for insufficient data, and never recalculates scores.
- [ ] Run demo, duplicate, market, risk, and AI test groups.
- [ ] Commit `feat: add Stage 9 demo scenarios and AI context`.

### Task 8: Mini App analytics UI

**Files:**
- Modify: `miniapp/src/lib/api.ts`
- Create: `miniapp/src/components/listing-analysis-panel.tsx`
- Create: `miniapp/src/components/listing-analysis-panel.test.tsx`
- Modify: `miniapp/src/components/cluster-browser.tsx`
- Modify: `miniapp/src/components/listing-feed.tsx`
- Modify: `miniapp/src/components/ai-assistant-workspace.tsx`
- Modify: `miniapp/src/app/globals.css`

**Interfaces:**
- Produces typed `AnalysisSummary`, `PriceHistoryResponse`, `MarketAnalysisResponse`, and `RiskAnalysisResponse` API contracts.
- Produces `<ListingAnalysisPanel listingId summary />` with loading, ready, insufficient, stale, failed, and retry states.

- [ ] Write failing component tests for price-change badge, market confidence gating, risk icon/text, disclaimer, chart text alternative, empty/stale/error states, refresh, and mobile-safe rendering.
- [ ] Implement typed API fetchers and runtime normalization for nullable backend data.
- [ ] Build an accessible SVG price-history chart with a screen-reader table/list alternative and no dependency addition.
- [ ] Integrate compact chips into feed/cluster cards and full panel into listing detail/AI comparison context.
- [ ] Add responsive CSS with 44 px controls, safe-area spacing, no horizontal overflow, and non-color-only statuses.
- [ ] Run Vitest, ESLint, TypeScript, production build, and npm audit.
- [ ] Commit `feat: add Stage 9 analytics UI`.

### Task 9: Documentation, rollout, and complete verification

**Files:**
- Create: `docs/stage-9-risk-market-analysis.md`
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/api.md`
- Modify: `.env.example`

**Interfaces:**
- Documents exact commands, settings, API examples, status semantics, safety wording, rollout, rollback, and known limits.

- [ ] Update docs with migration, baseline backfill, first analysis build, second demo revision, read-only rollout, auto-refresh enablement, and rollback switches.
- [ ] Verify no placeholder, contradictory setting, undocumented endpoint, or unbounded command remains.
- [ ] Run the complete standard backend/frontend/container/secret CI workflow.
- [ ] Inspect failing logs directly and fix root causes; do not weaken checks.
- [ ] Review the complete diff for temporary workflows, generated artifacts, secrets, unrelated refactors, unsafe wording, and accidental API changes.
- [ ] Merge only after every required job is green and verify the deployment status.
- [ ] Commit `docs: complete Stage 9 documentation`.