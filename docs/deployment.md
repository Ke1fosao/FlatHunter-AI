# Deployment

## Local Docker deployment

```bash
cp .env.example .env
docker compose up --build -d
```

To include Telegram long polling:

```bash
docker compose --profile polling up --build -d
```

Only use polling for local development.

## Production prerequisites

- Linux host or managed container platform;
- public domain with HTTPS;
- PostgreSQL with PostGIS;
- Redis with persistence and restricted network access;
- unique high-entropy Django secret and webhook secret;
- Telegram bot token stored outside Git;
- one Celery Beat instance only;
- backup and monitoring configured before live data is enabled.

## Production compose

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.production.yml \
  up --build -d
```

The included Nginx config is a gateway baseline. TLS termination must be added through a reverse proxy, ingress or certificate automation such as Caddy/Traefik before enabling Telegram webhook mode.

## Register Telegram webhook

After HTTPS is active, call Telegram's `setWebhook` method from a secure operator environment with:

- URL: `https://YOUR_DOMAIN/api/v1/telegram/webhook/`;
- `secret_token`: the same value as `TELEGRAM_WEBHOOK_SECRET`;
- only required update types.

Never put the bot token in shell history on a shared machine. Prefer a small deployment script reading secrets from the environment.

## Migrations

The backend container runs migrations and static collection when `RUN_MIGRATIONS=true` and `COLLECT_STATIC=true`. Celery and bot containers do not repeat migrations.

Manual command:

```bash
docker compose exec backend python manage.py migrate
```

## Verification

```bash
curl --fail https://YOUR_DOMAIN/health/live/
curl --fail https://YOUR_DOMAIN/health/ready/
curl --fail https://YOUR_DOMAIN/health
```
