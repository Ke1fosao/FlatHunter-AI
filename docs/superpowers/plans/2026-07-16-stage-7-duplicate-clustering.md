# Stage 7 Duplicate Clustering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, explainable duplicate-detection and clustering system that presents one canonical apartment card with all source copies available inside it.

**Architecture:** A new `apps.duplicates` Django app owns fingerprints, candidate scoring, cluster construction, manual decisions, cluster-level user state, API presentation helpers, commands, and Celery wrappers. Existing `Listing` rows remain immutable source-normalized records. Existing feeds, matches, detail, dashboard, and map endpoints become cluster-aware while preserving standalone-listing compatibility.

**Tech Stack:** Python 3.13, Django 6, DRF, GeoDjango/PostGIS, Celery, PostgreSQL, Next.js, TypeScript, React, Vitest, standard-library `difflib`, SHA-256, 64-bit SimHash/Hamming distance.

## Global Constraints

- Preserve every original `Listing`; deduplication groups records and never deletes source data.
- Default UX is option A: one primary card/marker per apartment cluster with a source-count badge and a complete source list in detail view.
- Do not use an LLM for duplicate decisions.
- Do not perform unrestricted all-pairs comparisons.
- Remote image fetching is disabled by default and never occurs in normal API reads.
- Auto-merge threshold is configurable and defaults to `92`; review threshold defaults to `78`.
- A manual block/split decision is authoritative until explicitly restored.
- Existing listing API fields and listing-level endpoints remain backward compatible.
- CI remains read-only and must pass Ruff format/check, mypy, migrations, migration drift, pytest, pip-audit, ESLint, TypeScript, frontend tests/build, npm audit, both Docker builds, and Gitleaks.

---

### Task 1: Duplicate domain models and migration

**Files:**
- Create: `backend/apps/duplicates/__init__.py`
- Create: `backend/apps/duplicates/apps.py`
- Create: `backend/apps/duplicates/models.py`
- Create: `backend/apps/duplicates/admin.py`
- Create: `backend/apps/duplicates/migrations/__init__.py`
- Create: `backend/apps/duplicates/migrations/0001_initial.py`
- Modify: `backend/config/settings.py`
- Test: `backend/tests/test_stage7_duplicates.py`

**Interfaces:**
- Produces `ListingFingerprint`, `DuplicateCandidate`, `ListingCluster`, `ListingClusterMember`, `DuplicateDecision`, and `UserClusterState`.
- `ListingClusterMember.listing` is globally unique; a listing can belong to at most one active stored cluster.
- Candidate pair order is canonicalized by service code and protected by a `(left_listing, right_listing)` unique constraint.

- [ ] Write model tests for uniqueness, one primary per cluster, candidate ordering service expectations, cluster-state uniqueness, and immutable decision history.
- [ ] Run `pytest tests/test_stage7_duplicates.py -q` and verify model-import failures.
- [ ] Implement the app, choices, indexes, constraints, model validation, admin registrations, and migration.
- [ ] Add `apps.duplicates` to `INSTALLED_APPS` and duplicate thresholds/settings.
- [ ] Run migration and model tests; run `python manage.py makemigrations --check --dry-run`.

### Task 2: Fingerprints, safe image metadata, and scoring engine

**Files:**
- Create: `backend/apps/duplicates/normalization.py`
- Create: `backend/apps/duplicates/fingerprints.py`
- Create: `backend/apps/duplicates/scoring.py`
- Test: `backend/tests/test_stage7_duplicates.py`

**Interfaces:**
- `normalize_text(value: str) -> str`
- `simhash64(value: str) -> int`
- `hamming_distance64(left: int, right: int) -> int`
- `build_listing_fingerprint(listing: Listing) -> ListingFingerprint`
- `evaluate_duplicate(left: Listing, right: Listing, left_fp: ListingFingerprint, right_fp: ListingFingerprint) -> DuplicateEvaluation`
- `DuplicateEvaluation` exposes all component scores, final score, hard conflicts, reasons, and policy decision.

