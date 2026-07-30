"""Two trust-boundary defects found while verifying the CI pipeline locally.

Both are cases where attacker-controlled text was passed to a consumer that interprets it:
``X-Forwarded-For`` to the throttle/audit layer, and export cells to a spreadsheet.
"""

import csv
import io

import pytest
from django.test import RequestFactory

from core.roles import Role
from core.utils import get_client_ip
from reports.views import _sanitize_cell

from .helpers import client_for, user

# --------------------------- X-Forwarded-For trust ---------------------------


def _req(xff=None, remote="203.0.113.9"):
    request = RequestFactory().get("/")
    request.META["REMOTE_ADDR"] = remote
    if xff is not None:
        request.META["HTTP_X_FORWARDED_FOR"] = xff
    return request


def test_forwarded_header_is_ignored_when_no_proxy_is_configured(settings):
    """Default posture. Django exposed directly means the header is pure client input."""
    settings.TRUSTED_PROXY_COUNT = 0
    assert get_client_ip(_req(xff="1.2.3.4")) == "203.0.113.9"


def test_client_cannot_forge_its_ip_behind_one_proxy(settings):
    """The regression test for the bug.

    nginx uses $proxy_add_x_forwarded_for, which *appends* the real peer address to whatever
    the client sent. The old implementation took the leftmost entry — i.e. the part the
    client wrote — so any caller could choose the IP recorded against their login attempts
    and audit rows. The rightmost entry is the one our own proxy added.
    """
    settings.TRUSTED_PROXY_COUNT = 1
    forged = _req(xff="1.2.3.4, 198.51.100.7", remote="10.0.0.1")
    assert get_client_ip(forged) == "198.51.100.7"


def test_a_longer_forged_header_cannot_push_past_our_proxies(settings):
    """Padding the header must not shift the trusted entry out of reach."""
    settings.TRUSTED_PROXY_COUNT = 1
    padded = _req(xff="9.9.9.9, 8.8.8.8, 7.7.7.7, 198.51.100.7")
    assert get_client_ip(padded) == "198.51.100.7"


def test_two_proxies_reads_one_hop_further_in(settings):
    """With a CDN in front of nginx, the CDN's view of the client is one entry further left."""
    settings.TRUSTED_PROXY_COUNT = 2
    assert get_client_ip(_req(xff="1.2.3.4, 198.51.100.7, 172.16.0.1")) == "198.51.100.7"


def test_falls_back_to_remote_addr_when_the_header_is_absent_or_empty(settings):
    settings.TRUSTED_PROXY_COUNT = 1
    assert get_client_ip(_req()) == "203.0.113.9"
    assert get_client_ip(_req(xff="   ")) == "203.0.113.9"
    assert get_client_ip(_req(xff=" , , ")) == "203.0.113.9"


def test_num_proxies_is_wired_into_drf_so_throttles_agree(settings):
    """DRF keys IP throttles on its own get_ident(), which has the identical flaw: with
    NUM_PROXIES unset it returns the whole header, so a client varying X-Forwarded-For gets a
    fresh throttle bucket per request. The two must be configured from the same number."""
    from django.conf import settings as dj

    assert dj.REST_FRAMEWORK["NUM_PROXIES"] == dj.TRUSTED_PROXY_COUNT


# --------------------------- CSV formula injection ---------------------------


@pytest.mark.parametrize(
    "hostile",
    [
        "=1+1",
        "=cmd|'/c calc'!A1",
        '=HYPERLINK("http://evil.example","Click")',
        "+1+1",
        "-1+1",
        "@SUM(A1)",
        "\t=1+1",
        "\r=1+1",
    ],
)
def test_formula_like_cells_are_neutralised(hostile):
    out = _sanitize_cell(hostile)
    assert out.startswith("'")
    assert not out.startswith(("=", "+", "-", "@", "\t", "\r"))


@pytest.mark.parametrize("ordinary", ["Asha Nair", "S101", "9876500001", "a@b.com", ""])
def test_ordinary_cells_are_untouched(ordinary):
    assert _sanitize_cell(ordinary) == ordinary


def test_non_string_cells_pass_through():
    for value in (42, 3.5, None, True):
        assert _sanitize_cell(value) is value


@pytest.mark.django_db
def test_student_export_neutralises_a_hostile_name(db):
    """End-to-end: a student whose name is a formula must not produce a live formula cell.

    Names arrive via MIS CSV import, so this is reachable by whoever supplies the roster —
    and the reader opening the export is staff.
    """
    import datetime

    from batches.models import Batch, BatchState, Course
    from enrollments.models import Enrollment

    course = Course.objects.create(code="FSX", name="FSX")
    batch = Batch.objects.create(
        code="BX",
        name="BX",
        course=course,
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=30),
        state=BatchState.ACTIVE,
    )
    student = user("Sx1", Role.STUDENT, full_name="=cmd|'/c calc'!A1")
    Enrollment.objects.create(student=student, batch=batch, registration_number="Sx1")
    admin = user("admx", Role.ADMIN)

    resp = client_for(admin).get(f"/api/v1/reports/students/?batch={batch.id}")
    assert resp.status_code == 200

    body = resp.content.decode()
    rows = list(csv.reader(io.StringIO(body)))
    name_cells = [c for row in rows for c in row if "calc" in c]
    assert name_cells, "the hostile name should still appear — sanitising must not drop data"
    for cell in name_cells:
        assert cell.startswith("'")
