# FlatHunter AI

**FlatHunter AI — розумний пошук житла**: Telegram-бот і Mini App для автоматизованого персоналізованого пошуку довгострокової оренди в Україні.

> Поточний стан: **Етап 7 — пошук дублікатів і кластери оголошень**. Користувач бачить одну картку й один маркер на квартиру, але може відкрити всі публікації, ціни та першоджерела.

## Реалізовано

- Django 6, DRF і GeoDjango;
- PostgreSQL 17 + PostGIS, Redis, Celery, Docker Compose та Nginx;
- Next.js Telegram Mini App з Telegram theme, safe-area й error states;
- Telegram auth через перевірений `initData` і HttpOnly session;
- aiogram bot із `/start`, Mini App та FSM onboarding;
- `SearchProfile`, важливі точки й правила сповіщень;
- natural-language fallback parser без обов'язкового AI API;
- legal-first source adapters, `RawListing`, `Listing` і persistent user states;
- deterministic synthetic data зі стабільними координатами й контрольованими групами дублікатів;
- deterministic Match Score із поясненнями;
- dashboard, стрічка, деталі, фільтри, обране, приховування та порівняння;
- PostGIS `PointField`, GeoJSON, bbox-фільтрація й distance context;
- deterministic demo geocoder та опційний hardened Nominatim provider;
- інтерактивна Leaflet-карта з важливими точками;
- `ListingFingerprint`, explainable `DuplicateCandidate` і `ListingCluster`;
- exact, address, geo, attributes, text, trusted image та price duplicate signals;
- bounded candidate generation без unrestricted all-pairs;
- hard-conflict і transitive-poisoning protection;
- manual confirm/split/block/restore з immutable audit history;
- одна cluster-aware favorite/hidden/compare/note state;
- одна картка і один map marker на кластер;
- Ruff, mypy, pytest, ESLint, TypeScript, audits, Docker builds і Gitleaks.

## Архітектура

```mermaid
flowchart LR
    TG[Telegram User] --> MINI[Next.js Mini App]
    TG --> BOT[aiogram Bot]
    MINI --> API[Django REST API]
    BOT --> API
    SOURCE[Demo / Approved Source] --> RAW[(RawListing)]
    RAW --> NORMALIZE[Normalization]
    NORMALIZE --> LISTING[(Listing + PostGIS Point)]
    LISTING --> FP[Fingerprint]
    FP --> DUP[Explainable Duplicate Engine]
    DUP --> CLUSTER[(ListingCluster)]
    PROFILE[(SearchProfile)] --> MATCH[Deterministic Match]
    CLUSTER --> FEED[One Card + All Sources]
    CLUSTER --> MAP[One Leaflet Marker]
    MATCH --> FEED
    API --> DB[(PostgreSQL + PostGIS)]
    API --> REDIS[(Redis Cache / Broker)]
    API --> CELERY[Celery Workers]
```

Детальніше:

- [`docs/architecture.md`](docs/architecture.md);
- [`docs/stage-7-duplicate-clustering.md`](docs/stage-7-duplicate-clustering.md).

## Запуск через Docker

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

Mini App: `http://localhost:8080`  
API docs: `http://localhost:8080/api/docs/`  
Liveness: `http://localhost:8080/health/live/`  
Readiness: `http://localhost:8080/health/ready/`

Повторний запуск seed, geodata, fingerprint, detection і cluster commands є ідемпотентним для незмінених даних.

## Локальний backend

PostgreSQL із PostGIS є обов’язковим.

```bash
cd backend
uv venv
uv pip install --python .venv/bin/python --requirement requirements-dev.lock
export DATABASE_URL=postgresql://flathunter:flathunter@localhost:5432/flathunter
uv run --no-sync python manage.py migrate
uv run --no-sync python manage.py seed_demo_listings
uv run --no-sync python manage.py geocode_demo_data
uv run --no-sync python manage.py build_listing_fingerprints
uv run --no-sync python manage.py detect_listing_duplicates
uv run --no-sync python manage.py rebuild_listing_clusters
uv run --no-sync python manage.py runserver
```

