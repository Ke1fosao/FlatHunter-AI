# FlatHunter AI — Stage 7 Duplicate Clustering Design

Date: 2026-07-16
Status: approved architecture, pending implementation plan
Branch: `stage-7-duplicate-clustering`

## 1. Goal

Stage 7 prevents the same apartment from appearing as several independent cards when it is published by multiple sources or reposted with small textual, price, image, or metadata changes.

The user-facing model is **one canonical card per apartment cluster** with a badge such as `3 джерела`. Opening the card exposes every source copy with its price, publication time, source, confidence, and direct source link.

The system must preserve all original `Listing` records. Deduplication groups records; it does not delete or rewrite source data.

## 2. Success criteria

Stage 7 is complete when:

- exact duplicates are grouped deterministically;
- fuzzy duplicates are evaluated with explainable component scores;
- image hashes can strengthen or weaken duplicate confidence;
- high-confidence candidates are auto-merged safely;
- medium-confidence candidates remain reviewable and do not disappear automatically;
- explicit manual split decisions prevent future automatic re-merging;
- one stable primary listing is chosen per cluster;
- feed, detail, favorites, hidden state, comparison, and map APIs expose cluster-aware behavior;
- the Mini App shows one card per cluster and all source alternatives inside the card;
- migrations, commands, tests, docs, audits, builds, and secret scanning pass in CI.

## 3. Non-goals

Stage 7 does not:

- scrape new production sources;
- use an LLM to decide whether two listings are duplicates;
- download arbitrary remote images during normal API requests;
- remove original listing records;
- merge listings across different deal types, property types, cities, or clearly incompatible room counts;
- introduce a full administrator dashboard for manual review beyond Django Admin and protected API primitives.

A richer moderation workspace can be added in Stage 12.

## 4. Architecture

A new Django app, `apps.duplicates`, owns duplicate detection and clustering. Existing `Listing` remains the source-normalized entity.

```text
Listing ingestion / update
        ↓
Fingerprint generation
        ↓
Cheap blocking keys
        ↓
Candidate pair generation
        ↓
Explainable weighted scoring
        ↓
Policy decision
  ├─ auto-merge
  ├─ needs-review
  └─ reject
        ↓
Cluster rebuild / primary selection
        ↓
Cluster-aware API and Mini App
```

The pipeline is deterministic and idempotent. Running it repeatedly on unchanged listings produces the same fingerprints, candidate scores, memberships, and primary selection.

## 5. Data model

### 5.1 `ListingFingerprint`

One-to-one with `Listing`.

Fields:

- `listing`;
- `version`;
- `normalized_city`;
- `normalized_district`;
- `normalized_street`;
- `normalized_title`;
- `normalized_description`;
- `address_key`;
- `attribute_key`;
- `text_simhash`;
- `contact_hashes` as JSON;
- `image_hashes` as JSON;
- `image_hash_version`;
- `generated_at`;
- `source_updated_at` copied from `Listing.last_seen_at` for staleness checks.

Indexes cover city, address key, attribute key, and text simhash prefix/block key.

### 5.2 `DuplicateCandidate`

Stores one canonical ordered listing pair. Pair order is always the lexicographically smaller UUID first, enforced by service logic and a unique constraint.

Fields:

- `left_listing`;
- `right_listing`;
- `exact_score`;
- `address_score`;
- `geo_score`;
- `attributes_score`;
- `text_score`;
- `image_score`;
- `price_score`;
- `final_score`;
- `decision`: `auto_merge`, `needs_review`, `rejected`, `confirmed`, `split`;
- `reasons` as structured JSON;
- `algorithm_version`;
- `evaluated_at`;
- `reviewed_at`;
- `reviewed_by` nullable;
- `review_note`.

### 5.3 `ListingCluster`

Fields:

- `id`;
- `status`: `active`, `split`, `archived`;
- `primary_listing`;
- `member_count`;
- `source_count`;
- `confidence_min`;
- `confidence_max`;
- `algorithm_version`;
- `created_at`;
- `updated_at`.

