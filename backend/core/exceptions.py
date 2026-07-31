"""Uniform API error envelope.

DRF's default handler returns different shapes depending on the exception: a plain
``{"detail": "..."}`` for APIException/PermissionDenied/NotFound/Throttled, but
``{"field": ["msg", ...]}`` (or a bare ``["msg", ...]`` for non-field errors) for a raised
serializer ``ValidationError``. Client code had to guess between shapes (see the
now-simplified fallback chain in ``frontend/src/lib/api.ts``).

This handler keeps the original field-level detail under ``"errors"`` (so a form can still
highlight the right input) and guarantees a single human-readable ``"detail"`` string at
the top level of every DRF-handled error response. Responses a view builds and returns
directly (not raised) — e.g. the enrolment import's per-row validation report — never pass
through here and are unaffected.
"""

from __future__ import annotations

from typing import Any

from django.db.models import ProtectedError, RestrictedError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as _drf_exception_handler

_FALLBACK = "Something went wrong — please try again."


def _first_message(data: Any) -> str:
    """Flatten DRF's error data (str | list | dict, arbitrarily nested) to one sentence."""
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        return _first_message(data[0]) if data else _FALLBACK
    if isinstance(data, dict):
        if not data:
            return _FALLBACK
        for key in ("detail", "non_field_errors"):
            if key in data:
                return _first_message(data[key])
        return _first_message(next(iter(data.values())))
    return _FALLBACK


def _protected_delete_response(exc: ProtectedError | RestrictedError) -> Response:
    """Turn a database-refused delete into a 409 in the standard envelope.

    ``on_delete=PROTECT`` raises during the delete, and ``ProtectedError`` is not a DRF
    exception — so without this it escapes as an unhandled 500 and the caller is told the
    server broke rather than that the operation is not allowed. ``CourseViewSet.destroy`` is
    the live example: it has no ``perform_destroy`` guard, so deleting a course whose batches
    issued certificates hits the protection directly.

    The blocking model is named because that is what makes the message actionable ("this has
    issued certificates"); the individual rows are not, since they are other people's records.
    """
    # ProtectedError exposes `protected_objects`, RestrictedError `restricted_objects`; either
    # may be absent or empty, so coerce before iterating rather than relying on `or` chaining.
    raw = getattr(exc, "protected_objects", None) or getattr(exc, "restricted_objects", None)
    protected = tuple(raw) if raw else ()
    names = sorted({str(type(obj)._meta.verbose_name_plural).lower() for obj in protected})
    what = ", ".join(names) if names else "other records"
    return Response(
        {
            "detail": (
                f"This cannot be deleted because {what} depend on it. "
                "Those are kept as academic records — archive it instead of deleting."
            ),
            "errors": {"protected_by": names},
        },
        status=status.HTTP_409_CONFLICT,
    )


def exception_handler(exc: Exception, context: dict) -> Response | None:
    # Before DRF's handler: it does not recognise these and would return None, leaving a 500.
    #
    # Deliberately narrow. ProtectedError and RestrictedError are both IntegrityError
    # subclasses, but catching IntegrityError wholesale would turn genuine bugs — a NOT NULL
    # violation, a unique constraint tripped by broken logic — into a tidy 409 and hide them
    # from Sentry. Only a refused *delete* is a legitimate conflict.
    if isinstance(exc, (ProtectedError, RestrictedError)):
        return _protected_delete_response(exc)

    response = _drf_exception_handler(exc, context)
    if response is None:
        return None  # Not a DRF-recognised exception — let Django handle it as normal.
    data = response.data
    if isinstance(data, dict) and set(data.keys()) <= {"detail"}:
        return response  # Already the uniform shape.
    response.data = {"detail": _first_message(data), "errors": data}
    return response
