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


def exception_handler(exc: Exception, context: dict) -> Response | None:
    response = _drf_exception_handler(exc, context)
    if response is None:
        return None  # Not a DRF-recognised exception — let Django handle it as normal.
    data = response.data
    if isinstance(data, dict) and set(data.keys()) <= {"detail"}:
        return response  # Already the uniform shape.
    response.data = {"detail": _first_message(data), "errors": data}
    return response
