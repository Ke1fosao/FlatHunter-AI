# Архітектура FlatHunter AI — Stage 6

## Принципи

- modular monorepo без змішування frontend, bot і domain logic;
- Telegram є каналом ідентифікації, backend залишається джерелом істини;
- core matching і demo geocoding не залежать від AI;
- зовнішні джерела та providers підключаються через legal-first adapters;
- персональні профілі, стани й геодані завжди user-scoped;
- external geocoding є opt-in і вимкнений за замовчуванням;
- PostGIS використовується для spatial filtering і distances;
- polling і webhook ніколи не працюють одночасно.

## Компоненти

```mermaid
flowchart TB
    subgraph Client
      Telegram[Telegram Client]
      Browser[Browser Preview]
      MiniApp[Next.js Mini App]
      Leaflet[Leaflet Map]
    end

    subgraph Edge
      Gateway[Nginx Gateway]
      Tiles[Configured Tile Provider]
    end

    subgraph Application
      API[Django + DRF + GeoDjango]
      Bot[aiogram]
      Worker[Celery Worker]
      Beat[Celery Beat]
      Geocoder[Geocoding Provider Adapter]
      Matcher[Deterministic Match Engine]
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
    MiniApp --> Leaflet
    Leaflet --> Tiles
    Bot --> API
    API --> Matcher
    API --> Geocoder
    API --> PostgreSQL
    API --> Redis
    API --> Worker
    Beat --> Worker
    Worker --> PostgreSQL
    Worker --> Redis
```

## Backend modules

- `apps.core`: logging, request IDs, normalized errors і health checks;
- `apps.accounts`: users, roles, Telegram profiles й authentication;
- `apps.telegram_bot`: aiogram runtime, onboarding, webhook і polling;
- `apps.searches`: search profiles, notification preferences й important places;
- `apps.listings`: raw/normalized listings і personal listing state;
- `apps.matching`: deterministic Match Score;
- `apps.geodata`: geometry helpers, providers, spatial services, GeoJSON і map API.

## Geodata flow

```mermaid
flowchart LR
    SOURCE[Approved Source Adapter] --> RAW[(RawListing)]
    RAW --> NORMALIZE[Normalize]
    NORMALIZE --> DECIMAL[latitude / longitude]
    DECIMAL --> POINT[GeoDjango Point SRID 4326]
    POINT --> POSTGIS[(PostGIS geography)]
    PROFILE[(Owned SearchProfile)] --> PLACE[(ImportantPlace Point)]
    POSTGIS --> BBOX[BBox query]
    POSTGIS --> DISTANCE[Distance annotation]
    BBOX --> GEOJSON[GeoJSON FeatureCollection]
    DISTANCE --> CONTEXT[Map context]
    PROFILE --> MATCH[Deterministic Match]
    MATCH --> GEOJSON
    GEOJSON --> MAP[Leaflet markers]
    PLACE --> MAP
```

## Coordinate model

`Listing` і `ImportantPlace` зберігають:

- decimal `latitude` / `longitude` для import/API compatibility;
- geography `location` для spatial operations.

Model helpers підтримують синхронізацію. Geometry використовує SRID 4326, а point order — longitude, latitude.

## Geocoding boundary

`apps.geodata.contracts.GeocodingProvider` визначає provider interface.

- `DemoGeocodingProvider`: deterministic, offline, CI-safe;
- `NominatimGeocodingProvider`: opt-in, fixed endpoint, UA-only, timeout, cache, rate slot.

API не приймає provider URL і не розкриває credentials.

## Authentication boundary

```mermaid
sequenceDiagram
    participant T as Telegram Client
    participant M as Mini App
    participant A as Django API
    participant R as Redis
    participant D as PostgreSQL

    T->>M: Open Mini App + raw initData
    M->>A: POST /api/v1/auth/telegram/
    A->>A: Verify HMAC and auth_date
    A->>R: Replay protection
    A->>D: Find or create user
    A-->>M: HttpOnly session + CSRF
    M->>A: GET /api/v1/map/listings/?profile_id=...
    A->>D: Verify profile ownership + spatial query
    A-->>M: User-scoped GeoJSON
```

## Deployment modes

### Local development

- PostgreSQL/PostGIS is required from Stage 6;
- Redis may be local or containerized;
- Next.js dev server;
- Django development server;
- Telegram long polling;
- demo geocoder by default.

### Production-oriented

- Nginx gateway and HTTPS termination;
- Gunicorn Django service with GIS runtime libraries;
- Next.js standalone runtime;
- PostgreSQL/PostGIS;
- Redis;
- Celery worker;
- exactly one Celery Beat;
- Telegram webhook;
- provider policies, attribution, backups and monitoring configured before external integrations.
