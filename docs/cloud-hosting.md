# Cloud Hosting

This project is prepared for a free-demo deployment split across:

- Vercel: `miniapp` Next.js Telegram Mini App and same-origin API gateway.
- Render: `backend` Django API and Telegram webhook.
- Supabase: PostgreSQL with PostGIS.

## 1. Supabase

Create or restore a Supabase project, then run:

```sql
create extension if not exists postgis;
```

Use the Supabase session pooler connection string as Render's `DATABASE_URL`. The value must not be committed.

For this project, the expected format is:

```text
postgresql://postgres.rmwadgvxlpurmsxrzseu:<YOUR-PASSWORD>@aws-1-eu-central-1.pooler.supabase.com:5432/postgres
```

Copy it from Supabase Dashboard -> Connect -> Direct -> Session pooler, then replace `<YOUR-PASSWORD>` with the database password.

This repository uses a dedicated PostgreSQL schema for the app:

```env
DATABASE_SCHEMA=flathunter
```

That keeps FlatHunter's Django migration history separate from any old tables in the default `public` schema.

## 2. Render Backend

Use the root-level `render.yaml` Blueprint. It creates one free Docker web service from `backend/Dockerfile`.

Set these secret/env values in Render:

```env
DJANGO_SECRET_KEY=<strong random secret>
DATABASE_URL=postgresql://postgres.rmwadgvxlpurmsxrzseu:<YOUR-PASSWORD>@aws-1-eu-central-1.pooler.supabase.com:5432/postgres
DATABASE_SCHEMA=flathunter
CORS_ALLOWED_ORIGINS=https://<your-vercel-app>.vercel.app
CSRF_TRUSTED_ORIGINS=https://<your-vercel-app>.vercel.app
TELEGRAM_BOT_TOKEN=<bot token>
TELEGRAM_BOT_USERNAME=<bot username without @>
TELEGRAM_WEBHOOK_SECRET=<strong random secret>
TELEGRAM_WEBHOOK_URL=https://<your-render-service>.onrender.com/api/v1/telegram/webhook/
TELEGRAM_MINI_APP_URL=https://<your-vercel-app>.vercel.app
```

Keep `SECURE_SSL_REDIRECT=false` on Render. Render terminates HTTPS before the container, and enabling Django's redirect can make internal Render health checks receive `301` instead of `200`.

The `render.yaml` Blueprint includes an `initialDeployHook` that runs these demo data commands once after the first successful deploy:

```bash
python manage.py seed_demo_listings
python manage.py geocode_demo_data
python manage.py build_listing_fingerprints
python manage.py detect_listing_duplicates
python manage.py rebuild_listing_clusters
```

Render Free web services do not provide normal shell access. For later re-seeding, run these commands from a trusted local machine with production `DATABASE_URL` set, or temporarily use a paid Render feature that supports one-off commands.

## 3. Telegram Webhook

Register the webhook after the Render URL is live:

```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -d "url=$TELEGRAM_WEBHOOK_URL" \
  -d "secret_token=$TELEGRAM_WEBHOOK_SECRET"
```

The free Render web service can spin down when idle, so the first Telegram message after inactivity can be delayed.

## 4. Vercel Mini App

Create a Vercel project with root directory `miniapp`.

Set:

```env
BACKEND_API_URL=https://<your-render-service>.onrender.com/api/v1
NEXT_PUBLIC_MAP_TILES_URL=https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png
NEXT_PUBLIC_MAP_ATTRIBUTION=© OpenStreetMap contributors
```

Do not point browser code directly at Render. The browser always calls the same-origin `/api/v1/...` route on Vercel. The Next.js catch-all route forwards that request to `BACKEND_API_URL`, rewrites backend cookies onto the Vercel origin, preserves the Django session, and forwards the CSRF token returned by Telegram authentication.

`BACKEND_API_URL` is server-only and must include `/api/v1`. `NEXT_PUBLIC_API_URL` is not required in production; when present, keep it as `/api/v1` for local compatibility.

After Vercel deploys, update Render's `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, and `TELEGRAM_MINI_APP_URL` to the final Vercel URL. These remain useful for direct operational tools and Django origin validation, even though normal Mini App traffic uses the Vercel gateway.

## Verification

Render backend:

```bash
curl --fail https://<your-render-service>.onrender.com/health/live/
curl --fail https://<your-render-service>.onrender.com/health/ready/
curl --fail https://<your-render-service>.onrender.com/api/v1/health/
```

Deployed Vercel gateway:

```bash
curl --fail https://<your-vercel-app>.vercel.app/api/v1/health/
```

The Vercel response should match the backend health JSON. Telegram authentication must then create a first-party session cookie on the Vercel domain, and subsequent protected API calls must return authenticated data instead of `401` or CSRF failures.
