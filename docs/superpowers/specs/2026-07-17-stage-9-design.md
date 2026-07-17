# Stage 9 — Risk і market analysis

Дата: 2026-07-17  
Статус: затверджено користувачем, реалізація та перевірка тривають

## Мета

Stage 9 додає автономний аналітичний шар для квартир:

- версіоновані snapshots оголошення;
- достовірну історію зміни ціни;
- ринкову оцінку за схожими активними оголошеннями;
- пояснюваний детермінований Risk Score 0–100;
- warning UI у стрічці, деталях і порівнянні;
- контракт для майбутнього зовнішнього market-data provider без залежності від нього зараз.

Система не створює фальшиву точність, не називає автора шахраєм і не ламає core search, коли аналіз вимкнений або даних недостатньо.

## Межі Stage 9

Входить:

- новий Django app `apps.analysis`;
- `ListingSnapshot`;
- `ListingPriceHistory`;
- `ListingMarketAssessment`;
- `ListingRiskAssessment`;
- deterministic local market provider;
- comparable selection, robust statistics і confidence;
- Risk Score engine;
- API, permissions, idempotent refresh;
- Mini App analytics UI;
- synthetic demo scenarios;
- management commands, Celery wrappers, тести й документація.

Не входить:

- Telegram-сповіщення — Stage 10;
- платні market APIs;
- юридична або фінансова експертиза;
- автоматичне блокування оголошень за Risk Score;
- непояснювана ML-модель;
- сторонній scraping або обхід захисту.

## Архітектура

```text
apps/analysis/
├── models.py
├── contracts.py
├── providers.py
├── snapshots.py
├── comparables.py
├── market.py
├── risk.py
├── services.py
├── tasks.py
├── serializers.py
├── views.py
├── urls.py
└── management/commands/
```

Відповідальність:

- `snapshots.py` — канонічний allowlisted стан Listing і визначення змін;
- `comparables.py` — bounded cluster-aware добір аналогів;
- `market.py` — медіана, квартилі, price/m², відхилення та confidence;
- `risk.py` — незалежні RiskSignal і агрегування score;
- `providers.py` — local provider та стабільний контракт adapters;
- `services.py` — транзакції, persistence, idempotency й orchestration;
- `tasks.py` — тонкі Celery wrappers без дублювання domain logic.

## Моделі

### ListingSnapshot

Зберігає нормалізований аналітичний стан, а не повний raw payload:

- `listing`, `captured_at`, `content_hash`;
- `price_uah`, `currency`;
- hashes заголовка й опису;
- місто, район, вулиця;
- кімнати, площа, поверхи;
- тип будинку, ремонт, опалення;
- pets/children/commission/owner;
- allowlisted `attributes_summary`;
- active/source-seen metadata.

Unique `(listing, content_hash)`, index `(listing, -captured_at)`.

### ListingPriceHistory

Створюється лише при реальній зміні нормалізованої ціни:

- `listing`, `snapshot`;
- попередня й нова ціна;
- абсолютна й відсоткова зміна;
- direction;
- changed/detected timestamps.

Unique `(listing, snapshot)` і constraint проти нульової зміни.

### ListingMarketAssessment

Версійований результат:

- status: `ready`, `insufficient_data`, `stale`, `failed`;
- median, Q1, Q3;
- median і target price/m²;
- deviation from median;
- comparable count;
- confidence label і score;
- comparable IDs;
- selection summary та explanation;
- algorithm version, input hash, calculated/valid timestamps, error code.

### ListingRiskAssessment

- status;
- score 0–100;
- level: `low`, `review`, `elevated`, `insufficient_data`;
- signals і protective signals;
- summary та safety advice;
- optional market assessment;
- algorithm version, input hash, timestamps, error code.

Кожен сигнал має стабільний контракт: `code`, `weight`, `severity`, `evidence`, `label`, `recommendation`.

