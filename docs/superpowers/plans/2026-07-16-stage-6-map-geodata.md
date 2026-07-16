# Stage 6 Map and Geodata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add PostGIS-backed locations, safe geocoding, important places, spatial APIs, and an interactive apartment map to the FlatHunter AI Telegram Mini App.

**Architecture:** GeoDjango stores geography points in PostGIS while preserving decimal coordinates for compatibility. A provider abstraction supplies deterministic demo geocoding and an opt-in Nominatim integration. Authenticated GeoJSON endpoints feed a client-only Leaflet map integrated into the existing Stage 5 workspace.

**Tech Stack:** Django 6, GeoDjango, PostGIS 17, DRF, aiohttp, Redis cache, Next.js 16, React 19, TypeScript 6, Leaflet, React Leaflet, Vitest, pytest.

## Global Constraints

- External geocoding must be disabled by default.
- CI must not depend on internet geocoding or tile availability.
- No user-controlled provider URL or SSRF-capable fetch path.
- All profile and important-place data must be user-scoped.
- Tile attribution must always be visible.
- Geometry uses SRID 4326 and longitude/latitude order.
- Keep existing decimal latitude/longitude API fields during Stage 6.
- Stage 6 does not implement routing, isochrones, duplicates, AI, or risk analysis.

---

### Task 1: GeoDjango runtime and database configuration

**Files:**
- Modify: `backend/config/settings.py`
- Modify: `backend/Dockerfile`
- Modify: `backend/pyproject.toml`
- Modify: `backend/requirements.lock`
- Modify: `backend/requirements-dev.lock`
- Modify: `.env.example`
- Modify: `docker-compose.yml`
- Test: `backend/tests/test_geodata_settings.py`

**Interfaces:**
- Produces: PostGIS database backend for PostgreSQL URLs, `GEOCODING_PROVIDER`, `GEOCODING_API_KEY`, `GEOCODING_USER_AGENT`, `MAP_TILES_URL`, and `MAP_ATTRIBUTION` settings.

- [ ] Write a failing settings test asserting `django.contrib.gis` is installed and PostgreSQL uses `django.contrib.gis.db.backends.postgis`.
- [ ] Run `pytest tests/test_geodata_settings.py -q` and verify failure.
- [ ] Add GeoDjango app and PostGIS engine selection without breaking explicit non-PostgreSQL test configuration.
- [ ] Install `binutils`, `gdal-bin`, `libgeos-c1v5`, and `libproj-dev` in the backend image.
- [ ] Add geodata environment variables to settings, Compose, and `.env.example`.
- [ ] Run the targeted test and `python manage.py check`.
- [ ] Commit with `chore: enable GeoDjango and geodata settings`.

### Task 2: Geometry fields and migration

**Files:**
- Modify: `backend/apps/listings/models.py`
- Modify: `backend/apps/searches/models.py`
- Create: `backend/apps/listings/migrations/0003_listing_location.py`
- Create: `backend/apps/searches/migrations/0003_importantplace_location.py`
- Create: `backend/apps/geodata/geometry.py`
- Test: `backend/tests/test_geodata_models.py`

**Interfaces:**
- Produces: `point_from_coordinates(latitude, longitude) -> Point | None`, `coordinates_from_point(point) -> tuple[Decimal, Decimal] | None`, `Listing.location`, and `ImportantPlace.location`.

- [ ] Write failing tests for coordinate-to-point conversion, longitude/latitude order, null values, and model synchronization.
- [ ] Run targeted tests and confirm missing interfaces.
- [ ] Add `PointField(srid=4326, geography=True, null=True, blank=True)` to both models.
- [ ] Implement focused conversion helpers and model `save()` synchronization.
- [ ] Add data migrations that populate geometry from existing decimals.
- [ ] Run migrations, migration drift check, and targeted tests.
- [ ] Commit with `feat: add PostGIS geometry to listings and places`.

### Task 3: Geocoding provider contracts and deterministic demo provider

**Files:**
- Create: `backend/apps/geodata/__init__.py`
- Create: `backend/apps/geodata/apps.py`
- Create: `backend/apps/geodata/contracts.py`
- Create: `backend/apps/geodata/providers.py`
- Create: `backend/apps/geodata/service.py`
- Test: `backend/tests/test_geocoding.py`

**Interfaces:**
- Produces: `GeocodingRequest`, `GeocodingResult`, `GeocodingProvider`, `DemoGeocodingProvider`, `NominatimGeocodingProvider`, `get_geocoding_provider()`, and `geocode_address()`.

