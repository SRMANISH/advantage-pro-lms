"""Phase-5 hardening: the import surface, the delivery seam, TOTP lifecycle, token hygiene."""

import datetime
import io
import logging
import zipfile

import pyotp
import pytest
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from accounts import totp as totp_service
from accounts.device import handle_device_login
from accounts.models import DeviceBinding, DeviceChangeRequest, PasswordResetToken
from content.delivery import _reject_unsafe_key
from core.crypto import decrypt_secret, encrypt_secret
from core.roles import Role
from enrollments.importer import parse_rows

from .helpers import client_for, user

# --------------------------- import surface ---------------------------


def _xlsx(sheets=1, payload=b""):
    """A minimal workbook-shaped zip. Enough for the container check, which never opens it."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        for i in range(sheets):
            zf.writestr(f"xl/worksheets/sheet{i + 1}.xml", "<worksheet/>")
        if payload:
            zf.writestr("xl/sharedStrings.xml", payload)
    return buf.getvalue()


def test_an_oversized_upload_is_refused_before_parsing(settings):
    settings.MAX_IMPORT_UPLOAD_MB = 1
    big = SimpleUploadedFile("students.csv", b"x" * (2 * 1024 * 1024), content_type="text/csv")
    with pytest.raises(ValueError, match="too large"):
        parse_rows(big)


def test_a_zip_bomb_is_refused_without_being_decompressed(settings):
    """The regression test. A few hundred KB of zeros expands to ~50 MB, and openpyxl reads
    sharedStrings.xml in full before a single row is validated."""
    settings.MAX_IMPORT_DECOMPRESSED_MB = 5
    upload = SimpleUploadedFile("bomb.xlsx", _xlsx(payload=b"\0" * (50 * 1024 * 1024)))

    with pytest.raises(ValueError, match="expands to far more data"):
        parse_rows(upload)


def test_an_absurd_compression_ratio_is_refused_even_under_the_size_cap(settings):
    """Either limit alone is evadable: stay under the total and still be disproportionate."""
    settings.MAX_IMPORT_DECOMPRESSED_MB = 500  # deliberately not the binding limit
    settings.MAX_IMPORT_COMPRESSION_RATIO = 50
    upload = SimpleUploadedFile("ratio.xlsx", _xlsx(payload=b"\0" * (20 * 1024 * 1024)))

    with pytest.raises(ValueError, match="compressed far beyond"):
        parse_rows(upload)


def test_a_workbook_with_too_many_sheets_is_refused(settings):
    settings.MAX_IMPORT_SHEETS = 3
    with pytest.raises(ValueError, match="sheets"):
        parse_rows(SimpleUploadedFile("many.xlsx", _xlsx(sheets=10)))


def test_a_corrupt_xlsx_gives_a_readable_error_not_a_crash():
    with pytest.raises(ValueError, match="not a readable workbook"):
        parse_rows(SimpleUploadedFile("bad.xlsx", b"not a zip at all"))


def test_an_ordinary_csv_still_imports(settings):
    settings.MAX_IMPORT_UPLOAD_MB = 10
    csv = b"registration_number,name,email,phone,batch,course,faculty\nS1,A,a@b.com,9,B,C,f\n"
    rows = parse_rows(SimpleUploadedFile("ok.csv", csv, content_type="text/csv"))
    assert len(rows) == 1 and rows[0]["registration_number"] == "S1"


# --------------------------- delivery seam ---------------------------


@pytest.mark.parametrize(
    "hostile",
    [
        "../../etc/passwd",
        "videos/../../../etc/passwd",
        "/etc/passwd",
        "C:/Windows/System32/config",
        "videos\\..\\..\\evil.mp4",
        "videos/%2e%2e/evil.mp4",
        "videos/evil.mp4\r\nX-Injected: 1",
        "videos/evil\x00.mp4",
        "",
    ],
)
def test_the_delivery_seam_refuses_a_dangerous_key(hostile):
    """In production the key goes into X-Accel-Redirect and nginx resolves it, so
    LocalStorageAdapter's containment check never runs — the deployment with a real
    filesystem to walk is the one without the guard."""
    with pytest.raises(SuspiciousFileOperation):
        _reject_unsafe_key(hostile)


@pytest.mark.parametrize(
    "ok", ["videos/3f2a-uuid.mp4", "forum/abc.pdf", "tests/resources/x.xlsx", "a.png"]
)
def test_ordinary_keys_pass(ok):
    _reject_unsafe_key(ok)  # must not raise


# --------------------------- TOTP lifecycle ---------------------------


@pytest.fixture
def enrolled(db):
    staff = user("hard_fac", Role.FACULTY)
    return staff, totp_service.get_or_create_pending(staff)


@pytest.mark.django_db
def test_a_code_cannot_be_replayed_within_its_window(enrolled):
    """A code stays valid for its whole step, widened to ~90s by the drift window. Seen once
    — a screenshot, a shoulder, a proxy log — it worked again until now."""
    _, device = enrolled
    code = pyotp.TOTP(device.secret).now()

    assert totp_service.verify(device, code) is True
    assert totp_service.verify(device, code) is False  # same code, same window


@pytest.mark.django_db
def test_a_replay_does_not_count_as_a_failed_attempt(enrolled):
    """Otherwise a double-submitted form would burn attempts toward the lockout."""
    _, device = enrolled
    code = pyotp.TOTP(device.secret).now()
    totp_service.verify(device, code)
    totp_service.verify(device, code)

    device.refresh_from_db()
    assert device.failed_attempts == 0


@pytest.mark.django_db
def test_super_admin_can_lift_a_lockout(enrolled):
    """Before this the cap had no way out: five mistypes and the account was locked out of
    its own second factor permanently, recoverable only from a database shell."""
    staff, device = enrolled
    for _ in range(totp_service.MAX_ATTEMPTS):
        totp_service.verify(device, "000000")
    device.refresh_from_db()
    assert totp_service.attempts_exhausted(device)

    sa = user("hard_sa", Role.SUPER_ADMIN)
    resp = client_for(sa).post(f"/api/v1/auth/totp/{staff.id}/reset/")

    assert resp.status_code == 200
    secret_before = device.secret
    device.refresh_from_db()
    assert device.failed_attempts == 0
    assert device.secret == secret_before  # the user keeps their authenticator entry


@pytest.mark.django_db
def test_the_reset_keeps_replay_protection_in_place(enrolled):
    """Clearing last_used_step would re-open a window the reset has no business touching."""
    staff, device = enrolled
    code = pyotp.TOTP(device.secret).now()
    totp_service.verify(device, code)
    device.refresh_from_db()
    spent = device.last_used_step

    sa = user("hard_sa2", Role.SUPER_ADMIN)
    client_for(sa).post(f"/api/v1/auth/totp/{staff.id}/reset/")

    device.refresh_from_db()
    assert device.last_used_step == spent
    assert totp_service.verify(device, code) is False  # still cannot be replayed


@pytest.mark.django_db
def test_only_super_admin_can_lift_a_lockout(enrolled):
    staff, _ = enrolled
    for role in (Role.MIS, Role.ADMIN, Role.FACULTY):
        other = user(f"hard_{role}", role)
        assert client_for(other).post(f"/api/v1/auth/totp/{staff.id}/reset/").status_code == 403


# --------------------------- token + device lifecycle ---------------------------


@pytest.mark.django_db
def test_changing_the_password_burns_an_outstanding_reset_token():
    """A link requested before the change stayed live for its whole window, so it could undo
    the change afterwards — and changing your password is exactly when you want that shut."""
    student = user("hard_stu", Role.STUDENT, password="Str0ng!passLMS")
    token = PasswordResetToken.objects.create(
        user=student,
        token="tok-hard-1",
        expires_at=timezone.now() + datetime.timedelta(hours=1),
    )

    resp = client_for(student).post(
        "/api/v1/auth/password/change/",
        {"old_password": "Str0ng!passLMS", "new_password": "An0ther!passLMS"},
        format="json",
    )
    assert resp.status_code == 200

    token.refresh_from_db()
    assert token.used is True


@pytest.mark.django_db
def test_a_graduate_on_a_new_device_gets_a_route_back_not_a_dead_end():
    """Post-course login exists so a graduate can enter their Certificate ID, and phones get
    lost. The old rule refused unconditionally — no request, no recourse."""
    student = user("hard_grad", Role.STUDENT)
    DeviceBinding.objects.create(user=student, device_id="old-phone")
    user("hard_ts", Role.TECH_SUPPORT)

    allowed, message = handle_device_login(student, "new-phone", course_ended=True)

    assert allowed is False
    assert "tech support" in message.lower()
    assert DeviceChangeRequest.objects.filter(
        user=student, new_device_id="new-phone", status=DeviceChangeRequest.Status.PENDING
    ).exists()


@pytest.mark.django_db
def test_a_graduates_bound_device_still_works():
    """The change is gated; ordinary post-course sign-in is not."""
    student = user("hard_grad2", Role.STUDENT)
    DeviceBinding.objects.create(user=student, device_id="same-phone")

    allowed, _ = handle_device_login(student, "same-phone", course_ended=True)
    assert allowed is True


# --------------------------- crypto rotation + session ---------------------------


@pytest.mark.django_db
def test_an_undecryptable_secret_warns_instead_of_failing_silently(caplog, settings):
    """Silence here means every channel stops sending with nothing in the logs to say why."""
    token = encrypt_secret("provider-key")
    settings.SECRET_KEY = "a-completely-different-key-after-rotation-000000"

    with caplog.at_level(logging.WARNING, logger="lms.crypto"):
        assert decrypt_secret(token) == ""  # still safe

    assert "SECRET_KEY" in caplog.text


def test_the_session_lifetime_is_shorter_than_djangos_default(settings):
    """The incident-response intent in ActiveSessionAuthentication is undermined by a
    fortnight-long cookie."""
    assert settings.SESSION_COOKIE_AGE < 14 * 24 * 60 * 60
    assert settings.SESSION_COOKIE_AGE == 12 * 60 * 60
