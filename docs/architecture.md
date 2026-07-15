# Архітектура FlatHunter AI — Stage 1

## Принципи

- модульний monorepo без змішування frontend, bot і domain logic;
- Telegram є каналом ідентифікації, але backend залишається джерелом істини;
- усі важкі операції в майбутньому передаються в Celery;
- зовнішні джерела підключаються через незалежні legal-first adapters;
- core-функції не повинні залежати від доступності AI;
- polling і webhook ніколи не працюють одночасно.

## Компоненти

```mermaid
flowchart TB
    subgraph Client
      Telegram[Telegram Client]
      Browser[Browser Preview]
      MiniApp[Next.js 16 Mini App]
    end

    subgraph Edge
      Gateway[Nginx Gateway]
    end

    subgraph Application
      API[Django 6 + DRF]
      Bot[aiogram 3]
      Worker[Celery Worker]
      Beat[Celery Beat]
    end

    subgraph Data
      PostgreSQL[(PostgreSQL + PostGIS)]
      Redis[(Redis Cache / Broker)]
    end

    Telegram --> Bot
    Telegram --> MiniApp
    Browser --> MiniApp
    MiniApp --> Gateway
    Gateway --> API
    Gateway --> MiniApp
    Bot --> API
    API --> PostgreSQL
    API --> Redis
    API --> Worker
    Beat --> Worker
    Worker --> PostgreSQL
    Worker --> Redis
```

## Telegram Mini App authentication

```mermaid
sequenceDiagram
    participant T as Telegram Client
    participant M as Mini App
    participant A as Django API
    participant R as Redis
    participant D as PostgreSQL

    T->>M: Open Mini App + raw initData
    M->>A: POST /api/v1/auth/telegram/ {initData}
    A->>A: Verify HMAC and auth_date
    A->>R: Reserve hash for replay protection
    A->>D: Find or create User + TelegramProfile
    A-->>M: HttpOnly session + CSRF token + safe user data
```

## Backend module boundaries

- `apps.core`: logging, request IDs, errors and health checks;
- `apps.accounts`: users, roles, Telegram profiles and authentication;
- `apps.telegram_bot`: aiogram runtime, `/start`, webhook and polling command;
- future domain apps are added independently under `backend/apps/`.

## Deployment modes

### Local

- Next.js dev server;
- Django development server;
- optional SQLite/in-memory cache;
- bot long polling.

### Docker / production-oriented

- Nginx gateway;
- Gunicorn Django service;
- Next.js standalone runtime;
- PostgreSQL/PostGIS;
- Redis;
- Celery worker;
- exactly one Celery Beat;
- Telegram webhook over HTTPS.
