# FlatHunter AI

**FlatHunter AI — розумний пошук житла**: Telegram-бот і Mini App для автоматизованого персоналізованого пошуку довгострокової оренди в Україні.

> Поточний стан: **Етап 6 — Карта та геодані**. Система має Telegram onboarding, synthetic pipeline, deterministic Match Score, мобільний кабінет, PostGIS-карту квартир і важливі точки користувача.

## Реалізовано

- Django 6, DRF і GeoDjango;
- PostgreSQL 17 + PostGIS, Redis, Celery, Docker Compose та Nginx;
- Next.js Telegram Mini App з Telegram theme, safe-area й offline/error states;
- Telegram auth через перевірений `initData` і HttpOnly session;
- aiogram bot із `/start`, Mini App та FSM onboarding;
- `SearchProfile`, важливі точки й правила сповіщень;
- природномовний fallback parser без обов'язкового AI API;
- `ListingSource`, `RawListing`, `Listing` і `UserListingState`;
- legal-first adapter interface та deterministic demo source;
- 150 synthetic demo listings зі стабільними координатами;
- deterministic Match Score із поясненнями;
- dashboard, стрічка, деталі, фільтри, обране, приховування та порівняння;
- PostGIS `PointField` для квартир і важливих місць;
- GeoJSON API, bbox-фільтрація та straight-line distance через PostGIS;
- deterministic demo geocoder;
- опційний Nominatim provider із fixed host, timeout, cache, rate limit і UA-only scope;
- інтерактивна Leaflet-карта з маркерами квартир і важливих точок;
- додавання важливої точки за адресою або кліком на карту;
- ownership-захист усіх персональних геоданих;
- Ruff, mypy, pytest, ESLint, TypeScript, audits, Docker builds і Gitleaks.

## Архітектура

```mermaid
flowchart LR
    TG[Telegram User] --> MINI[Next.js Mini App]
    TG --> BOT[aiogram Bot]
    MINI --> API[Django REST API]
    BOT --> API
    SOURCE[Demo / approved source] --> RAW[(RawListing)]
    RAW --> NORMALIZE[Normalization]
    NORMALIZE --> LISTING[(Listing + PostGIS Point)]
    PROFILE[(SearchProfile)] --> MATCH[Deterministic Match Engine]
    LISTING --> MATCH
    PROFILE --> PLACE[(ImportantPlace + PostGIS Point)]
    LISTING --> GEO[Spatial / GeoJSON Service]
    PLACE --> GEO
    MATCH --> GEO
    GEO --> MAP[Leaflet Map]
    API --> DB[(PostgreSQL + PostGIS)]
    API --> REDIS[(Redis Cache / Broker)]
    API --> CELERY[Celery Workers]
```

Детальніше: [`docs/architecture.md`](docs/architecture.md) і [`docs/stage-6-map-geodata.md`](docs/stage-6-map-geodata.md).

## Запуск через Docker

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_demo_listings
docker compose exec backend python manage.py geocode_demo_data
```

Mini App: `http://localhost:8080`  
API docs: `http://localhost:8080/api/docs/`  
Liveness: `http://localhost:8080/health/live/`  
Readiness: `http://localhost:8080/health/ready/`

## Локальний backend

Stage 6 потребує PostgreSQL із PostGIS. SQLite більше не підтримується для міграцій геометрії.

```bash
cd backend
uv venv
uv pip install --python .venv/bin/python --requirement requirements-dev.lock
export DATABASE_URL=postgresql://flathunter:flathunter@localhost:5432/flathunter
uv run --no-sync python manage.py migrate
uv run --no-sync python manage.py seed_demo_listings
uv run --no-sync python manage.py geocode_demo_data
uv run --no-sync python manage.py runserver
```

Повторні запуски seed і geodata backfill ідемпотентні.

## Mini App

```bash
cd miniapp
npm ci
npm run dev
```

Браузерний preview не обходить Telegram-вхід. Карта, важливі точки та персональні стани доступні лише після серверної перевірки Telegram `initData`.

## Налаштування карти

Безпечний demo-режим працює без API-ключа:

```env
GEOCODING_PROVIDER=demo
GEOCODING_EXTERNAL_ENABLED=false
MAP_TILES_URL=https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png
MAP_ATTRIBUTION=© OpenStreetMap contributors
NEXT_PUBLIC_MAP_TILES_URL=https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png
NEXT_PUBLIC_MAP_ATTRIBUTION=© OpenStreetMap contributors
```

Nominatim є опційним і вимкнений за замовчуванням. Перед production-використанням потрібно вказати реальний контактний `GEOCODING_USER_AGENT`, перевірити usage policy провайдера та ввімкнути `GEOCODING_EXTERNAL_ENABLED=true`. URL провайдера не приймається від користувача й не може бути довільно змінений через API.

## API етапу 6

```text
GET    /api/v1/map/listings/
GET    /api/v1/search-profiles/{id}/important-places/
POST   /api/v1/search-profiles/{id}/important-places/
POST   /api/v1/search-profiles/{id}/important-places/geocode/
DELETE /api/v1/search-profiles/{id}/important-places/{place_id}/
GET    /api/v1/search-profiles/{id}/map-context/
```

Map-фільтри: `profile_id`, `bbox=west,south,east,north`, `min_score`, `favorites`, `limit`.

Map API повертає GeoJSON `FeatureCollection`. Координати завжди мають порядок `[longitude, latitude]` і SRID 4326.

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

cd ../miniapp
npm run lint
npm run typecheck
npm test
npm run build
```

## Документація

- [`docs/architecture.md`](docs/architecture.md);
- [`docs/api.md`](docs/api.md);
- [`docs/security.md`](docs/security.md);
- [`docs/deployment.md`](docs/deployment.md);
- [`docs/stage-3-demo-pipeline.md`](docs/stage-3-demo-pipeline.md);
- [`docs/stage-4-matching.md`](docs/stage-4-matching.md);
- [`docs/stage-5-miniapp-ui.md`](docs/stage-5-miniapp-ui.md);
- [`docs/stage-6-map-geodata.md`](docs/stage-6-map-geodata.md).

## Відоме обмеження

Етап 6 обчислює геодезичну відстань по прямій. Час пішки, автомобілем або громадським транспортом потребує routing provider і буде окремим розширенням.

## Наступний етап

Етап 7: exact/fuzzy duplicate matching, image hashing і `ListingCluster`.

## Legal notice

FlatHunter AI не містить механізмів обходу CAPTCHA, авторизації, rate limits, fingerprinting або приватних API. Реальні джерела й зовнішні geocoding/tiles providers підключаються лише після перевірки умов доступу. До цього система працює на synthetic demo data та явно дозволених інтеграціях.
