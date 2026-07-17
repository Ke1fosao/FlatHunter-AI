from __future__ import annotations

import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    TELEGRAM_AUTH_MAX_AGE=(int, 300),
    GEOCODING_EXTERNAL_ENABLED=(bool, False),
    GEOCODING_TIMEOUT_SECONDS=(int, 8),
    GEOCODING_CACHE_SECONDS=(int, 2592000),
    DUPLICATE_AUTO_QUEUE_ENABLED=(bool, False),
)
env_file = BASE_DIR.parent / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="unsafe-development-key-change-me")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "backend"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "apps.core",
    "apps.accounts",
    "apps.ai_analysis",
    "apps.searches",
    "apps.listings",
    "apps.matching",
    "apps.geodata",
    "apps.duplicates",
    "apps.telegram_bot",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgresql://flathunter:flathunter@postgres:5432/flathunter",
    )
}
DATABASES["default"]["ENGINE"] = "django.contrib.gis.db.backends.postgis"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "uk"
TIME_ZONE = "Europe/Kyiv"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.exceptions.standard_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "FlatHunter AI API",
    "DESCRIPTION": "Backend API for the FlatHunter AI Telegram Mini App.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=not DEBUG)
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=not DEBUG)
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=not DEBUG)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0 if DEBUG else 31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
REFERRER_POLICY = "same-origin"

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True

REDIS_URL = env("REDIS_URL", default="redis://redis:6379/0")

TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_BOT_USERNAME = env("TELEGRAM_BOT_USERNAME", default="")
TELEGRAM_WEBHOOK_URL = env("TELEGRAM_WEBHOOK_URL", default="")
TELEGRAM_WEBHOOK_SECRET = env("TELEGRAM_WEBHOOK_SECRET", default="")
TELEGRAM_MINI_APP_URL = env("TELEGRAM_MINI_APP_URL", default="http://localhost:3000")
TELEGRAM_AUTH_MAX_AGE = env.int("TELEGRAM_AUTH_MAX_AGE", default=300)
TELEGRAM_AUTH_REPLAY_TTL = env.int("TELEGRAM_AUTH_REPLAY_TTL", default=600)
TELEGRAM_LONG_POLLING = env.bool("TELEGRAM_LONG_POLLING", default=DEBUG)
TELEGRAM_ADMIN_IDS = env.list("TELEGRAM_ADMIN_IDS", default=[])

AI_PROVIDER = env("AI_PROVIDER", default="local_rules")
AI_API_KEY = env("AI_API_KEY", default="")
AI_MODEL = env("AI_MODEL", default="local-rules-v1")
AI_ENABLED = env.bool("AI_ENABLED", default=False)
AI_DAILY_BUDGET = env.float("AI_DAILY_BUDGET", default=0)
AI_TIMEOUT_SECONDS = env.int("AI_TIMEOUT_SECONDS", default=15)

GEOCODING_PROVIDER = env("GEOCODING_PROVIDER", default="demo")
GEOCODING_API_KEY = env("GEOCODING_API_KEY", default="")
GEOCODING_EXTERNAL_ENABLED = env.bool("GEOCODING_EXTERNAL_ENABLED", default=False)
GEOCODING_TIMEOUT_SECONDS = env.int("GEOCODING_TIMEOUT_SECONDS", default=8)
GEOCODING_CACHE_SECONDS = env.int("GEOCODING_CACHE_SECONDS", default=2592000)
GEOCODING_USER_AGENT = env(
    "GEOCODING_USER_AGENT",
    default="FlatHunterAI/0.1 (demo; configure a real contact before production)",
)
GDAL_LIBRARY_PATH = env("GDAL_LIBRARY_PATH", default=None)
_GDAL_DLL_DIRECTORY = None
_add_dll_directory = getattr(os, "add_dll_directory", None)
if GDAL_LIBRARY_PATH and _add_dll_directory is not None:
    _GDAL_DLL_DIRECTORY = _add_dll_directory(str(Path(GDAL_LIBRARY_PATH).parent))
MAP_TILES_URL = env("MAP_TILES_URL", default="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png")
MAP_ATTRIBUTION = env("MAP_ATTRIBUTION", default="© OpenStreetMap contributors")

DUPLICATE_AUTO_MERGE_THRESHOLD = env.float("DUPLICATE_AUTO_MERGE_THRESHOLD", default=92.0)
DUPLICATE_REVIEW_THRESHOLD = env.float("DUPLICATE_REVIEW_THRESHOLD", default=78.0)
DUPLICATE_SIMHASH_BLOCK_DISTANCE = env.int("DUPLICATE_SIMHASH_BLOCK_DISTANCE", default=12)
DUPLICATE_BLOCK_LIMIT = env.int("DUPLICATE_BLOCK_LIMIT", default=500)
DUPLICATE_AUTO_QUEUE_ENABLED = env.bool("DUPLICATE_AUTO_QUEUE_ENABLED", default=False)
DUPLICATE_TASK_QUEUE = env("DUPLICATE_TASK_QUEUE", default="duplicates")

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL or "redis://redis:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=REDIS_URL or "redis://redis:6379/2")
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 270
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

SOURCE_DEMO_ENABLED = env.bool("SOURCE_DEMO_ENABLED", default=True)
SOURCE_OLX_ENABLED = env.bool("SOURCE_OLX_ENABLED", default=False)
SOURCE_LUN_ENABLED = env.bool("SOURCE_LUN_ENABLED", default=False)
SOURCE_RIELTOR_ENABLED = env.bool("SOURCE_RIELTOR_ENABLED", default=False)
SOURCE_OTODIM_ENABLED = env.bool("SOURCE_OTODIM_ENABLED", default=False)

FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")
BACKEND_URL = env("BACKEND_URL", default="http://localhost:8000")
LOG_LEVEL = env("LOG_LEVEL", default="INFO")
SENTRY_DSN = env("SENTRY_DSN", default="")
