# FlatHunter AI API

Base path: `/api/v1/`

Усі endpoints, крім health і Telegram webhook, використовують authenticated HttpOnly session. Помилки мають normalized shape:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed",
    "details": {}
  }
}
```

## Health

- `GET /health/` — aggregated backend readiness для Mini App;
- `GET /health/live/` — process liveness;
- `GET /health/ready/` — database/cache readiness.

## Telegram authentication

### `POST /auth/telegram/`

```json
{ "initData": "query_id=...&user=...&auth_date=...&hash=..." }
```

Backend перевіряє original query string, HMAC, freshness і replay. Успішна відповідь створює server-side session.

- `GET /me/` — поточний користувач;
- `POST /logout/` — завершення session;
- `POST /telegram/webhook/` — Telegram webhook із secret header;
- `GET /telegram/status/` — safe configuration status.

## Search profiles

- `GET /search-profiles/`;
- `POST /search-profiles/`;
- `GET/PATCH/DELETE /search-profiles/{id}/`;
- `POST /search-profiles/{id}/activate/`;
- `POST /search-profiles/{id}/pause/`;
- `POST /search-profiles/parse-natural-language/`;
- `GET /search-profiles/{id}/matches/`.

Matches query: `min_score`, `eligible_only`, `ordering`, `limit`.

Match results are cluster-aware: active duplicate clusters contribute only their primary listing, while standalone listings remain unchanged.

## Listings workspace

- `GET /listings/`;
- `GET /listings/{id}/`;
- `GET /listings/dashboard/`;
- `POST /listings/{id}/favorite/`;
- `POST /listings/{id}/hide/`;
- `POST /listings/{id}/compare/`.

Listing query: `city`, `district`, `rooms`, `price_min`, `price_max`, `favorites`, `compared`, `include_hidden`, `search`, `ordering`.

Staff may use `include_duplicates=true` for diagnostic listing feeds. Regular users always receive standalone listings and active cluster primaries.

Every listing payload includes:

```json
{
  "cluster_id": "uuid-or-null",
  "source_count": 2,
  "member_count": 3,
  "is_cluster_primary": true,
  "price_min_uah": 18000,
  "price_max_uah": 19000,
  "analysis_summary": {
    "market": {"status": "ready", "median_price_uah": 18000, "confidence_label": "high"},
    "risk": {"status": "ready", "score": 32, "level": "review"},
    "latest_price_change": null
  }
}
```

State mutation:

```json
{ "value": true }
```

Legacy listing state endpoints automatically route clustered listings to cluster-level state.

## Stage 7 listing clusters

### `GET /listing-clusters/{cluster_id}/`

Returns:

- canonical primary listing;
- active source copies ordered primary-first;
- confidence and concise duplicate reasons;
- price range;
- cluster user state;
- optional Match Score.

Optional query:

```text
profile_id={owned_search_profile_uuid}
```

### `PATCH /listing-clusters/{cluster_id}/state/`

Supports any non-empty subset:

```json
{
  "is_favorite": true,
  "is_hidden": false,
  "is_compared": true,
  "note": "Уточнити комісію"
}
```

One cluster occupies one comparison slot. The global maximum remains four apartments.

### Staff duplicate review

- `GET /duplicate-candidates/`;
- `GET /duplicate-candidates/{id}/`;
- `POST /duplicate-candidates/{id}/confirm/`;
- `POST /duplicate-candidates/{id}/split/`;
- `POST /duplicate-candidates/{id}/restore/`.

Review payload:

```json
{ "note": "Reason for the decision" }
```

All candidate review actions require staff permission and create immutable audit history.

## Map

### `GET /map/listings/`

Authenticated GeoJSON feed.

Query:

- `profile_id` — owned search profile for Match Score;
- `bbox` — `west,south,east,north`;
- `min_score` — 0–100;
- `favorites` — explicit boolean;
- `limit` — 1–500.

Response is a GeoJSON `FeatureCollection`. Point coordinates use `[longitude, latitude]` and SRID 4326. Duplicate clusters produce one marker with cluster metadata and price range.

### Important places

- `GET /search-profiles/{profile_id}/important-places/`;
- `POST /search-profiles/{profile_id}/important-places/`;
- `POST /search-profiles/{profile_id}/important-places/geocode/`;
- `DELETE /search-profiles/{profile_id}/important-places/{place_id}/`.

Coordinates must be supplied together. Otherwise an address is required and backend geocoding is used. `max_distance_km` must be between `0.10` and `100.00`.

### `GET /search-profiles/{profile_id}/map-context/`

Query `listing_ids` accepts up to 100 comma-separated UUID values. The response contains owned places and straight-line PostGIS distances for each requested listing.

## Stage 8 AI layer

AI endpoints return structured, schema-validated output. The deterministic search, map, matching and listing flows remain available when AI is disabled or unavailable.

### `POST /search-profiles/parse-natural-language/`

```json
{
  "text": "Шукаю однокімнатну квартиру у Львові до 18 тисяч, до 25 хв від політехніки"
}
```

Response contains:

- normalized search `data`;
- per-field `confidence` in range `0..1`;
- `missing_fields`;
- AI/fallback `meta`.

### `POST /ai/listings/{listing_id}/summary/`

Empty JSON body is accepted. Returns:

- `summary`;
- `advantages`;
- `caveats`;
- `unknowns`;
- `confidence`;
- `meta`.

### `POST /ai/listings/{listing_id}/owner-questions/`

```json
{
  "search_profile_id": "optional-owned-profile-uuid"
}
```

The profile is optional. When present, questions account for pets, children and configured filters. The endpoint never contacts the owner automatically.

### `POST /ai/listings/compare/`

```json
{
  "listing_ids": ["uuid-1", "uuid-2"],
  "search_profile_id": "optional-owned-profile-uuid"
}
```

Rules:

- `listing_ids` must contain 2–5 unique UUIDs;
- every listing must be active and belong to an enabled legally approved source;
- `search_profile_id`, when supplied, must belong to the authenticated user;
- recommendation is profile-aware through deterministic Match Score;
- a listing is marked decisive only when the score gap is meaningful;
- unavailable facts remain in `unknowns` instead of being invented.

Comparison rows may include:

```json
{
  "id": "uuid",
  "price_uah": 16500,
  "commission": "потрібно уточнити",
  "known_first_payment_uah": null,
  "match_score": 92,
  "risk_score": null,
  "travel_minutes": null,
  "advantages": [],
  "disadvantages": [],
  "unknowns": ["deposit", "risk_score", "travel_time"]
}
```

`risk_score` is populated only from a persisted validated non-stale Stage 9 assessment. Exact `travel_minutes` stays `null` until a routing provider is available.

### AI metadata

```json
{
  "meta": {
    "feature": "listings.compare",
    "provider": "local_rules",
    "model": "local-rules-v1",
    "prompt_version": "listings-compare-v2",
    "status": "success",
    "latency_ms": 7,
    "attempts": 1,
    "cache_key": "sanitized-hash"
  }
}
```

Status values:

- `success`;
- `cached`;
- `fallback`;
- `disabled`.

Fallback responses additionally include a safe `reason`, such as `provider_error`, `provider_unavailable`, `circuit_open` or `daily_budget_exhausted`.

## Stage 9 Risk і market analysis

- `GET /listings/{id}/price-history/` — current price and real normalized price-change events;
- `GET /listings/{id}/market-analysis/` — median, Q1/Q3, price/m², deviation, sample size, confidence and status;
- `GET /listings/{id}/risk-analysis/` — explainable score, neutral level, signals, safety advice and disclaimer;
- `POST /listings/{id}/analysis/refresh/` — throttled idempotent refresh.

Refresh accepts only:

```json
{ "force": false }
```

Optional header `Idempotency-Key` deduplicates repeated commands. Provider names, weights and algorithms are server-controlled and cannot be supplied by frontend. Endpoints return `404` for inactive listings or sources without `approved`/`approved_demo` legal status. `insufficient_data`, `stale`, `failed` and `disabled` are normal explicit states rather than fabricated numbers or HTTP 500.

## Schema

- `GET /api/schema/` — OpenAPI JSON;
- `GET /api/docs/` — Swagger UI.
