"""Production settings — security hardened."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import ALLOWED_HOSTS, MIDDLEWARE, SECRET_KEY

DEBUG = False

# Fail fast on insecure dev defaults — never boot prod with these.
if SECRET_KEY in ("", "dev-insecure-secret-change-me"):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set to a strong secret in production.")
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ["localhost", "127.0.0.1"]:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must be set to your real host(s) in production."
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
