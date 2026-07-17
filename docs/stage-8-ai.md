# Stage 8 — безпечний AI-шар

Stage 8 додає AI-функції поверх детермінованого FlatHunter pipeline. AI не є джерелом істини для оголошень, не визначає дублікати, не змінює Match Score і не надсилає повідомлення власникам без явної дії користувача.

## Реалізовано

- абстракція `AIProvider` із єдиним контрактом `structured_completion`;
- локальний детермінований provider `local_rules`, який працює без платного ключа й зовнішньої мережі;
- суворі Pydantic-схеми з `extra="forbid"`, межами довжин, діапазоном confidence `0..1` та перевіркою цін;
- спільний deterministic fallback для AI-enabled, AI-disabled і provider-failure режимів;
- природномовний розбір пошуку з важливими точками та confidence;
- структуроване резюме оголошення;
- персональні питання власнику з урахуванням належного користувачу `SearchProfile`;
- порівняння 2–5 квартир із Match Score, комісією, відомою сумою першого платежу, тваринами, автономністю, паркуванням, перевагами, недоліками й невідомими параметрами;
- обережна рекомендація: квартира позначається рекомендованою лише при достатньому розриві Match Score;
- user-facing AI workspace у Mini App;
- `AIRequest` audit trail із sanitized input hash, результатом, latency, status, provider/model/prompt version і cache key;
- `AIPromptVersion` registry з checksum та активною версією;
- timeout, bounded retry, cache, circuit breaker і daily budget guard;
- fallback для validation errors, timeout, неочікуваних provider errors та неактивного provider;
- повне вимкнення AI без поломки пошуку, карти, фільтрів або сповіщень.

## API

```text
POST /api/v1/search-profiles/parse-natural-language/
POST /api/v1/ai/listings/{listing_id}/summary/
POST /api/v1/ai/listings/{listing_id}/owner-questions/
POST /api/v1/ai/listings/compare/
```

### Питання власнику

```json
{
  "search_profile_id": "optional-owned-profile-uuid"
}
```

`search_profile_id` є необов’язковим. Якщо його передано, backend перевіряє належність профілю поточному користувачу. Чужий або неіснуючий профіль повертає `404`.

### AI-порівняння

```json
{
  "listing_ids": ["uuid-1", "uuid-2"],
  "search_profile_id": "optional-owned-profile-uuid"
}
```

Вимоги:

- 2–5 унікальних listing IDs;
- тільки активні оголошення з дозволених джерел;
- профіль, якщо вказаний, повинен належати користувачу;
- без профілю система показує структуровані факти й trade-offs, але не робить персонального категоричного висновку.

## Meta response

Кожна AI-відповідь містить `meta`:

```json
{
  "feature": "listings.compare",
  "provider": "local_rules",
  "model": "local-rules-v1",
  "prompt_version": "listings-compare-v2",
  "status": "success",
  "latency_ms": 8,
  "attempts": 1,
  "cache_key": "sanitized-hash"
}
```

Можливі status:

- `success` — provider успішно повернув валідований результат;
- `cached` — повернуто раніше валідований результат;
- `fallback` — provider недоступний, перевищив timeout, відкритий circuit або вичерпано бюджет;
- `disabled` — AI повністю вимкнений, використано deterministic rules без AI audit row.

Для fallback також повертається безпечний `reason`, наприклад `provider_error`, `circuit_open`, `daily_budget_exhausted` або `provider_unavailable`.

## Налаштування

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

- `AI_DAILY_BUDGET=0` вимикає бюджетний ліміт.
- `AI_CACHE_SECONDS=0` вимикає result cache.
- `AI_MAX_RETRIES=0` виконує одну provider-спробу без retry.
- після заданої кількості послідовних failures circuit відкривається на cooldown period.

## Безпека й приватність

- raw user prompt не зберігається в `AIRequest.input_summary`;
- audit містить короткий SHA-256 hash і довжину input;
- AI output повторно проходить schema validation навіть після provider response;
- cache key формується з канонічного structured context, provider/model і prompt version;
- API не приймає provider URL або secret;
- користувач не може використати чужий SearchProfile;
- AI не вигадує адресу, контакти, точний routing time, Risk Score або суму застави;
- невідомі параметри позначаються як невідомі;
- готовий текст для власника лише копіюється користувачем і не надсилається автоматично.

## Відомі межі Stage 8

- у production build не підключено платний remote LLM provider; `local_rules` є стабільним demo/fallback provider;
- token і cost поля вже є в audit model, але реальні значення заповнюватиме remote provider adapter;
- Risk Score, ринкова оцінка та історія ціни належать наступному етапу, тому Stage 8 не створює фальшиві значення;
- точний travel time потребує окремого routing provider.

## Перевірки

Stage 8 regression tests перевіряють:

- deterministic parity при вимкненому AI;
- важливі точки у fallback режимі;
- timeout і audit fallback;
- неочікувані provider exceptions;
- bounded retries;
- circuit breaker;
- result cache;
- daily budget guard;
- schema validation;
- sanitized audit data;
- profile-aware questions and comparison;
- object ownership;
- 2–5 listing validation;
- Mini App AI workspace flows.