### 5.4 `ListingClusterMember`

Fields:

- `cluster`;
- `listing` with global uniqueness so one listing belongs to at most one active cluster;
- `role`: `primary` or `duplicate`;
- `confidence`;
- `joined_by`: `auto`, `manual`, `exact`;
- `reasons`;
- `joined_at`.

A partial unique constraint ensures one primary member per active cluster where supported; service-level transactional validation remains authoritative.

### 5.5 `DuplicateDecision`

Immutable audit history for manual actions.

Fields:

- `candidate` nullable;
- `left_listing`;
- `right_listing`;
- `action`: `confirm`, `split`, `block_pair`, `restore_auto`;
- `actor` nullable for system decisions;
- `note`;
- `created_at`.

A `block_pair` decision is authoritative and prevents future auto-merge until explicitly restored.

## 6. Fingerprint generation

### 6.1 Text normalization

Normalization is Ukrainian-aware but library-light:

- Unicode NFKC;
- case folding;
- replacement of punctuation with spaces;
- whitespace collapse;
- canonical apartment terms and common abbreviations;
- removal of source-specific boilerplate and tracking fragments;
- stable token sorting only for unordered fingerprint subsets, never for the displayed text.

The implementation must not claim linguistic equivalence beyond deterministic normalization.

### 6.2 Address fingerprint

Address identity combines:

- normalized city;
- normalized district;
- normalized street;
- building number from attributes or text when available;
- coordinate geohash/grid bucket when exact building data is unavailable.

Missing street or building number reduces confidence but does not automatically reject a pair.

### 6.3 Attribute fingerprint

Includes stable normalized values:

- deal type;
- property type;
- rooms;
- total area bucket;
- floor and total floors;
- building type;
- renovation level;
- heating type.

### 6.4 Contact fingerprints

Contacts are hashed before persistence. Raw phone numbers, email addresses, or messenger handles are not copied into duplicate tables.

### 6.5 Image hashes

Image identity uses two layers:

1. exact SHA-256 for already available image bytes or trusted imported image metadata;
2. perceptual dHash or pHash for decoded image bytes processed by an explicit background command/task.

Normal read requests never fetch remote images. Remote image processing is opt-in, allowlisted by source policy, size-limited, MIME-validated, timeout-limited, and protected against private-network addresses and redirects.

Demo listings receive deterministic synthetic image fingerprint metadata so image matching is testable without network access.

## 7. Candidate generation

The system never performs an unrestricted all-pairs comparison.

Candidate blocks are generated from one or more of:

- same canonical URL or normalized source URL;
- same contact hash;
- same city + address key;
- same city + coordinate grid + rooms;
- same city + attribute key + close price bucket;
- shared exact image hash;
- close text simhash within a constrained city/property block.

Hard incompatibility filters reject pairs before expensive scoring:

- different deal type;
- different property type;
- different city;
- room-count difference greater than one, unless one side is missing or explicitly studio-like;
- coordinate distance beyond a configured maximum when both locations are building-accurate;
- strongly incompatible total area.

## 8. Duplicate score

Each pair receives component scores from 0 to 100 and structured reasons.

Default weighted score:

- exact identifiers and contacts: 25%;
- address and geography: 25%;
- property attributes: 15%;
- text similarity: 15%;
- image similarity: 15%;
- price compatibility: 5%.

Weights are renormalized when a component is genuinely unavailable. Missing data is never treated as a positive match.

Policy thresholds:

- `>= 92`: auto-merge when no hard conflict or manual block exists;
- `78–91.99`: needs review, no automatic hiding/grouping unless already connected through another confirmed edge;
- `< 78`: rejected;
- exact canonical URL, exact source-independent contact plus compatible property data, or multiple exact image hashes may trigger an explainable exact merge rule.

Thresholds live in settings and are versioned in candidate records.

## 9. Cluster construction

Confirmed duplicate edges form connected components, but cluster formation is guarded against transitive poisoning.