## Snapshot і price-history flow

Після create/update Listing:

1. створити канонічний allowlisted snapshot;
2. порахувати SHA-256 content hash;
3. не створювати дублікат із тим самим hash;
4. при новому snapshot порівняти ціну з попереднім;
5. price event створити лише при фактичній зміні;
6. через `transaction.on_commit` запланувати bounded market/risk refresh.

Unchanged ingestion лише оновлює `last_seen_at`. Backfill наявних квартир створює baseline snapshot без вигаданих price events.

## Market provider

```python
class MarketAnalysisProvider(Protocol):
    provider_name: str
    model_version: str

    def select_comparables(self, listing: Listing) -> ComparableSet: ...
    def assess(self, listing: Listing, comparables: ComparableSet) -> MarketAssessmentResult: ...
```

Default: `LocalDeterministicMarketProvider`. Невідомий або вимкнений provider повертає безпечний status, а не HTTP 500.

## Добір аналогів

Кандидати повинні бути:

- активними;
- з enabled approved source;
- не target Listing;
- не членом того самого ListingCluster;
- у нормалізованій UAH;
- достатньо свіжими;
- із позитивною ціною.

Bounded cascade:

1. місто + район + кімнати + площа ±20%;
2. місто + георадіус + кімнати + площа ±25%;
3. місто + кімнати + тип будинку/ремонт;
4. місто + кімнати як fallback.

У вибірці використовується primary listing кластера, тому одна квартира з кількох джерел не спотворює статистику. Limits, freshness, radius і tolerances задаються settings.

## Market statistics

Рахуються:

- median;
- inclusive Q1/Q3;
- IQR;
- median price/m²;
- target deviation;
- sample size;
- confidence.

Extreme observations за IQR fences не зникають мовчки: їх кількість записується в summary. При недостатній вибірці необґрунтовані числа повертаються як `null`.

Confidence враховує sample size, частку точних географічних збігів, свіжість, повноту площі, dispersion і location accuracy.

## Risk Score

Детерміновані сигнали:

- ціна суттєво нижча за ринок лише при достатньому market confidence;
- різкі або численні зміни ціни;
- повторне перевиставлення;
- trusted image reuse у різних містах;
- hard conflicts із duplicate engine;
- суперечність міста й опису;
- дуже короткий або шаблонний опис;
- фрази з вимогою передоплати;
- небезпечні зовнішні посилання;
- відсутність базових полів;
- суперечлива або прихована комісія;
- невідповідність адреси й trusted coordinates;
- розбіжності між джерелами одного кластера.

Protective signals можуть зменшувати сирий score, але не приховують high-severity evidence.

Рівні:

- 0–24: low;
- 25–49: review;
- 50–100: elevated;
- `insufficient_data`: окремо.

Текст завжди нейтральний: перевірити документи, особу, право власності й договір; не переказувати кошти до перегляду й перевірки.

## API

```text
GET  /api/v1/listings/{id}/price-history/
GET  /api/v1/listings/{id}/market-analysis/
GET  /api/v1/listings/{id}/risk-analysis/
POST /api/v1/listings/{id}/analysis/refresh/
```

Refresh:

- authenticated;
- object-authorized;
- throttled;
- підтримує idempotency key;
- не приймає provider або weights від frontend;
- повертає current result або `202 accepted`.

Listing serializer отримує compact `analysis_summary`. Відсутність результату повертається як pending/insufficient/stale, не як 500.

## Mini App

### Feed/cluster card

- badge зміни ціни;
- market chip лише при medium/high confidence;
- risk chip із icon + text, не тільки кольором;
- максимум один короткий warning.

### Listing detail

Блок «Аналітика квартири»:

- current price і market range;
- confidence та comparable count;
- price-history chart і текстова альтернатива;
- Risk Score та level;
- пояснювані signals;
- safety advice;
- disclaimer «Допоміжна оцінка, не юридичний висновок»;
- timestamp, stale, failed і retry states.

