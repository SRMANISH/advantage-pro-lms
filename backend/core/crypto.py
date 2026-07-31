"""Symmetric encryption for secrets stored at rest.

Used for third-party provider credentials (IntegrationSetting.secret) so a database dump
does not leak API keys. The Fernet key is derived from ``SECRET_KEY`` — rotating
``SECRET_KEY`` therefore invalidates stored ciphertexts (they decrypt to "" and must be
re-entered), which is the safe failure mode.
"""

from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

logger = logging.getLogger("lms.crypto")


def _fernet() -> Fernet:
    # 32-byte key from SECRET_KEY -> urlsafe base64, the format Fernet expects. Not cached
    # so tests overriding SECRET_KEY (override_settings) still work correctly.
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_secret(raw: str) -> str:
    """Encrypt a plaintext secret. Empty input stays empty (nothing to hide)."""
    if not raw:
        return ""
    return _fernet().encrypt(raw.encode()).decode()


def decrypt_secret(token: str) -> str:
    """Decrypt a stored ciphertext. Returns "" for empty input or an unreadable token
    (e.g. after a SECRET_KEY rotation) rather than raising."""
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        # Almost always one thing: SECRET_KEY was rotated, so every stored provider secret is
        # now undecryptable. Returning "" keeps the app up, but silently — the adapters then
        # behave as though no credentials were configured and every email, SMS and WhatsApp
        # stops being delivered with nothing in the logs to say why. Warn loudly instead; the
        # recovery is to re-enter each secret (docs/DEPLOYMENT.md).
        logger.warning(
            "Could not decrypt a stored integration secret — this normally means SECRET_KEY "
            "was rotated. Re-enter the provider secrets in Channels; until then that channel "
            "sends nothing."
        )
        return ""
