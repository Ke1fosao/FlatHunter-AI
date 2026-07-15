# Security baseline

## Telegram Mini App authentication

The frontend sends the **original** `initData` string. It does not trust `initDataUnsafe` as authentication evidence.

The backend:

1. parses the query string strictly;
2. rejects duplicate fields and oversized payloads;
3. removes `hash` and optional third-party `signature` from the data-check string;
4. derives the Web App secret using the Telegram bot token;
5. compares HMAC values with `hmac.compare_digest`;
6. validates `auth_date` with future tolerance and maximum age;
7. validates required user fields;
8. reserves the hash in cache to block replay;
9. creates a server-side session with HttpOnly/SameSite cookies;
10. never logs full `initData` or bot tokens.

## Webhook

- only POST is accepted;
- `X-Telegram-Bot-Api-Secret-Token` is constant-time compared;
- malformed updates are rejected before aiogram processing;
- `update_id` is reserved in Redis/cache to ensure idempotency;
- failed processing releases the reservation for a legitimate retry;
- the bot session is always closed.

## Browser preview

There is no development login bypass. Outside Telegram, the frontend renders a non-authenticated product preview and reports backend health only.

## Cookies and headers

- session cookie is HttpOnly;
- secure cookies are enabled outside debug mode;
- CORS and CSRF use explicit allowlists;
- content sniffing is disabled;
- strict referrer policy is enabled;
- HSTS is enabled in production settings;
- Nginx adds a restrictive CSP for the Mini App.

## Secrets

Secrets belong in environment variables or a deployment secret manager. `.env`, key files, local databases, caches and build artifacts are ignored by Git.

## Deferred security work

Stage 13 will add API-wide rate limiting, object-level permission tests, SSRF-safe URL import, upload validation, dependency scanning policies and a dedicated threat-model review.
