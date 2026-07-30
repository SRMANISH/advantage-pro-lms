"""Shared test helpers.

Nearly every test module needs "make a user of role X" and "an API client authenticated as
them", and each had grown its own near-identical copy. The signatures here are a superset of
the variants that existed, so a module needing a custom password, status, or extra field
(e.g. ``full_name``, ``phone``) can still use them.
"""

from rest_framework.test import APIClient

from accounts.models import User, UserStatus


def user(username, role, password="x", status=UserStatus.ACTIVE, **extra):
    """Create an active user of the given role. Extra model fields pass straight through."""
    return User.objects.create_user(
        username=username, password=password, role=role, status=status, **extra
    )


def client_for(u):
    """An APIClient authenticated as ``u`` (bypasses login — permissions still apply)."""
    client = APIClient()
    client.force_authenticate(user=u)
    return client