- [ ] Add failing unit tests for Ukrainian-aware deterministic normalization, contact hashing, URL normalization, address/attribute keys, SimHash distance, exact and perceptual image metadata, missing-component weight renormalization, hard conflicts, exact merge rules, and threshold decisions.
- [ ] Run focused tests and verify failures.
- [ ] Implement normalization with NFKC, case folding, punctuation removal, abbreviation canonicalization, bounded contact extraction, SHA-256 contact hashing, stable URL canonicalization, address/attribute block keys, and 64-bit SimHash.
- [ ] Implement fingerprint upsert with staleness detection and bounded `last_error`; consume only trusted imported image hash metadata and deterministic demo metadata.
- [ ] Implement explainable weighted scoring with exact/address/geo/attributes/text/image/price components and renormalized weights.
- [ ] Run focused tests, Ruff, and mypy.

### Task 3: Candidate generation, clustering, manual decisions, and tasks

**Files:**
- Create: `backend/apps/duplicates/candidates.py`
- Create: `backend/apps/duplicates/clustering.py`
- Create: `backend/apps/duplicates/services.py`
- Create: `backend/apps/duplicates/tasks.py`
- Create: `backend/apps/duplicates/management/__init__.py`
- Create: `backend/apps/duplicates/management/commands/__init__.py`
- Create: `backend/apps/duplicates/management/commands/build_listing_fingerprints.py`
- Create: `backend/apps/duplicates/management/commands/detect_listing_duplicates.py`
- Create: `backend/apps/duplicates/management/commands/rebuild_listing_clusters.py`
- Create: `backend/apps/duplicates/management/commands/process_listing_image_hashes.py`
- Modify: `backend/apps/listings/services.py`
- Test: `backend/tests/test_stage7_duplicates.py`

**Interfaces:**
- `candidate_pairs_for_listing(listing, *, limit) -> list[tuple[Listing, Listing]]`
- `evaluate_listing_candidates(listing, *, dry_run=False) -> CandidateRunResult`
- `rebuild_clusters(*, city=None, dry_run=False) -> ClusterRunResult`
- `confirm_candidate(candidate, actor, note)`, `split_candidate(candidate, actor, note)`, `restore_candidate_auto(candidate, actor, note)`.
- `schedule_listing_duplicate_refresh(listing_id)` queues only when `DUPLICATE_AUTO_QUEUE_ENABLED=true`.

- [ ] Add failing service tests for bounded candidate blocks, canonical pair order, idempotent upsert, auto-merge/review/reject, manual confirm/split/block/restore, transitive-poisoning prevention, stable cluster identity, deterministic primary selection, and rollback on failure.
- [ ] Run focused tests and verify failures.
- [ ] Implement candidate blocking by canonical URL, contact hash, address key, geo grid + rooms, attribute key + price bucket, image hash, and text block.
- [ ] Implement candidate persistence and manual decision authority.
- [ ] Implement guarded connected-component clustering, transactional rebuild, stable cluster reuse, primary quality tuple, member confidence/reasons, and aggregate counts/ranges.
- [ ] Implement idempotent commands with `--listing-id`, `--city`, `--limit`, and `--dry-run` where meaningful; image command operates offline on trusted/demo metadata only.
- [ ] Add Celery wrappers and optional ingestion scheduling without blocking image processing.
- [ ] Run service tests, full backend tests, Ruff, and mypy.

### Task 4: Cluster-aware serializers, feeds, state, matches, dashboard, and map

**Files:**
- Create: `backend/apps/duplicates/presentation.py`
- Create: `backend/apps/duplicates/serializers.py`
- Create: `backend/apps/duplicates/views.py`
- Create: `backend/apps/duplicates/urls.py`
- Modify: `backend/apps/listings/serializers.py`
- Modify: `backend/apps/listings/views.py`
- Modify: `backend/apps/searches/views.py`
- Modify: `backend/apps/geodata/views.py`
- Modify: `backend/apps/geodata/spatial.py`
- Modify: `backend/config/urls.py`
- Test: `backend/tests/test_stage7_duplicates.py`

**Interfaces:**
- Listing payload adds `cluster_id`, `source_count`, `member_count`, `is_cluster_primary`, `price_min_uah`, and `price_max_uah`.
- Default listing/match/map queries return standalone listings and active cluster primaries only.
- `GET /api/v1/listing-clusters/{id}/` returns primary, ordered members, reasons, confidence, user state, and optional profile match.
- `PATCH /api/v1/listing-clusters/{id}/state/` mutates favorite/hidden/compared/note transactionally.
- Staff endpoints confirm/split/restore candidates.

