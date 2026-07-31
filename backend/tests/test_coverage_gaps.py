"""Endpoints the audit found with real behaviour and zero test coverage.

Four surfaced from an endpoint x test cross-reference: a state-changing restore whose *revoke*
counterpart was tested but whose *restore* was not, an OTP resend, and two role-scoped reads.
None had ever been exercised.
"""

import datetime

import pytest
from rest_framework.test import APIClient

from accounts.models import PasswordResetToken
from accounts.password import start_reset
from batches.models import Batch, BatchState, Course
from content.models import VideoAccessRevocation
from core.roles import Role
from engagement.models import GoogleReview
from enrollments.models import Enrollment

from .helpers import client_for, user

# --------------------------- RestoreVideoAccessView (state-changing) ---------------------------


@pytest.fixture
def revoked(db):
    course = Course.objects.create(code="CG", name="CG")
    batch = Batch.objects.create(
        code="CG-1",
        name="CG-1",
        course=course,
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=30),
        state=BatchState.ACTIVE,
    )
    student = user("cg_stu", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="cg_stu")
    VideoAccessRevocation.objects.create(student=student, batch=batch)
    return {"batch": batch, "student": student}


@pytest.mark.django_db
def test_mis_restores_revoked_video_access(revoked):
    """The counterpart of the tested revoke: it deletes the revocation rows, re-granting play."""
    mis = user("cg_mis", Role.MIS)
    assert VideoAccessRevocation.objects.filter(student=revoked["student"]).exists()

    resp = client_for(mis).post(
        "/api/v1/video-access/restore/",
        {"student_id": str(revoked["student"].id), "batch_id": str(revoked["batch"].id)},
        format="json",
    )

    assert resp.status_code == 200
    assert not VideoAccessRevocation.objects.filter(student=revoked["student"]).exists()


@pytest.mark.django_db
def test_restore_for_an_unknown_student_is_a_clean_404(revoked):
    mis = user("cg_mis2", Role.MIS)
    import uuid

    resp = client_for(mis).post(
        "/api/v1/video-access/restore/",
        {"student_id": str(uuid.uuid4())},
        format="json",
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_a_student_cannot_restore_their_own_access(revoked):
    """Matrix-gated on REVOKE_VIDEO_INDIVIDUAL — a student self-restoring would defeat the point."""
    resp = client_for(revoked["student"]).post(
        "/api/v1/video-access/restore/",
        {"student_id": str(revoked["student"].id)},
        format="json",
    )
    assert resp.status_code == 403
    assert VideoAccessRevocation.objects.filter(student=revoked["student"]).exists()


# --------------------------- ForgotPasswordResendView ---------------------------


@pytest.mark.django_db
def test_password_reset_resend_issues_a_fresh_code(db):
    """The view reads the flow token from the request body (not the session), so the test
    must send it there — otherwise it passes vacuously through the invalid-session branch,
    which is precisely the kind of coverage gap this suite exists to close."""
    student = user("cg_reset", Role.STUDENT, email="cg@example.com", phone="9876511111")
    token = start_reset(student)[0]

    resp = APIClient().post("/api/v1/auth/password/resend/", {"token": token.token}, format="json")

    assert resp.status_code == 200, resp.content
    token.refresh_from_db()
    assert token.resend_count == 1  # a fresh code really was issued


@pytest.mark.django_db
def test_resend_without_a_reset_session_is_refused_not_crashed(db):
    resp = APIClient().post("/api/v1/auth/password/resend/", {}, format="json")
    assert resp.status_code == 400  # no session -> "invalid or expired", never a 500


@pytest.mark.django_db
def test_resend_stops_at_the_cap(db):
    """The resend cap is the abuse control; it must actually bind."""
    from accounts.password import MAX_RESENDS, resend

    student = user("cg_cap", Role.STUDENT, email="cap@example.com")
    token = start_reset(student)[0]
    PasswordResetToken.objects.filter(pk=token.pk).update(resend_count=MAX_RESENDS)
    token.refresh_from_db()

    _, reason = resend(token)
    assert reason  # refused
    assert "limit" in reason.lower()


# --------------------------- ForumBatchesView (role-scoped read) ---------------------------


@pytest.fixture
def forum_world(db):
    course = Course.objects.create(code="FB", name="FB")
    batch = Batch.objects.create(
        code="FB-1",
        name="FB-1",
        course=course,
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=30),
        state=BatchState.ACTIVE,
    )
    faculty = user("fb_fac", Role.FACULTY)
    batch.faculty.add(faculty)
    student = user("fb_stu", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="fb_stu")
    return {"batch": batch, "faculty": faculty, "student": student}


@pytest.mark.django_db
def test_forum_batches_are_scoped_to_the_caller(forum_world):
    URL = "/api/v1/forum/batches/"

    # Tech Support sees every batch.
    ts = user("fb_ts", Role.TECH_SUPPORT)
    assert len(client_for(ts).get(URL).json()) >= 1

    # A student sees only their enrolled batch.
    body = client_for(forum_world["student"]).get(URL).json()
    assert [b["code"] for b in body] == ["FB-1"]

    # Faculty sees the batch they teach.
    fac_body = client_for(forum_world["faculty"]).get(URL).json()
    assert "FB-1" in [b["code"] for b in fac_body]

    # MIS has no forum under the procedure -> empty, not an error.
    mis = user("fb_mis", Role.MIS)
    assert client_for(mis).get(URL).json() == []


# --------------------------- GoogleReviewReportView (role-scoped read) ---------------------------


@pytest.mark.django_db
def test_google_review_report_counts_and_scopes(db):
    student = user("gr_stu", Role.STUDENT)
    GoogleReview.objects.create(student=student, status=GoogleReview.Status.SUBMITTED)
    other = user("gr_stu2", Role.STUDENT)
    GoogleReview.objects.create(student=other, status=GoogleReview.Status.PENDING)

    mis = user("gr_mis", Role.MIS)
    resp = client_for(mis).get("/api/v1/engagement/reports/google-review/")

    assert resp.status_code == 200
    body = resp.json()
    assert body["submitted"] == 1
    assert body["pending"] == 1


@pytest.mark.django_db
def test_google_review_report_is_role_gated(db):
    """ReportRoles = Admin/MIS. A student must not read the whole cohort's review status."""
    student = user("gr_stu3", Role.STUDENT)
    assert client_for(student).get("/api/v1/engagement/reports/google-review/").status_code == 403
