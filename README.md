# FlatHunter AI

**FlatHunter AI — розумний пошук житла**: Telegram-бот і Mini App для автоматизованого персоналізованого пошуку довгострокової оренди в Україні.

> Поточний стан: **Етап 3 — Demo data pipeline**. Система вже має production-oriented основу, Telegram onboarding, пошукові профілі, synthetic demo source, окремі raw/normalized моделі оголошень, seed-команду та API-стрічку квартир.

## Реалізовано

- Django 6 + Django REST Framework;
- Next.js Telegram Mini App з UA/EN, Telegram theme, safe-area та offline states;
- Telegram auth через перевірений `initData` і HttpOnly session;
- aiogram bot із `/start`, Mini App та FSM onboarding;
- `SearchProfile`, важливі точки й правила сповіщень;
- природномовний fallback parser без обов'язкового AI API;
- `ListingSource`, `RawListing`, `Listing`;
- adapter interface для джерел;
- legal-first source policy;
- deterministic `DemoListingSourceAdapter`;
- ідемпотентний ingestion pipeline;
- 150 synthetic demo listings;
- read-only listing feed API з фільтрами, пошуком і сортуванням;
- Mini App feed, loading, empty та authentication states;
- PostgreSQL/PostGIS, Redis, Celery, Docker Compose, Nginx і CI;
- Ruff, mypy, pytest, ESLint, TypeScript, audits, Docker builds і Gitleaks.

## Архітектура

```mermaid
flowchart LR
    TG[Telegram User] --> BOT[aiogram Bot]
    TG --> MINI[Next.js Mini App]
    MINI --> API[Django REST API]
    BOT --> API
    CMD[seed_demo_listings] --> ADAPTER[Demo Source Adapter]
    ADAPTER --> RAW[(RawListing)]
    RAW --> NORMALIZE[Normalization Service]
    NORMALIZE --> LISTING[(Listing)]
    LISTING --> API
    API --> DB[(PostgreSQL / PostGIS)]
    API --> REDIS[(Redis)]
    API --> CELERY[Celery Workers]
```

Детальніше: [`docs/architecture.md`](docs/architecture.md) і [`docs/stage-3-demo-pipeline.md`](docs/stage-3-demo-pipeline.md).

## Запуск через Docker

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec backend python manage.py seed_demo_listings
```

Mini App: `http://localhost:8080`  
API docs: `http://localhost:8080/api/docs/`  
Liveness: `http://localhost:8080/health/live/`  
Readiness: `http://localhost:8080/health/ready/`

## Локальний backend

```bash
cd backend
uv venv
uv pip install --python .venv/bin/python --requirement requirements-dev.lock
uv run --no-sync python manage.py migrate
uv run --no-sync python manage.py seed_demo_listings
uv run --no-sync python manage.py runserver
```

Повторний запуск seed-команди безпечний: однаковий dataset не створює дублікати.

```bash
uv run --no-sync python manage.py seed_demo_listings --count 150 --seed 20260716
```

## Mini App

```bash
cd miniapp
npm ci
npm run dev
```

Браузерний preview не обходить Telegram-вхід. Реальна персональна стрічка доступна після серверної перевірки Telegram `initData`.

## Listing API

```text
GET /api/v1/listings/
GET /api/v1/listings/{id}/
```

Фільтри: `city`, `rooms`, `price_min`, `price_max`, `district`, `search`, `ordering`.

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
- [`docs/bot-flows.md`](docs/bot-flows.md);
- [`docs/data-sources.md`](docs/data-sources.md);
- [`docs/security.md`](docs/security.md);
- [`docs/deployment.md`](docs/deployment.md);
- [`docs/demo.md`](docs/demo.md);
- [`docs/stage-3-demo-pipeline.md`](docs/stage-3-demo-pipeline.md).

## Наступний етап

Етап 4 додасть детермінований Match Score, складові оцінки, пояснення, персональну фільтрацію та сортування.

## Legal notice

FlatHunter AI не містить механізмів обходу CAPTCHA, авторизації, rate limits, fingerprinting або приватних API. Реальні джерела підключаються тільки після перевірки умов доступу. До цього система працює на synthetic demo data, ручному імпорті та офіційно дозволених інтеграціях.
