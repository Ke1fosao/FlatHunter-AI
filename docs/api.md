# API — Stage 1

Base path: `/api/v1/`

## Public health

- `GET /health/` — aggregated backend readiness for Mini App;
- `GET /health/live/` — process liveness;
- `GET /health/ready/` — database and cache readiness.

## Telegram authentication

### `POST /auth/telegram/`

Body:

```json
{ "initData": "query_id=...&user=...&auth_date=...&hash=..." }
```

The backend validates the original query string, HMAC signature, freshness and replay. A successful response creates a server-side session and returns only safe user fields.

### `GET /me/`

Requires an authenticated session.

### `POST /logout/`

Terminates the backend session.

## Telegram bot

- `POST /telegram/webhook/` — protected by `X-Telegram-Bot-Api-Secret-Token`;
- `GET /telegram/status/` — safe configuration status without secrets.

## Schema

- `GET /api/schema/` — OpenAPI JSON;
- `GET /api/docs/` — Swagger UI.

All errors use a normalized shape:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed",
    "details": {}
  }
}
```
