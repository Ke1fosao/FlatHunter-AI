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
  "price_max_uah": 19000
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

## Schema

- `GET /api/schema/` — OpenAPI JSON;
- `GET /api/docs/` — Swagger UI.
