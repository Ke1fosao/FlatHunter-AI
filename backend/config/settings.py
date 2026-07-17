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
    "apps.searches",
    "apps.listings",
    "apps.duplicates",
    "apps.geodata",
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
    "apps.core.middleware.RequestIdMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

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
            ]
        },
    }
]

DATABASE_URL = env("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
DATABASE_URL = DATABASE_URL.replace(
    "aws-0-eu-central-1.pooler.supabase.com",
    "aws-1-eu-central-1.pooler.supabase.com",
)
DATABASES = {"default": env.db_url_config(DATABASE_URL)}
if DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql":
    DATABASES["default"]["ENGINE"] = "django.contrib.gis.db.backends.postgis"
DATABASE_SCHEMA = env("DATABASE_SCHEMA", default="")
if DATABASE_SCHEMA:
    if not DATABASE_SCHEMA.replace("_", "").isalnum():
        raise ValueError("DATABASE_SCHEMA must contain only letters, numbers, and underscores.")
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"]["options"] = f"-c search_path={DATABASE_SCHEMA},public"
DATABASES["default"]["CONN_MAX_AGE"] = 60
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

REDIS_URL = env("REDIS_URL", default="")
if REDIS_URL:
    CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL}
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "flathunter-local",
        }
    }

LANGUAGE_CODE = "uk"
TIME_ZONE = "Europe/Kyiv"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS", default=["http://localhost:3000", "http://localhost:8080"]
)
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS", default=["http://localhost:3000", "http://localhost:8080"]
)

SESSION_COOKIE_NAME = "flathunter_session"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "SAMEORIGIN"
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0 if DEBUG else 31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}
SPECTACULAR_SETTINGS = {
    "TITLE": "FlatHunter AI API",
    "DESCRIPTION": "Backend API for FlatHunter AI Telegram Mini App",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_BOT_USERNAME = env("TELEGRAM_BOT_USERNAME", default="")
TELEGRAM_MODE = env("TELEGRAM_MODE", default="polling")
TELEGRAM_WEBHOOK_URL = env("TELEGRAM_WEBHOOK_URL", default="")
TELEGRAM_WEBHOOK_SECRET = env("TELEGRAM_WEBHOOK_SECRET", default="")
TELEGRAM_MINI_APP_URL = env("TELEGRAM_MINI_APP_URL", default="")
TELEGRAM_AUTH_MAX_AGE = env.int("TELEGRAM_AUTH_MAX_AGE", default=300)
TELEGRAM_UPDATE_TTL = env.int("TELEGRAM_UPDATE_TTL", default=86400)

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
if GDAL_LIBRARY_PATH:
    _GDAL_DLL_DIRECTORY = os.add_dll_directory(str(Path(GDAL_LIBRARY_PATH).parent))
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
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_DEFAULT_QUEUE = "default"

LOG_LEVEL = env("LOG_LEVEL", default="INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "apps.core.logging.JsonFormatter"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "json"}},
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
}