- [ ] Write failing tests for deterministic demo results, unsupported addresses, provider selection, cache keys, and disabled Nominatim.
- [ ] Run targeted tests and verify failure.
- [ ] Implement immutable request/result dataclasses and provider protocol.
- [ ] Implement Ukrainian city-centre demo coordinates with deterministic address offsets.
- [ ] Implement opt-in Nominatim with fixed host, timeout, explicit user-agent, cache, and one-request-per-second lock.
- [ ] Return stable domain exceptions instead of leaking aiohttp errors.
- [ ] Run targeted tests, Ruff, and mypy.
- [ ] Commit with `feat: add safe geocoding providers`.

### Task 4: Spatial query and distance services

**Files:**
- Create: `backend/apps/geodata/spatial.py`
- Test: `backend/tests/test_spatial_services.py`

**Interfaces:**
- Produces: `BoundingBox.parse(value)`, `filter_listings_in_bbox(queryset, bbox)`, `annotate_distance_to_place(queryset, place)`, and `serialize_listing_feature(listing, match=None)`.

- [ ] Write failing PostGIS tests for bbox parsing, invalid coordinate order, bbox filtering, and distance in kilometres.
- [ ] Run tests against the PostGIS service and verify failure.
- [ ] Implement strict bbox validation for `west,south,east,north`.
- [ ] Implement PostGIS polygon filtering and geography distance annotation.
- [ ] Implement compact GeoJSON feature serialization with listing state and optional match data.
- [ ] Run targeted tests and mypy.
- [ ] Commit with `feat: add spatial listing services`.

### Task 5: Important-place and map APIs

**Files:**
- Create: `backend/apps/geodata/serializers.py`
- Create: `backend/apps/geodata/views.py`
- Create: `backend/apps/geodata/urls.py`
- Modify: `backend/config/urls.py`
- Modify: `backend/apps/searches/serializers.py`
- Modify: `backend/apps/searches/views.py`
- Test: `backend/tests/test_map_api.py`

**Interfaces:**
- Produces API endpoints documented in the design specification and GeoJSON `FeatureCollection` responses.

- [ ] Write failing API tests for authentication, ownership, bbox validation, GeoJSON shape, listing limits, geocoding preview, place creation, place deletion, and map context.
- [ ] Run targeted API tests and verify failure.
- [ ] Add strict serializers for coordinates, bbox, geocoding preview, and important places.
- [ ] Implement user-scoped map listing endpoint with optional profile matching.
- [ ] Implement important-place CRUD and geocoding preview under owned search profiles.
- [ ] Implement map-context endpoint with nearest straight-line distances.
- [ ] Register URLs and schema annotations.
- [ ] Run targeted tests, full backend tests, Ruff, and mypy.
- [ ] Commit with `feat: add user-scoped map and important-place API`.

### Task 6: Demo data geometry and management command

**Files:**
- Modify: `backend/apps/listings/demo_source.py`
- Modify: `backend/apps/listings/services.py`
- Create: `backend/apps/geodata/management/__init__.py`
- Create: `backend/apps/geodata/management/commands/__init__.py`
- Create: `backend/apps/geodata/management/commands/geocode_demo_data.py`
- Test: `backend/tests/test_demo_geodata.py`

**Interfaces:**
- Produces deterministic geometry for demo listings and an idempotent `geocode_demo_data` command.

- [ ] Write failing tests that seeded listings contain valid points and repeated geocoding is idempotent.
- [ ] Run tests and verify failure.
- [ ] Ensure normalized listing values include synchronized geometry.
- [ ] Add command for backfilling listings and important places lacking geometry.
- [ ] Report processed, updated, unchanged, and failed counts.
- [ ] Run the command twice and assert no duplicate or drifting coordinates.
- [ ] Commit with `feat: geocode deterministic demo data`.

### Task 7: Frontend geodata API client

**Files:**
- Modify: `miniapp/src/lib/api.ts`
- Create: `miniapp/src/lib/map-types.ts`
- Test: `miniapp/src/lib/map-types.test.ts`

**Interfaces:**
- Produces: `MapFeatureCollection`, `ImportantPlace`, `MapContextResponse`, `fetchMapListings()`, `fetchImportantPlaces()`, `previewImportantPlaceGeocode()`, `createImportantPlace()`, and `deleteImportantPlace()`.

