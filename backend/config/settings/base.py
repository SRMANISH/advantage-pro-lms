"""Base settings shared by all environments.

Security-sensitive and environment-specific values are read from the environment
(12-factor). See dev.py / prod.py for per-environment overrides.
"""

from pathlib import Path
from urllib.parse import urlparse

import environ

# backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-insecure-secret-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "django_q",
    # Local
    "core",
    "accounts",
    "audit",
    "batches",
    "enrollments",
    "content",
    "notifications",
    "assessments",
    "attendance",
    "escalations",
    "forum",
    "liveclasses",
    "certification",
    "engagement",
    "feedback",
]

MIDDLEWARE = [
    "core.request_id.RequestIDMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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
            ],
        },
    },
]

# PostgreSQL via DATABASE_URL in real environments; SQLite fallback for quick local dev.
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'dev.sqlite3'}",
    )
}

AUTH_USER_MODEL = "accounts.User"

# Argon2id first — strongest available password hashing.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("THROTTLE_ANON", default="60/min"),
        "user": env("THROTTLE_USER", default="240/min"),
        "login": env("THROTTLE_LOGIN", default="10/min"),
        # Code-verification + credential-change endpoints (setup/reset OTP, TOTP).
        "otp": env("THROTTLE_OTP", default="20/min"),
        # Student -> management feedback fans out a WhatsApp per Super Admin; keep it low.
        "feedback": env("THROTTLE_FEEDBACK", default="5/hour"),
    },
    "EXCEPTION_HANDLER": "core.exceptions.exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Advantage Pro LMS API",
    "DESCRIPTION": "Internal batch-centric LMS for Advantage Pro.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # Several serializers expose a field literally named "status" backed by different
    # choice sets; give each enum a distinct component name so the schema doesn't collide.
    "ENUM_NAME_OVERRIDES": {
        "LiveClassStatusEnum": "liveclasses.models.LiveClassStatus.choices",
        "ThreadStatusEnum": "forum.models.ThreadStatus.choices",
    },
}

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# Static & media
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Business rules (config-driven; editable per the dynamic principle).
FORUM_RESPONSE_WINDOW_HOURS = env.int("FORUM_RESPONSE_WINDOW_HOURS", default=3)
LIVE_CLASS_DURATION_MINUTES = env.int("LIVE_CLASS_DURATION_MINUTES", default=120)
# Attendance denominator: when False, Saturdays/Sundays don't count as expected days (and
# weekend logins don't count as present days), so weekend gaps don't drag percentages down.
ATTENDANCE_COUNT_WEEKENDS = env.bool("ATTENDANCE_COUNT_WEEKENDS", default=True)
# Student import: hard cap per file so one upload can't stall a worker (split larger lists).
MAX_IMPORT_ROWS = env.int("MAX_IMPORT_ROWS", default=5000)

# Upload limits. DATA_UPLOAD_MAX_MEMORY_SIZE caps non-file POST bodies; the per-file hard
# caps (video/document) are enforced by core.uploads.validate_upload.
DATA_UPLOAD_MAX_MEMORY_SIZE = env.int("DATA_UPLOAD_MAX_MEMORY_SIZE", default=10 * 1024 * 1024)
FILE_UPLOAD_MAX_MEMORY_SIZE = env.int("FILE_UPLOAD_MAX_MEMORY_SIZE", default=10 * 1024 * 1024)
MAX_VIDEO_UPLOAD_MB = env.int("MAX_VIDEO_UPLOAD_MB", default=512)
MAX_DOCUMENT_UPLOAD_MB = env.int("MAX_DOCUMENT_UPLOAD_MB", default=25)

# Media delivery: when set (e.g. "/protected"), gated video/material endpoints return an
# nginx ``X-Accel-Redirect`` instead of streaming through the app worker. Configure a
# matching internal nginx location: `location /protected/ { internal; alias <MEDIA_ROOT>/; }`.
# Empty in dev/CI, so the app streams the bytes itself.
MEDIA_XACCEL_PREFIX = env("MEDIA_XACCEL_PREFIX", default="")