Before adding a listing to a cluster, the service checks compatibility with the cluster primary and a minimum proportion of existing members. A-B and B-C similarity alone must not force A-C into one cluster when A and C conflict materially.

Cluster rebuilds run in a transaction and lock affected candidate/member rows.

When a manual split occurs:

- the target pair receives a blocking decision;
- the cluster is rebuilt from remaining confirmed edges;
- user-visible states are preserved and remapped deterministically.

## 10. Primary listing selection

Primary selection is deterministic. The ordered quality tuple is:

1. active status;
2. approved source and source health;
3. building-level location accuracy;
4. number of valid images;
5. completeness score;
6. owner listing preference;
7. lower commission;
8. newest publication time;
9. newest last-seen time;
10. stable UUID tie-breaker.

Changing the primary does not change cluster identity.

## 11. User state semantics

The Stage 7 API exposes cluster-aware state while retaining existing `UserListingState` records.

Rules:

- favorite: true when any active member is favorite; setting favorite applies to the current primary and clears redundant member flags transactionally;
- hidden: hiding a cluster hides all current members through a cluster-state projection; newly joined duplicates inherit the cluster-hidden state;
- compared: one cluster occupies one comparison slot, never one slot per source copy;
- note: cluster-level note takes precedence; existing primary-listing notes are migrated lazily when the user next updates the state.

A new `UserClusterState` model is preferred over overloading `UserListingState`.

## 12. API design

### 12.1 Cluster-aware feed

Existing listing and match endpoints remain backward compatible but add cluster metadata:

- `cluster_id`;
- `source_count`;
- `member_count`;
- `is_cluster_primary`;
- `price_min_uah`;
- `price_max_uah`.

By default, feeds return only standalone listings and active cluster primaries.

Optional `include_duplicates=true` exposes all members for diagnostics/admin use where authorized.

### 12.2 Cluster detail

`GET /api/v1/listing-clusters/{cluster_id}/`

Returns:

- canonical primary card;
- all active members;
- source name and source URL;
- current and historical price fields available in Stage 7;
- publication and last-seen timestamps;
- confidence and concise reasons;
- user cluster state;
- best available Match Score evaluated against the selected profile.

### 12.3 Cluster state

`PATCH /api/v1/listing-clusters/{cluster_id}/state/`

Supports favorite, hidden, compared, and note with the existing comparison limit enforced transactionally.

### 12.4 Review/admin primitives

Staff-only endpoints may confirm or split candidates. Django Admin provides candidate filters, component scores, reasons, cluster members, primary reassignment, and decision history.

## 13. Mini App UX

### 13.1 Feed and map

- one card and one marker per cluster;
- badge such as `3 джерела`;
- price range when source prices differ;
- source count never replaces the main Match Score;
- standalone listings remain visually unchanged except for a stable cluster metadata shape.

### 13.2 Detail panel

A `Джерела` section lists all copies, ordered by primary first and then source quality/freshness.

Each source row contains:

- source name;
- price;
- publication time;
- last-seen freshness;
- owner/commission indicators where available;
- duplicate confidence and short explanation;
- direct external link.

The UI clearly says that several advertisements likely describe the same apartment; it does not state certainty for review-level candidates.

### 13.3 State actions

Favorite, hide, compare, and note actions operate once per cluster. The UI must not create duplicate comparison entries.

### 13.4 States and accessibility

The interface includes loading, empty, partial-data, authentication, and API-error states. Source rows use semantic buttons/links, visible focus, keyboard access, and Telegram safe-area spacing.

## 14. Pipeline integration

After a successful normalized listing create/update, ingestion schedules fingerprint refresh and incremental candidate evaluation. The ingestion transaction does not wait for image processing.

Management commands:

- `build_listing_fingerprints`;
- `detect_listing_duplicates`;
- `rebuild_listing_clusters`;
- `process_listing_image_hashes` with safe demo/offline mode.

Commands support `--listing-id`, `--city`, `--limit`, `--dry-run`, and idempotent repeated execution where meaningful.

