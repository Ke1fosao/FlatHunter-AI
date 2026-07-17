# FlatHunter AI

**FlatHunter AI — розумний пошук житла**: Telegram-бот і Mini App для автоматизованого персоналізованого пошуку довгострокової оренди в Україні.

> Поточний стан: **Етап 8 — безпечний AI-шар**. Система має deterministic search/matching, PostGIS-карту, guarded duplicate clusters і user-facing AI workspace для структурованого аналізу без передачі AI права вигадувати факти або приймати рішення за користувача.

## Реалізовано

- Django 6, DRF і GeoDjango;
- PostgreSQL 17 + PostGIS, Redis, Celery, Docker Compose та Nginx;
- Next.js Telegram Mini App з Telegram theme, safe-area й error states;
- Telegram auth через перевірений `initData` і HttpOnly session;
- aiogram bot із `/start`, Mini App та FSM onboarding;
- `SearchProfile`, важливі точки й правила сповіщень;
- natural-language parser з deterministic fallback і confidence;
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
- typed `AIProvider` abstraction і offline `local_rules` provider;
- суворі AI output schemas та deterministic fallback;
- AI summary, profile-aware owner questions і profile-aware comparison 2–5 квартир;
- Mini App AI workspace з copy-ready текстом без автоматичного надсилання;
- timeout, retry, result cache, circuit breaker і daily budget guard;
- sanitized `AIRequest` audit і `AIPromptVersion` registry;
- Ruff, mypy, pytest, ESLint, TypeScript, Vitest, audits, Docker builds і Gitleaks.

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
    PROFILE --> AI[Safe AI Orchestration]
    CLUSTER --> AI
    AI --> PROVIDER[Typed AIProvider]
    AI --> FALLBACK[Deterministic Rules]
    AI --> AUDIT[(AIRequest + Prompt Versions)]
    AI --> MINI
    API --> DB[(PostgreSQL + PostGIS)]
    API --> REDIS[(Redis Cache / Broker / Circuit)]
    API --> CELERY[Celery Workers]
```

Детальніше:

- [`docs/architecture.md`](docs/architecture.md);
- [`docs/stage-7-duplicate-clustering.md`](docs/stage-7-duplicate-clustering.md);
- [`docs/stage-8-ai.md`](docs/stage-8-ai.md).

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

Браузерний preview не обходить Telegram-вхід. Персональні профілі, геодані, кластери, user states й AI context доступні лише після серверної перевірки Telegram `initData`.

## Налаштування AI

Безпечний локальний режим:

```env
AI_PROVIDER=local_rules
AI_MODEL=local-rules-v1
AI_ENABLED=false
AI_DAILY_BUDGET=0
AI_TIMEOUT_SECONDS=15
AI_MAX_RETRIES=1
AI_CACHE_SECONDS=300
AI_CIRCUIT_BREAKER_FAILURES=3
AI_CIRCUIT_BREAKER_COOLDOWN_SECONDS=60
```

`AI_ENABLED=false` залишає deterministic parser та всі core flows працездатними без зовнішнього provider. Для демонстрації provider contract і audit можна встановити `AI_ENABLED=true` з `AI_PROVIDER=local_rules`.

Remote provider у production дозволено підключати лише окремим reviewed adapter із secret manager, schema validation, timeout, cost metadata та бюджетним лімітом.

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

## API етапу 8

```text
POST /api/v1/search-profiles/parse-natural-language/
POST /api/v1/ai/listings/{listing_id}/summary/
POST /api/v1/ai/listings/{listing_id}/owner-questions/
POST /api/v1/ai/listings/compare/
```

`owner-questions` і `compare` приймають optional `search_profile_id`. Backend перевіряє, що профіль належить authenticated user.

Comparison приймає 2–5 унікальних listing IDs. Рекомендація ґрунтується на deterministic Match Score; при незначній різниці система прямо повідомляє, що однозначного переможця немає.

Кожна відповідь містить `meta` зі status `success`, `cached`, `fallback` або `disabled`, provider/model/prompt version, latency та безпечним fallback reason.

Повна API-документація: [`docs/api.md`](docs/api.md).

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
- [`docs/stage-7-duplicate-clustering.md`](docs/stage-7-duplicate-clustering.md);
- [`docs/stage-8-ai.md`](docs/stage-8-ai.md).

## Відомі обмеження

- production remote LLM adapter ще не підключений; `local_rules` є offline demo/fallback provider;
- token/cost audit fields готові, але реальні значення має надати майбутній remote provider;
- routing time пішки/авто/транспортом ще потребує окремого routing provider;
- Risk Score, ринкова оцінка й історія ціни не вигадуються та належать наступному етапу;
- production image downloading intentionally не реалізовано без source allowlist і окремої security review;
- повноцінна moderation workspace запланована для admin етапу, а Stage 7 надає Django Admin і staff API primitives.

## Наступний етап

Етап 9: ринкова оцінка ціни, Risk Score, історія ціни й пояснення ризиків без юридичних висновків або фальшивої точності.

## Legal notice

FlatHunter AI не містить механізмів обходу CAPTCHA, авторизації, rate limits, fingerprinting або приватних API. Реальні джерела й зовнішні providers підключаються лише після перевірки умов доступу. До цього система працює на synthetic demo data та явно дозволених інтеграціях.