# Data retention (days) for purge_old_data — activity data only, never academic records.
RETENTION_AUDIT_DAYS = env.int("RETENTION_AUDIT_DAYS", default=365)
RETENTION_NOTIFICATION_DAYS = env.int("RETENTION_NOTIFICATION_DAYS", default=180)

# Frontend (SPA) integration
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:5173")
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:5173"])
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["http://localhost:5173"])

# Secure session/CSRF cookie defaults (relaxed in dev.py).
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# Cache — Redis when REDIS_URL is set (shared across gunicorn workers, so DRF throttling
# and rate limits are consistent), else in-process LocMemCache for local dev/tests.
REDIS_URL = env("REDIS_URL", default="")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# Structured logging to stdout (the platform/process manager collects it). Every line
# carries the request id (core.request_id) so one request's logs can be grepped together.
LOG_LEVEL = env("LOG_LEVEL", default="INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {"()": "core.request_id.RequestIDLogFilter"},
    },
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} [{request_id}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "filters": ["request_id"],
        },
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}

# Error monitoring — initialised in prod.py only when a DSN is configured.
SENTRY_DSN = env("SENTRY_DSN", default="")
SENTRY_TRACES_SAMPLE_RATE = env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0)

# Ports & adapters — swap dotted paths via env for Hostinger / 3rd-party services.
LMS_ADAPTERS = {
    "storage": env("LMS_STORAGE_ADAPTER", default="core.adapters.local.LocalStorageAdapter"),
    "email": env("LMS_EMAIL_ADAPTER", default="core.adapters.local.ConsoleEmailAdapter"),
    "sms": env("LMS_SMS_ADAPTER", default="core.adapters.local.ConsoleSmsAdapter"),
    "whatsapp": env("LMS_WHATSAPP_ADAPTER", default="core.adapters.local.ConsoleWhatsAppAdapter"),
    "scheduler": env("LMS_SCHEDULER_ADAPTER", default="core.adapters.local.ImmediateScheduler"),
}

# --- Provider credentials (only read by the adapter you actually configure above) ---
# SMTP (core.adapters.smtp.SmtpEmailAdapter) — Django's own EMAIL_* settings.
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@advantagepro.example")

# MSG91 (core.adapters.msg91.Msg91SmsAdapter)
MSG91_AUTH_KEY = env("MSG91_AUTH_KEY", default="")
MSG91_SENDER_ID = env("MSG91_SENDER_ID", default="")
MSG91_ROUTE = env("MSG91_ROUTE", default="4")
MSG91_COUNTRY = env("MSG91_COUNTRY", default="91")

# Meta WhatsApp Cloud API (core.adapters.whatsapp_cloud.WhatsAppCloudAdapter)
WHATSAPP_ACCESS_TOKEN = env("WHATSAPP_ACCESS_TOKEN", default="")
WHATSAPP_PHONE_NUMBER_ID = env("WHATSAPP_PHONE_NUMBER_ID", default="")
WHATSAPP_TEMPLATE_NAME = env("WHATSAPP_TEMPLATE_NAME", default="")
WHATSAPP_TEMPLATE_LANG = env("WHATSAPP_TEMPLATE_LANG", default="en")

# Background queue (django-q2). Dev/CI (no REDIS_URL): tasks execute inline/synchronously
# so tests stay deterministic without a worker. Prod (REDIS_URL set): true async via a
# `python manage.py qcluster` worker process against Redis.
Q_CLUSTER = {
    "name": "AdvantagePro",
    "workers": env.int("Q_CLUSTER_WORKERS", default=2),
    "retry": 90,
    "timeout": 60,
    "queue_limit": 50,
    "bulk": 10,
    "orm": "default",
    "sync": REDIS_URL == "",
}
if REDIS_URL:
    _redis_bits = urlparse(REDIS_URL)
    Q_CLUSTER["redis"] = {
        "host": _redis_bits.hostname or "localhost",
        "port": _redis_bits.port or 6379,
        "db": int((_redis_bits.path or "/0").lstrip("/") or 0),
        "password": _redis_bits.password,
    }
