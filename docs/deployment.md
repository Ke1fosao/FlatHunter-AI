# Deployment

## Local Docker deployment

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_demo_listings
docker compose exec backend python manage.py geocode_demo_data
```

To include Telegram long polling:

```bash
docker compose --profile polling up --build -d
```

Only use polling for local development.

## Stage 6 geodata requirements

Stage 6 requires PostgreSQL with the PostGIS extension. SQLite is not supported for geometry migrations or spatial queries.

The backend image installs:

- GDAL;
- GEOS;
- PROJ;
- PostgreSQL runtime libraries.

The database service uses `postgis/postgis:17-3.5`.

Default safe configuration:

```env
GEOCODING_PROVIDER=demo
GEOCODING_EXTERNAL_ENABLED=false
GEOCODING_TIMEOUT_SECONDS=8
GEOCODING_CACHE_SECONDS=2592000
MAP_TILES_URL=https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png
MAP_ATTRIBUTION=© OpenStreetMap contributors
NEXT_PUBLIC_MAP_TILES_URL=https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png
NEXT_PUBLIC_MAP_ATTRIBUTION=© OpenStreetMap contributors
```

External geocoding is opt-in. Before enabling Nominatim:

- review the current provider usage policy;
- set a real contact in `GEOCODING_USER_AGENT`;
- ensure cache and rate limiting are active;
- keep the endpoint fixed in backend code;
- set `GEOCODING_EXTERNAL_ENABLED=true` only after review.

Tile attribution must remain visible in the Mini App.

## Production prerequisites

- Linux host or managed container platform;
- public domain with HTTPS;
- PostgreSQL 17 with PostGIS;
- Redis with persistence and restricted network access;
- unique high-entropy Django secret and webhook secret;
- Telegram bot token stored outside Git;
- one Celery Beat instance only;
- approved geocoding and tile provider configuration;
- database backups including PostGIS data;
- monitoring configured before live data is enabled.

## Production compose

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.production.yml \
  up --build -d
```

The included Nginx config is a gateway baseline. TLS termination must be added through a reverse proxy, ingress or certificate automation before enabling Telegram webhook mode.

## Register Telegram webhook

After HTTPS is active, configure Telegram `setWebhook` from a secure operator environment with:

- URL: `https://YOUR_DOMAIN/api/v1/telegram/webhook/`;
- `secret_token`: the same value as `TELEGRAM_WEBHOOK_SECRET`;
- only required update types.

Never put the bot token in shell history on a shared machine.

## Migrations and backfill

The backend container runs migrations and static collection when `RUN_MIGRATIONS=true` and `COLLECT_STATIC=true`. Celery and bot containers do not repeat migrations.

Manual commands:

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py geocode_demo_data
```

The Stage 6 migrations add PostGIS point fields and backfill them from existing decimal coordinates. `geocode_demo_data` is an idempotent operational backfill for records that still lack geometry.

## Verification

```bash
curl --fail https://YOUR_DOMAIN/health/live/
curl --fail https://YOUR_DOMAIN/health/ready/
curl --fail https://YOUR_DOMAIN/health
```

Authenticated map verification should confirm:

- `/api/v1/map/listings/` returns a GeoJSON FeatureCollection;
- every geometry is a Point;
- tile attribution is visible;
- foreign profile IDs return `404`;
- external geocoding remains disabled unless explicitly approved.