- [ ] Add failing API tests for collapsed feeds, cluster detail ordering, standalone compatibility, hidden/favorite/compare semantics, one comparison slot per cluster, comparison limit, dashboard counts, match primary-only behavior, map one-marker behavior, profile ownership, and staff-only decisions.
- [ ] Run focused API tests and verify failures.
- [ ] Implement presentation query helpers and serializer metadata without N+1 queries.
- [ ] Project cluster user state over listing-level endpoints; retain listing-level behavior for standalone records.
- [ ] Implement cluster detail/state and staff decision APIs.
- [ ] Update matches and map to evaluate/serialize primary listings while retaining cluster metadata.
- [ ] Run API tests and full backend suite.

### Task 5: Deterministic demo duplicates and operational documentation

**Files:**
- Modify: `backend/apps/listings/demo_source.py`
- Modify: `README.md`
- Modify: `.env.example`
- Modify: `docs/api.md`
- Modify: `docs/architecture.md`
- Modify: `docs/deployment.md`
- Create: `docs/stage-7-duplicate-clustering.md`
- Test: `backend/tests/test_stage7_duplicates.py`

**Interfaces:**
- Demo source emits deterministic duplicate groups with small price/text/source-copy variations and trusted synthetic image hashes.
- Repeated seed runs and duplicate commands produce identical clusters.

- [ ] Add a failing deterministic demo test that expects known three-member groups and stable primary selection.
- [ ] Implement synthetic duplicate groups without real addresses, contacts, or remote image downloads.
- [ ] Document commands, thresholds, security boundaries, rollout, monitoring metrics, and rollback procedure.
- [ ] Run seed/fingerprint/detection/rebuild twice and verify idempotent counts.

### Task 6: Mini App cluster UX

**Files:**
- Modify: `miniapp/src/lib/api.ts`
- Modify: `miniapp/src/lib/map-types.ts`
- Modify: `miniapp/src/components/listing-feed.tsx`
- Modify: `miniapp/src/components/map-workspace.tsx`
- Modify: `miniapp/src/components/leaflet-map.tsx`
- Modify: `miniapp/src/components/stage-six-shell.tsx`
- Create: `miniapp/src/components/cluster-sources.tsx`
- Create: `miniapp/src/components/cluster-sources.test.tsx`
- Create: `miniapp/src/lib/cluster-types.test.ts`
- Modify: `miniapp/src/app/stage-six.css`

**Interfaces:**
- `ListingFeedItem.cluster` metadata is stable for clustered and standalone listings.
- `fetchListingCluster(id, profileId?)` and `setClusterState(id, payload)` use cluster endpoints.
- Cards and map markers display `N джерела`; details show all source copies and a price range.

- [ ] Add failing type/contract/component tests for cluster metadata, source ordering, badge/pluralization, source links, price range, cluster state actions, and standalone rendering.
- [ ] Run Vitest and verify failures.
- [ ] Implement API types/functions and cluster-aware state routing.
- [ ] Implement source badge, price range, `Джерела` detail section, confidence wording, semantic links, loading/error states, and mobile-safe styling.
- [ ] Make map markers and selected-detail actions operate once per cluster.
- [ ] Run ESLint, TypeScript, Vitest, production build, and npm audit.

### Task 7: Full verification, PR, and merge

**Files:**
- Modify only files required by verified failures.

- [ ] Run backend formatter, Ruff, mypy, migrations, migration drift, full pytest, and pip-audit.
- [ ] Run frontend lint, typecheck, tests, build, and npm audit.
- [ ] Build backend and Mini App Docker images and run Gitleaks.
- [ ] Review branch diff for temporary workflows, diagnostic artifacts, secrets, placeholders, and accidental remote image fetching.
- [ ] Open one PR from `stage-7-duplicate-clustering` to `main`.
- [ ] Fix CI failures in consolidated commits; do not weaken quality gates.
- [ ] Confirm no unresolved review threads and merge with squash only after a fresh clean CI success.