- [ ] Write failing Vitest tests for bbox query construction, GeoJSON validation, and invalid payload rejection.
- [ ] Run `npm test -- map-types.test.ts` and verify failure.
- [ ] Add strict TypeScript map types and runtime payload guards.
- [ ] Implement authenticated API functions with CSRF for mutations.
- [ ] Run targeted tests, ESLint, and typecheck.
- [ ] Commit with `feat: add map API client`.

### Task 8: Leaflet map component

**Files:**
- Modify: `miniapp/package.json`
- Modify: `miniapp/package-lock.json`
- Create: `miniapp/src/components/listing-map.tsx`
- Create: `miniapp/src/components/listing-map-client.tsx`
- Test: `miniapp/src/components/listing-map.test.tsx`

**Interfaces:**
- Produces: `<ListingMap profileId onOpenListing />` and a client-only Leaflet renderer.

- [ ] Write failing component tests for loading, empty, error, marker selection, and important-place controls using a mocked renderer.
- [ ] Run targeted tests and verify failure.
- [ ] Add exact Leaflet and React Leaflet dependencies plus type definitions.
- [ ] Implement dynamic client-only map loading.
- [ ] Render apartment and important-place markers, fit bounds, and selected marker state.
- [ ] Always show configured tile attribution.
- [ ] Preserve the last valid feature collection after refresh failures.
- [ ] Run component tests, lint, typecheck, and build.
- [ ] Commit with `feat: add interactive listing map`.

### Task 9: Important-place mobile workflow

**Files:**
- Create: `miniapp/src/components/important-place-panel.tsx`
- Modify: `miniapp/src/components/listing-map.tsx`
- Modify: `miniapp/src/app/globals.css`
- Test: `miniapp/src/components/important-place-panel.test.tsx`

**Interfaces:**
- Produces accessible address-preview-create, map-click-create, list, distance display, and delete workflows.

- [ ] Write failing tests for preview, create, validation error, map-click coordinates, and delete confirmation.
- [ ] Run targeted tests and verify failure.
- [ ] Implement the mobile bottom sheet with touch-safe controls and Telegram safe areas.
- [ ] Add address preview before persistence.
- [ ] Add map-click draft point and max-distance input.
- [ ] Add optimistic delete with rollback on API failure.
- [ ] Run targeted tests, lint, and typecheck.
- [ ] Commit with `feat: add important-place map workflow`.

### Task 10: Workspace integration and detail-map synchronization

**Files:**
- Create: `miniapp/src/components/stage-six-shell.tsx`
- Modify: `miniapp/src/app/page.tsx`
- Modify: `miniapp/src/components/listing-feed.tsx`
- Modify: `miniapp/src/app/globals.css`
- Test: `miniapp/src/components/stage-six-shell.test.tsx`

**Interfaces:**
- Produces a new `map` workspace tab and shared listing-detail opening between list and map.

- [ ] Write failing tests for map-tab navigation, active profile propagation, and opening listing details from a marker.
- [ ] Run targeted tests and verify failure.
- [ ] Extract the existing detail panel opening into a reusable callback boundary.
- [ ] Add map tab to desktop/mobile navigation.
- [ ] Keep dashboard, feed, favorites, and comparison behavior unchanged.
- [ ] Add responsive map layout and accessible tab labels.
- [ ] Run frontend tests, lint, typecheck, and production build.
- [ ] Commit with `feat: integrate map into Mini App workspace`.

### Task 11: Documentation and final verification

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/api.md`
- Modify: `docs/deployment.md`
- Create: `docs/stage-6-map-geodata.md`
- Modify: `.github/workflows/ci.yml` only if required for GIS system packages

**Interfaces:**
- Produces complete Stage 6 setup, provider, API, security, and troubleshooting documentation.

- [ ] Document PostGIS requirements, migrations, demo geocoding, map environment variables, tile attribution, and optional Nominatim configuration.
- [ ] Add Mermaid geodata flow and database updates.
- [ ] Document known limitation: straight-line distance, not travel time.
- [ ] Run backend Ruff format/check, mypy, migrations, migration drift, pytest, and pip-audit.
- [ ] Run frontend ESLint, typecheck, tests, build, and npm audit.
- [ ] Build backend and Mini App Docker images.
- [ ] Run Gitleaks.
- [ ] Open one PR, wait for all checks, fix failures in grouped commits, and squash merge only after every job succeeds.
