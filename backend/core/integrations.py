"""Effective third-party connection config for the provider adapters (req 21).

Super Admin edits provider credentials from the Channels page; they're stored encrypted in
``notifications.IntegrationSetting``. Adapters read the *effective* config here — the
SA-saved DB value first, then the env/settings fallback — so a save takes effect without a
redeploy. Cached briefly (ciphertext only: the secret is decrypted per call and never
cached in plaintext) and invalidated on save. When no row exists (or before the first
migrate) the adapters fall back to their env settings, so the .env path keeps working.
"""

from __future__ import annotations

from django.core.cache import cache

_CACHE_KEY = "core.integration-config"
_TTL_SECONDS = 60

_EMPTY: dict = {"provider": "", "config": {}, "secret": ""}


def _rows() -> dict[str, dict]:
    """{channel: {provider, config, secret_ciphertext}}, cached; empty if unavailable."""
    data = cache.get(_CACHE_KEY)
    if data is None:
        try:
            from notifications.models import IntegrationSetting

            data = {
                s.channel: {
                    "provider": s.provider,
                    "config": s.config or {},
                    "secret": s.secret,  # ciphertext — decrypted lazily in integration_config
                }
                for s in IntegrationSetting.objects.all()
            }
        except Exception:  # pragma: no cover - table missing / DB unavailable
            return {}
        cache.set(_CACHE_KEY, data, _TTL_SECONDS)
    return data


def integration_config(channel: str) -> dict:
    """Effective ``{provider, config, secret}`` for a channel (secret decrypted); the
    SA-saved DB values take precedence, callers fall back to settings per key."""
    row = _rows().get(channel)
    if not row:
        return dict(_EMPTY)
    from core.crypto import decrypt_secret

    return {
        "provider": row.get("provider", ""),
        "config": row.get("config", {}),
        "secret": decrypt_secret(row.get("secret", "")),
    }


def invalidate_integration_config() -> None:
    """Drop the cached config — called after every Channels save."""
    cache.delete(_CACHE_KEY)
