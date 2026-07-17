# Stage 9 — Risk і market analysis

Stage 9 додає автономний детермінований аналітичний шар поверх нормалізованих оголошень FlatHunter AI. Він працює без платних API, не залежить від LLM і не називає автора оголошення шахраєм.

## Що реалізовано

- канонічні версійовані `ListingSnapshot` без повного raw payload;
- `ListingPriceHistory`, яка створюється лише при реальній зміні нормалізованої ціни;
- кластерно-дедуплікований добір схожих активних оголошень;
- медіана, inclusive Q1/Q3, медіанна ціна за м², відхилення та confidence;
- явний `insufficient_data` без фальшивої точності;
- пояснюваний Risk Score 0–100 із evidence для кожного нарахованого бала;
- нейтральні рівні: `low`, `review`, `elevated`, `insufficient_data`;
- API історії ціни, ринкової оцінки, Risk Score та ручного refresh;
- compact analytics summary у listing payload;
- accessible Mini App UI: chips, детальний блок, графік і текстова альтернатива;
- deterministic demo revisions для демонстрації зниження та підвищення ціни;
- validated Stage 9 context для Stage 8 AI без повторного обчислення score.

## Безпечні принципи

Market sample містить лише:

- активні оголошення;
- enabled sources;
- legal status `approved` або `approved_demo`;
- нормалізовану позитивну ціну в UAH;
- достатньо свіжі оголошення;
- максимум одну primary-публікацію на duplicate cluster;
- не target listing і не інші публікації тієї самої квартири.

Risk Score:

- є допоміжною оцінкою, а не юридичним висновком;
- ніколи автоматично не приховує і не блокує оголошення;
- не робить категоричних висновків про людину;
- зберігає стабільний код, вагу, severity, evidence, label і recommendation кожного сигналу;
- використовує market deviation лише при достатньому confidence;
- показує safety advice незалежно від рівня.

## Моделі

### `ListingSnapshot`

Allowlisted стан Listing із SHA-256 `content_hash`. Unique constraint `(listing, content_hash)` робить capture ідемпотентним.

### `ListingPriceHistory`

Подія містить попередню та нову ціну, абсолютну й відсоткову зміну, direction і timestamps. Baseline snapshot не створює вигадану подію.

### `ListingMarketAssessment`

Містить status, provider/version, input hash, median/Q1/Q3, price/m², deviation, comparable count, confidence, IDs аналогів, selection summary, validity і safe error code.

### `ListingRiskAssessment`

Містить status, score, level, explainable signals, protective signals, summary, safety advice, algorithm version, validity і safe error code.

## Добір аналогів

Bounded cascade:

1. місто + район + кімнати + площа ±20%;
2. місто + георадіус + кімнати + площа в налаштованій tolerance;
3. місто + кімнати + тип будинку або ремонт;
4. місто + кімнати як fallback.

Налаштування:

```dotenv
MARKET_ANALYSIS_PROVIDER=local
MARKET_ANALYSIS_ENABLED=true
MARKET_MIN_COMPARABLES=8
MARKET_MAX_COMPARABLES=120
MARKET_FRESHNESS_DAYS=90
MARKET_RADIUS_KM=5
MARKET_AREA_TOLERANCE_PERCENT=25
MARKET_ASSESSMENT_TTL_SECONDS=21600
```

## Market statistics

Система рахує:

- median price;
- inclusive Q1/Q3;
- IQR і кількість extreme observations;
- median price per m² для rows із відомою площею;
- target price per m²;
- deviation target від median;
- confidence score та label.

Confidence враховує sample size, район, повноту площі, свіжість і dispersion. Якщо sample менший за `MARKET_MIN_COMPARABLES`, числові market estimates повертаються як `null`.

## Risk signals

Поточний deterministic engine перевіряє:

- суттєво нижчу за ринок ціну при medium/high confidence;
- різкі та численні зміни ціни;
- trusted image hash reuse у різних містах;
- hard conflicts duplicate engine;
- source conflicts усередині cluster;
- згадку іншого міста в описі;
- надто короткий або тиснучий шаблонний текст;
- фрази про передоплату до перегляду;
- зовнішні посилання;
- відсутність кількох базових полів;
- ознаку прихованої комісії.

Protective signals можуть зменшити score, але не видаляють high-severity evidence.

## API

```text
GET  /api/v1/listings/{listing_id}/price-history/
GET  /api/v1/listings/{listing_id}/market-analysis/
GET  /api/v1/listings/{listing_id}/risk-analysis/
POST /api/v1/listings/{listing_id}/analysis/refresh/
```

Усі endpoints потребують authenticated session і доступні лише для активного оголошення з дозволеного source.

Refresh підтримує:

```http
Idempotency-Key: user-generated-stable-key
Content-Type: application/json

{"force": false}
```

Frontend не може передати provider, weights або алгоритм оцінювання.

## Перший запуск

```bash
docker compose up --build -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_demo_listings --revision 1
docker compose exec backend python manage.py backfill_listing_snapshots
docker compose exec backend python manage.py refresh_listing_analyses
```

## Демонстрація історії ціни

Спочатку виконайте baseline revision 1, потім:

```bash
docker compose exec backend python manage.py seed_demo_listings --revision 2
docker compose exec backend python manage.py refresh_listing_analyses --force
```

Revision 2 детерміновано змінює частину цін, додаючи справжні snapshot differences та price events. Дані залишаються synthetic і не описують реальних людей або квартири.

Dry-run і bounded batches:

```bash
docker compose exec backend python manage.py backfill_listing_snapshots --dry-run
docker compose exec backend python manage.py refresh_listing_analyses --dry-run
docker compose exec backend python manage.py refresh_listing_analyses --limit 50 --batch-size 25
```

## Background execution

Celery wrappers:

- `apps.analysis.tasks.capture_listing_snapshot_task`;
- `apps.analysis.tasks.refresh_listing_market_task`;
- `apps.analysis.tasks.refresh_listing_risk_task`;
- `apps.analysis.tasks.refresh_listing_analysis_task`;
- `apps.analysis.tasks.refresh_stale_listing_analyses_task`.

Stage 9 correctness не залежить від Celery Beat. Auto-refresh вимкнений за замовчуванням:

```dotenv
ANALYSIS_AUTO_REFRESH_ENABLED=false
ANALYSIS_TASK_QUEUE=analytics
ANALYSIS_BATCH_SIZE=100
```

У production спочатку виконайте backfill та перевірте distributions, потім увімкніть auto-refresh.

## Stage 8 integration

AI отримує тільки persisted, validated і non-stale поля Stage 9. Він не рахує market або Risk Score самостійно. `insufficient_data`, stale, failed та disabled results залишаються unknown.

## Rollback

Stage 9 additive. Для миттєвого safe rollback:

```dotenv
MARKET_ANALYSIS_ENABLED=false
RISK_ANALYSIS_ENABLED=false
ANALYSIS_AUTO_REFRESH_ENABLED=false
```

Listings, search profiles, matching, map, duplicates і deterministic AI fallback продовжують працювати. Міграції не потрібно відкочувати для вимкнення UI/API обчислень.

## Перевірки

```bash
cd backend
ruff format --check apps config tests manage.py
ruff check apps config tests manage.py
mypy apps config
python manage.py migrate --noinput
python manage.py makemigrations --check --dry-run
pytest --cov=apps --cov-report=term-missing
uvx pip-audit --strict -r requirements.lock

cd ../miniapp
npm run lint
npm run typecheck
npm test
npm run build
npm audit --audit-level=high
```

Stage 9 не вважається завершеним без зелених Docker builds і Gitleaks secret scan.
