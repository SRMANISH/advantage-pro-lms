"""Phase 2: mandatory schedule, primary/soft faculty, occupied-faculty conflict,
faculty skills profile surfaced at assignment."""

import datetime

import pytest

from accounts.models import FacultyProfile
from batches.models import Batch, BatchState, Course
from batches.scheduling import faculty_schedule_conflicts
from core.roles import Role

from .helpers import client_for, user


@pytest.fixture
def base(db):
    course = Course.objects.create(code="FS", name="Full Stack")
    return {
        "course": course,
        "admin": user("ad", Role.ADMIN),
        "fac1": user("fac1", Role.FACULTY),
        "fac2": user("fac2", Role.FACULTY),
    }


def make_batch(course, code, days, start, end, **extra):
    return Batch.objects.create(
        code=code,
        name=code,
        course=course,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 12, 1),
        class_days=days,
        class_start_time=start,
        class_end_time=end,
        **extra,
    )


# ---------- conflict detection service ----------


@pytest.mark.django_db
def test_conflict_when_day_and_time_overlap(base):
    b1 = make_batch(base["course"], "A", ["mon", "wed"], "18:00", "20:00")
    b1.faculty.add(base["fac1"])
    # Same Monday, overlapping 19:00-21:00.
    clashes = faculty_schedule_conflicts(
        base["fac1"], ["mon"], datetime.time(19, 0), datetime.time(21, 0)
    )
    assert clashes == ["A"]


@pytest.mark.django_db
def test_no_conflict_when_days_differ(base):
    b1 = make_batch(base["course"], "A", ["mon"], "18:00", "20:00")
    b1.faculty.add(base["fac1"])
    assert (
        faculty_schedule_conflicts(
            base["fac1"], ["tue"], datetime.time(18, 0), datetime.time(20, 0)
        )
        == []
    )


@pytest.mark.django_db
def test_no_conflict_when_times_do_not_overlap(base):
    b1 = make_batch(base["course"], "A", ["mon"], "18:00", "20:00")
    b1.faculty.add(base["fac1"])
    assert (
        faculty_schedule_conflicts(
            base["fac1"], ["mon"], datetime.time(20, 0), datetime.time(22, 0)
        )
        == []
    )


@pytest.mark.django_db
def test_completed_batch_never_conflicts(base):
    b1 = make_batch(base["course"], "A", ["mon"], "18:00", "20:00", state=BatchState.COMPLETED)
    b1.faculty.add(base["fac1"])
    assert (
        faculty_schedule_conflicts(
            base["fac1"], ["mon"], datetime.time(18, 0), datetime.time(20, 0)
        )
        == []
    )


# ---------- assign-faculty endpoint: primary + soft + conflict ----------


@pytest.mark.django_db
def test_assign_sets_primary_and_soft_faculty(base):
    batch = make_batch(base["course"], "B", ["tue"], "10:00", "12:00")
    resp = client_for(base["admin"]).post(
        f"/api/v1/batches/{batch.id}/assign-faculty/",
        {"primary_faculty": str(base["fac1"].id), "faculty_ids": [str(base["fac2"].id)]},
        format="json",
    )
    assert resp.status_code == 200
    batch.refresh_from_db()
    assert batch.primary_faculty_id == base["fac1"].id
    # The M2M holds the full set (primary + soft).
    assert set(batch.faculty.values_list("id", flat=True)) == {base["fac1"].id, base["fac2"].id}


@pytest.mark.django_db
def test_assign_rejects_occupied_faculty(base):
    # fac1 already teaches an overlapping Monday-evening batch.
    busy = make_batch(base["course"], "BUSY", ["mon"], "18:00", "20:00")
    busy.faculty.add(base["fac1"])
    new = make_batch(base["course"], "NEW", ["mon"], "19:00", "21:00")

    resp = client_for(base["admin"]).post(
        f"/api/v1/batches/{new.id}/assign-faculty/",
        {"primary_faculty": str(base["fac1"].id)},
        format="json",
    )
    assert resp.status_code == 400
    assert "already occupied" in resp.json()["detail"]
    assert "BUSY" in resp.json()["detail"]


# ---------- faculty profile (skills/certs) + surfaced in the assign dropdown ----------


@pytest.mark.django_db
def test_faculty_edits_own_profile_and_it_shows_in_faculty_list(base):
    url = "/api/v1/auth/faculty/profile/"
    saved = client_for(base["fac1"]).put(
        url, {"skills": "React, Django", "certifications": "AWS SAA"}, format="json"
    )
    assert saved.status_code == 200
    assert FacultyProfile.objects.get(user=base["fac1"]).skills == "React, Django"

    # Non-faculty cannot use the endpoint.
    assert client_for(base["admin"]).get(url).status_code == 403

    # Skills ride along on the assign-dropdown list so the assigner can match skills.
    listing = client_for(base["admin"]).get("/api/v1/faculty/")
    fac1_row = next(r for r in listing.json() if r["id"] == str(base["fac1"].id))
    assert fac1_row["skills"] == "React, Django"
    assert fac1_row["certifications"] == "AWS SAA"
