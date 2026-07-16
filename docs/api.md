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

## Listings workspace

- `GET /listings/`;
- `GET /listings/{id}/`;
- `GET /listings/dashboard/`;
- `POST /listings/{id}/favorite/`;
- `POST /listings/{id}/hide/`;
- `POST /listings/{id}/compare/`.

Listing query: `city`, `district`, `rooms`, `price_min`, `price_max`, `favorites`, `compared`, `include_hidden`, `search`, `ordering`.

State mutation:

```json
{ "value": true }
```

## Stage 6 map

### `GET /map/listings/`

Authenticated GeoJSON feed.

Query:

- `profile_id` — owned search profile for Match Score;
- `bbox` — `west,south,east,north`;
- `min_score` — 0–100;
- `favorites` — explicit boolean;
- `limit` — 1–500.

Response is a GeoJSON `FeatureCollection`. Point coordinates use `[longitude, latitude]` and SRID 4326.

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
