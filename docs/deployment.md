# Deployment

## Local Docker deployment

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_demo_listings
docker compose exec backend python manage.py geocode_demo_data
docker compose exec backend python manage.py build_listing_fingerprints
docker compose exec backend python manage.py detect_listing_duplicates
docker compose exec backend python manage.py rebuild_listing_clusters
```

To include Telegram long polling:

```bash
docker compose --profile polling up --build -d
```

Only use polling for local development.

## PostGIS requirements

The project requires PostgreSQL with the PostGIS extension. SQLite is not supported for geometry migrations or spatial queries.

The backend image installs GDAL, GEOS, PROJ and PostgreSQL runtime libraries. The database service uses `postgis/postgis:17-3.5`.

Default safe map configuration:

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

External geocoding is opt-in. Review provider policy, configure a real contact User-Agent, keep caching/rate limits active and never expose a user-controlled provider URL. Tile attribution must remain visible.

## Stage 7 duplicate rollout

Safe defaults:

```env
DUPLICATE_AUTO_MERGE_THRESHOLD=92
DUPLICATE_REVIEW_THRESHOLD=78
DUPLICATE_SIMHASH_BLOCK_DISTANCE=12
DUPLICATE_BLOCK_LIMIT=500
DUPLICATE_AUTO_QUEUE_ENABLED=false
DUPLICATE_TASK_QUEUE=duplicates
```

Initial rollout order:

1. deploy code and apply migrations;
2. build fingerprints;
3. run detection in dry-run mode per city;
4. inspect decision distributions and high-score review candidates;
5. run persisted detection;
6. rebuild clusters;
7. repeat fingerprint/detection/rebuild and confirm stable counts;
8. verify one card and one map marker per cluster;
9. enable incremental queueing only after staging evidence is acceptable.

Commands:

```bash
docker compose exec backend python manage.py build_listing_fingerprints --dry-run
docker compose exec backend python manage.py detect_listing_duplicates --city Львів --dry-run
docker compose exec backend python manage.py rebuild_listing_clusters --city Львів --dry-run

docker compose exec backend python manage.py build_listing_fingerprints
docker compose exec backend python manage.py detect_listing_duplicates
docker compose exec backend python manage.py rebuild_listing_clusters
```

The image command is offline by design:

```bash
docker compose exec backend python manage.py process_listing_image_hashes
```

It processes trusted imported/demo metadata only and never downloads arbitrary remote images.

When queued incremental refresh is approved, set:

```env
DUPLICATE_AUTO_QUEUE_ENABLED=true
```

Route the `duplicates` queue to at least one Celery worker. Keep it disabled during migrations and bulk imports to avoid unnecessary repeated cluster rebuilds.

## Production prerequisites

- Linux host or managed container platform;
- public domain with HTTPS;
- PostgreSQL 17 with PostGIS;
- Redis with persistence and restricted network access;
- unique high-entropy Django secret and webhook secret;
- Telegram bot token stored outside Git;
- one Celery Beat instance only;
- approved geocoding and tile provider configuration;
- reviewed duplicate thresholds and image-source policy;
- database backups including PostGIS and duplicate audit tables;
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
docker compose exec backend python manage.py build_listing_fingerprints
docker compose exec backend python manage.py detect_listing_duplicates
docker compose exec backend python manage.py rebuild_listing_clusters
```

All duplicate commands are idempotent for unchanged data. Manual split/block decisions survive re-evaluation until explicitly restored.

## Monitoring and alerts

Track:

- fingerprint failures;
- candidate counts by decision and algorithm version;
- auto-merge and manual-split rates;
- average and maximum cluster size;
- cluster rebuild duration;
- clusters with missing/inactive primary;
- Celery duplicate queue depth;
- cluster-state update failures.

Alert when manual split rate rises after an algorithm/threshold change.

## Rollback

Disable incremental work immediately:

```env
DUPLICATE_AUTO_QUEUE_ENABLED=false
```

Original listings are never deleted. Active clusters can be archived to restore independent listing presentation while preserving audit history.

## Verification

```bash
curl --fail https://YOUR_DOMAIN/health/live/
curl --fail https://YOUR_DOMAIN/health/ready/
curl --fail https://YOUR_DOMAIN/health
```

Authenticated verification should confirm:

- listing and match feeds return one primary per cluster;
- cluster detail returns every source copy;
- favorite/hide/compare/note are shared by the cluster;
- one cluster consumes one comparison slot;
- `/api/v1/map/listings/` returns one marker per cluster;
- foreign profile IDs return `404`;
- staff-only duplicate actions return `403` for normal users;
- external geocoding and remote image fetching remain disabled unless explicitly approved.