## Mini App

```bash
cd miniapp
npm ci
npm run dev
```

Браузерний preview не обходить Telegram-вхід. Персональні профілі, геодані, кластери й user states доступні лише після серверної перевірки Telegram `initData`.

## Налаштування дедуплікації

Безпечні defaults:

```env
DUPLICATE_AUTO_MERGE_THRESHOLD=92
DUPLICATE_REVIEW_THRESHOLD=78
DUPLICATE_SIMHASH_BLOCK_DISTANCE=12
DUPLICATE_BLOCK_LIMIT=500
DUPLICATE_AUTO_QUEUE_ENABLED=false
DUPLICATE_TASK_QUEUE=duplicates
```

Queued incremental refresh вимкнений за замовчуванням. Спочатку виконайте dry-run і перевірте decision distribution у staging.

Image fingerprint command працює лише з trusted imported/demo metadata й не завантажує довільні URL:

```bash
python manage.py process_listing_image_hashes
```

## API етапу 7

```text
GET   /api/v1/listing-clusters/{cluster_id}/
PATCH /api/v1/listing-clusters/{cluster_id}/state/

GET  /api/v1/duplicate-candidates/                         staff only
POST /api/v1/duplicate-candidates/{candidate_id}/confirm/ staff only
POST /api/v1/duplicate-candidates/{candidate_id}/split/   staff only
POST /api/v1/duplicate-candidates/{candidate_id}/restore/ staff only
```

Existing listing, match, dashboard and map endpoints remain backward compatible and add:

```text
cluster_id
source_count
member_count
is_cluster_primary
price_min_uah
price_max_uah
```

Default feeds return only standalone listings and active cluster primaries.

## Перевірки

```bash
make check
```

Окремо:

```bash
cd backend
uv run --no-sync ruff format --check apps config tests manage.py
uv run --no-sync ruff check apps config tests manage.py
uv run --no-sync mypy apps config
uv run --no-sync python manage.py migrate --noinput
uv run --no-sync python manage.py makemigrations --check --dry-run
uv run --no-sync pytest
uvx pip-audit --strict -r requirements.lock

cd ../miniapp
npm run lint
npm run typecheck
npm test
npm run build
npm audit --audit-level=high
```

## Документація

- [`docs/architecture.md`](docs/architecture.md);
- [`docs/api.md`](docs/api.md);
- [`docs/security.md`](docs/security.md);
- [`docs/deployment.md`](docs/deployment.md);
- [`docs/cloud-hosting.md`](docs/cloud-hosting.md);
- [`docs/stage-3-demo-pipeline.md`](docs/stage-3-demo-pipeline.md);
- [`docs/stage-4-matching.md`](docs/stage-4-matching.md);
- [`docs/stage-5-miniapp-ui.md`](docs/stage-5-miniapp-ui.md);
- [`docs/stage-6-map-geodata.md`](docs/stage-6-map-geodata.md);
- [`docs/stage-7-duplicate-clustering.md`](docs/stage-7-duplicate-clustering.md).

## Відомі обмеження

- routing time пішки/авто/транспортом ще потребує окремого routing provider;
- production image downloading intentionally не реалізовано без source allowlist і окремої security review;
- повноцінна moderation workspace запланована для admin етапу, а Stage 7 надає Django Admin і staff API primitives.

## Наступний етап

Етап 8: AI enrichment поверх deterministic pipeline — структурований аналіз опису, extraction і language assistance без передачі AI права вирішувати duplicate identity.

## Legal notice

FlatHunter AI не містить механізмів обходу CAPTCHA, авторизації, rate limits, fingerprinting або приватних API. Реальні джерела й зовнішні providers підключаються лише після перевірки умов доступу. До цього система працює на synthetic demo data та явно дозволених інтеграціях.
