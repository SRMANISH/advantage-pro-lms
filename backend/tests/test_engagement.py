"""Engagement: LinkedIn follow, Google review, course-end next plan."""

import datetime

import pytest
from rest_framework.test import APIClient

from accounts.models import User, UserStatus
from batches.models import Batch, BatchState, Course
from core.roles import Role
from engagement.models import CourseNextPlan, GoogleReview, LinkedInFollow
from enrollments.models import Enrollment

ME = "/api/v1/engagement/me/"


def user(username, role):
    return User.objects.create_user(
        username=username, password="x", role=role, status=UserStatus.ACTIVE
    )


def client_for(u):
    c = APIClient()
    c.force_authenticate(user=u)
    return c


def completed_batch(code="DONE"):
    course = Course.objects.create(code=code, name="C")
    return Batch.objects.create(
        code=code,
        name="B",
        course=course,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 4, 1),
        state=BatchState.COMPLETED,
    )


@pytest.mark.django_db
def test_linkedin_popup_shows_until_confirmed():
    student = user("stu", Role.STUDENT)
    sc = client_for(student)
    assert sc.get(ME).json()["linkedin"]["show"] is True
    sc.post("/api/v1/engagement/linkedin/", {"action": "confirmed"}, format="json")
    assert sc.get(ME).json()["linkedin"]["show"] is False
    assert LinkedInFollow.objects.get(student=student).status == "confirmed"


@pytest.mark.django_db
def test_google_review_shows_after_course_completion():
    student = user("stu", Role.STUDENT)
    # No completed course yet -> no review prompt.
    assert client_for(student).get(ME).json()["google_review"]["show"] is False
    batch = completed_batch()
    Enrollment.objects.create(student=student, batch=batch, registration_number="stu")
    assert client_for(student).get(ME).json()["google_review"]["show"] is True
    client_for(student).post(
        "/api/v1/engagement/google-review/", {"action": "submitted"}, format="json"
    )
    assert GoogleReview.objects.get(student=student).status == "submitted"


@pytest.mark.django_db
def test_next_plan_submitted_and_visible_to_admin():
    # A student's username IS their Registration ID (set by the importer).
    student = user("REG1", Role.STUDENT)
    batch = completed_batch()
    Enrollment.objects.create(student=student, batch=batch, registration_number="REG1")
    admin = user("ad", Role.ADMIN)

    assert client_for(student).get(ME).json()["next_plan"]["show"] is True
    resp = client_for(student).post(
        "/api/v1/engagement/next-plan/",
        {
            "planning_another_course": True,
            "interested_course": "Data Science",
            "goal": "upskilling",
        },
        format="json",
    )
    assert resp.status_code == 200
    assert CourseNextPlan.objects.filter(student=student).exists()

    listing = client_for(admin).get("/api/v1/engagement/next-plans/")
    assert listing.status_code == 200
    assert any(r["registration_number"] == "REG1" for r in listing.json())


@pytest.mark.django_db
def test_engagement_reports_are_admin_mis_only():
    student = user("stu", Role.STUDENT)
    assert client_for(student).get("/api/v1/engagement/reports/linkedin/").status_code == 403
    assert (
        client_for(user("mis", Role.MIS)).get("/api/v1/engagement/reports/linkedin/").status_code
        == 200
    )


@pytest.mark.django_db
def test_reminders_run():
    from engagement.services import run_engagement_reminders

    student = user("stu", Role.STUDENT)
    batch = completed_batch()
    Enrollment.objects.create(student=student, batch=batch, registration_number="stu")
    result = run_engagement_reminders()
    assert result["linkedin"] == 1
    assert result["google_review"] == 1
    assert result["next_plan"] == 1
    assert student.notifications.filter(kind="linkedin_follow").exists()


@pytest.mark.django_db
def test_linkedin_report_filters_by_batch():
    """req 5: engagement reports can be scoped to one batch."""
    b1 = completed_batch("BA")
    b2 = completed_batch("BB")
    s1 = user("s1", Role.STUDENT)
    s2 = user("s2", Role.STUDENT)
    Enrollment.objects.create(student=s1, batch=b1, registration_number="s1")
    Enrollment.objects.create(student=s2, batch=b2, registration_number="s2")
    LinkedInFollow.objects.create(student=s1)
    LinkedInFollow.objects.create(student=s2)

    mis = client_for(user("mis", Role.MIS))
    all_rows = mis.get("/api/v1/engagement/reports/linkedin/").json()["students"]
    assert {r["registration_number"] for r in all_rows} == {"s1", "s2"}

    scoped = mis.get(f"/api/v1/engagement/reports/linkedin/?batch={b1.id}").json()["students"]
    assert {r["registration_number"] for r in scoped} == {"s1"}