A Celery task layer wraps the same services without duplicating business logic.

## 15. Security and privacy

- no raw contact duplication in fingerprint tables;
- no arbitrary user-controlled image URLs fetched by backend workers;
- remote image fetching disabled by default;
- fixed source allowlist and DNS/IP validation before external fetches;
- maximum image byte size, dimensions, redirects, and timeout;
- MIME sniffing rather than trusting extension alone;
- staff-only manual decision endpoints;
- ownership checks for cluster state and profile-dependent Match Score;
- audit trail for every manual merge/split;
- source URLs are returned only from already normalized listings;
- no LLM or external AI provider is required.

## 16. Error handling

- fingerprint failure records a bounded error and leaves listing visible as standalone;
- image hashing failure does not block text/attribute duplicate detection;
- candidate scoring failures are isolated per pair;
- cluster rebuild failure rolls back atomically;
- stale fingerprints are regenerated before scoring;
- deleted/inactive source records remain in history but are excluded from active cluster presentation;
- conflicts caused by manual decisions are surfaced to staff rather than silently overridden.

## 17. Testing strategy

### Unit tests

- normalization and fingerprints;
- exact rules;
- text simhash distance;
- geographic and attribute compatibility;
- image hash distance;
- missing-component weight renormalization;
- deterministic primary selection;
- hard incompatibility filters.

### Service tests

- idempotent fingerprint generation;
- candidate pair canonical ordering;
- auto-merge, review, reject, confirm, split, and block behavior;
- transitive-poisoning prevention;
- cluster rebuild and primary replacement;
- concurrent comparison-limit updates;
- user-state migration/projection.

### API tests

- default feed collapses active clusters;
- cluster detail source ordering;
- ownership isolation;
- staff-only decision endpoints;
- hidden/favorite/compare cluster behavior;
- map emits one marker per cluster;
- backward-compatible standalone payloads.

### Frontend tests

- source-count badge;
- price range;
- source drawer/list;
- cluster-level state actions;
- no duplicate comparison slots;
- loading/empty/error states;
- source links and accessibility labels.

### CI

The final clean CI must run Ruff format/check, mypy, PostGIS migrations, migration drift check, pytest, pip-audit, ESLint, TypeScript, frontend tests/build, npm audit, both Docker builds, and Gitleaks.

## 18. Rollout and backward compatibility

1. Apply schema migrations.
2. Build fingerprints for existing listings.
3. Run duplicate detection in dry-run mode and inspect metrics.
4. Enable auto-merge only for the high-confidence threshold.
5. Rebuild clusters.
6. Deploy cluster-aware read APIs and Mini App.
7. Keep standalone fallback when cluster services fail or have not processed a listing yet.

Existing `Listing` identifiers and source URLs remain valid. Existing API consumers that ignore new cluster fields continue to work.

## 19. Observability

Structured metrics/logs include:

- fingerprints generated/failed/stale;
- candidate pairs generated/scored;
- auto-merge, review, reject counts;
- cluster count and average size;
- primary changes;
- manual split/block count;
- image fetch/hash failures;
- pipeline duration by city/source;
- percentage of feed cards collapsed by clustering.

No raw contacts or full listing descriptions are logged.

## 20. Acceptance checklist

- [ ] All original listings remain queryable internally.
- [ ] Default user feed shows one card per apartment cluster.
- [ ] Cluster card exposes all sources and direct links.
- [ ] Exact, fuzzy, geographic, attribute, price, and image signals are explainable.
- [ ] Auto-merge only occurs above the configured safe threshold.
- [ ] Medium-confidence pairs do not disappear automatically.
- [ ] Manual split blocks future automatic re-merge.
- [ ] Primary selection is deterministic.
- [ ] Favorite, hidden, compare, note, and map behavior are cluster-aware.
- [ ] Remote image processing is optional and hardened.
- [ ] Commands and tasks are idempotent.
- [ ] Backend, frontend, migration, security, audit, and Docker checks pass.
