"""Request-id middleware: generated/forwarded, echoed back, and log-correlatable."""

import logging

import pytest
from rest_framework.test import APIClient

from core.request_id import HEADER_NAME, RequestIDLogFilter, get_request_id


@pytest.mark.django_db
def test_response_carries_a_generated_request_id():
    resp = APIClient().get("/api/v1/health/")
    assert resp.status_code == 200
    assert resp[HEADER_NAME]  # non-empty
    assert len(resp[HEADER_NAME]) == 32  # uuid4().hex


@pytest.mark.django_db
def test_incoming_request_id_is_forwarded_not_replaced():
    resp = APIClient().get("/api/v1/health/", HTTP_X_REQUEST_ID="from-the-lb-123")
    assert resp[HEADER_NAME] == "from-the-lb-123"


def test_get_request_id_defaults_outside_a_request():
    assert get_request_id() == "-"


def test_log_filter_attaches_the_current_id():
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "msg", None, None)
    RequestIDLogFilter().filter(record)
    assert record.request_id == "-"  # no active request in this unit test
