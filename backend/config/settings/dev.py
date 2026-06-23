"""Development settings."""

from .base import *  # noqa: F401,F403

DEBUG = True

# Cookies served over http during local development.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
