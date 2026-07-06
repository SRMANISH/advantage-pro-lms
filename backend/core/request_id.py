"""Per-request correlation id: generate/propagate X-Request-ID, expose it to logging.

Every log line emitted while handling a request gets the same id (via a logging
``Filter`` reading a contextvar), so grepping one id in production logs reconstructs
everything that request touched — auth, the view, notification fan-out, DB errors —
without threading an id through every function signature. A reverse proxy's own id
(if it sets the header) is honoured rather than overwritten, so a single id can be
traced from nginx through to the app.
"""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar

HEADER_NAME = "X-Request-ID"

_current: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return _current.get()


class RequestIDMiddleware:
    """Assigns (or forwards) a request id and echoes it back on the response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get(HEADER_NAME, "").strip() or uuid.uuid4().hex
        request.request_id = request_id
        token = _current.set(request_id)
        try:
            response = self.get_response(request)
        finally:
            _current.reset(token)
        response[HEADER_NAME] = request_id
        return response


class RequestIDLogFilter(logging.Filter):
    """Attaches the current request id to every log record (``"-"`` outside a request)."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True