### Compare/AI

Stage 8 отримує тільки validated Stage 9 context. AI не перераховує score самостійно й не вигадує результат при insufficient data.

UI має mobile safe-area, touch targets від 44 px, null-safe rendering, loading/empty/stale/error states та accessibility labels.

## Demo data

Deterministic сценарії:

- price drops і increases між revisions;
- квартира нижче медіани;
- короткий опис;
- фраза про передоплату;
- trusted demo image reuse у різних містах;
- inconsistent cluster;
- strong low-risk deal.

Усе явно synthetic, без чужих фотографій.

## Background execution

Domain services мають Celery wrappers:

- `capture_listing_snapshot`;
- `refresh_listing_market_assessment`;
- `refresh_listing_risk_assessment`;
- `refresh_stale_listing_analyses`;
- `backfill_listing_snapshots`.

Вимоги: idempotency, bounded batches, timeout, retry/backoff, correlation ID, failure status і stale-lock protection. Stage 9 не залежить від Celery Beat для локальної коректності.

## Settings

```dotenv
MARKET_ANALYSIS_PROVIDER=local
MARKET_ANALYSIS_ENABLED=true
MARKET_MIN_COMPARABLES=8
MARKET_MAX_COMPARABLES=120
MARKET_FRESHNESS_DAYS=90
MARKET_RADIUS_KM=5
MARKET_AREA_TOLERANCE_PERCENT=25
MARKET_ASSESSMENT_TTL_SECONDS=21600
RISK_ANALYSIS_ENABLED=true
RISK_ASSESSMENT_TTL_SECONDS=21600
ANALYSIS_AUTO_REFRESH_ENABLED=true
ANALYSIS_TASK_QUEUE=analytics
```

## Rollout і rollback

1. schema migration;
2. baseline snapshot backfill;
3. bounded assessment build;
4. перевірка score/confidence distributions у demo/staging;
5. read-only UI;
6. auto-refresh;
7. Risk Score не використовується для auto-hide.

Stage 9 additive. Його UI та auto-refresh можна вимкнути без поломки listings, search, map, duplicates або AI fallback.

## Тестування

Unit:

- snapshot/hash/idempotency;
- real-only price changes;
- exclusion target/same cluster;
- bounded cascade;
- median/Q1/Q3/outlier/confidence;
- кожна межа RiskSignal;
- score cap, stable order і safe wording;
- provider disabled/unavailable.

Integration:

- ingestion → snapshot → history → assessments;
- persistence/idempotency;
- approved-source filtering;
- endpoint permissions/throttle;
- baseline backfill;
- cluster-aware sample.

Frontend:

- ready/insufficient/stale/failed states;
- price badge;
- risk disclaimer;
- chart text alternative;
- compare integration;
- null-safe mobile rendering.

Повні gates: Ruff, mypy, migrations, pytest/coverage, pip-audit, ESLint, TypeScript, Vitest, production build, npm audit, Docker builds і Gitleaks.

## Критерії приймання

Stage 9 готовий лише коли:

1. snapshots і price events ідемпотентні;
2. market sample cluster-deduplicated;
3. statistics мають sample size та confidence;
4. insufficient data позначається явно;
5. кожен нарахований Risk Score бал має evidence;
6. немає категоричного звинувачення автора;
7. feed/detail/compare працюють без assessment;
8. demo scenarios перевіряються тестами;
9. AI використовує лише validated Stage 9 context;
10. Stage 9 можна вимкнути без поломки core;
11. стандартний CI зелений;
12. документація та deployment оновлені.

## Послідовність реалізації

1. regression tests і models;
2. snapshot/price history;
3. comparables/market statistics;
4. Risk Score;
5. API/permissions;
6. demo/backfill;
7. Mini App UI;
8. Stage 8 integration;
9. docs/config;
10. CI і deployment verification.
