"""Production settings — security hardened."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import (
    ALLOWED_HOSTS,
    MIDDLEWARE,
    REDIS_URL,
    SECRET_KEY,
    SENTRY_DSN,
    SENTRY_TRACES_SAMPLE_RATE,
)

DEBUG = False

# Error monitoring (optional) — only active when a DSN is set and the SDK is installed.
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration()],
            traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
            send_default_pii=False,
        )
    except ImportError:
        pass

# Fail fast on insecure dev defaults — never boot prod with these.
if SECRET_KEY in ("", "dev-insecure-secret-change-me"):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set to a strong secret in production.")
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ["localhost", "127.0.0.1"]:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must be set to your real host(s) in production."
    )
if not REDIS_URL:
    raise ImproperlyConfigured(
        "REDIS_URL must be set in production — it backs shared rate-limiting/caching "
        "across workers and the background task queue (qcluster). Without it, login "
        "throttling is per-process and notifications send synchronously in-request."
    )

# HTTPS / transport security
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"

# Serve hashed static files efficiently behind the app server.
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
