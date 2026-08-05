"""Production settings — security hardened."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import (
    LMS_ADAPTERS,
    MIDDLEWARE,
    REDIS_URL,
    SECRET_KEY,
    SENTRY_DSN,
    SENTRY_TRACES_SAMPLE_RATE,
    env,
)
from .hosts import is_missing_or_dev_default, normalize_allowed_hosts

DEBUG = False

# Render's Blueprint `fromService.property: host` is the private-network hostname. Public
# traffic arrives with RENDER_EXTERNAL_HOSTNAME (for example, app.onrender.com), so include it
# automatically when this settings module runs on Render.
ALLOWED_HOSTS = normalize_allowed_hosts(
    env.list("DJANGO_ALLOWED_HOSTS", default=[]),
    env("RENDER_EXTERNAL_HOSTNAME", default=""),
)

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
if is_missing_or_dev_default(ALLOWED_HOSTS):
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must be set to your real host(s) in production."
    )
if not REDIS_URL:
    raise ImproperlyConfigured(
        "REDIS_URL must be set in production — it backs shared rate-limiting/caching "
        "across workers and the background task queue (qcluster). Without it, login "
        "throttling is per-process and notifications send synchronously in-request."
    )

# The notification adapters default to console stubs, which log instead of sending. Shipping
# that to production is silent, not loud: setup links, OTPs, absence chasers and the Super
# Admin feedback WhatsApp would all "succeed" while nobody receives anything. Fail fast
# unless the operator has explicitly opted out (e.g. a staging box with no provider yet).
_STUB_PREFIX = "core.adapters.local"
if not env.bool("LMS_ALLOW_CONSOLE_ADAPTERS", default=False):
    _stubbed = sorted(
        channel
        for channel in ("email", "sms", "whatsapp")
        if LMS_ADAPTERS.get(channel, "").startswith(_STUB_PREFIX)
    )
    if _stubbed:
        raise ImproperlyConfigured(
            "These notification channels are still using the local console stub in "
            f"production: {', '.join(_stubbed)}. Messages would be logged and silently "
            "dropped. Set the matching LMS_<CHANNEL>_ADAPTER env var to a real provider "
            "(see docs/DEPLOYMENT.md §6), or set LMS_ALLOW_CONSOLE_ADAPTERS=true to "
            "acknowledge this deliberately."
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
# "Lax" by default. A split deployment — frontend and API on different sites, as with
# Vercel + Render — needs "None" (with Secure, set above) or the browser withholds the session
# cookie on every cross-site request: login succeeds and every call after it is anonymous.
# Env-driven rather than hardcoded so that topology does not require a code change.
SESSION_COOKIE_SAMESITE = env("SESSION_COOKIE_SAMESITE", default="Lax")
CSRF_COOKIE_SAMESITE = env("CSRF_COOKIE_SAMESITE", default="Lax")
X_FRAME_OPTIONS = "DENY"

# Serve hashed static files efficiently behind the app server.
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
