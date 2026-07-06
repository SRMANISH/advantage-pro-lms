"""In-app notifications: delivery, scoping, read state, and event triggers."""

import datetime

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from accounts.models import User, UserStatus
from batches.models import Batch, Course
from core.roles import Role
from notifications.models import Notification
from notifications.services import notify

LIST_URL = "/api/v1/notifications/"


def user(username, role, **extra):
    return User.objects.create_user(
        username=username, password="x", role=role, status=UserStatus.ACTIVE, **extra
    )


def client_for(u):
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.mark.django_db
def test_notify_creates_in_app_and_lists_only_own():
    a = user("a", Role.ADMIN)
    b = user("b", Role.ADMIN)
    notify(a, "hello", "for A")
    notify(b, "hello", "for B")

    resp = client_for(a).get(LIST_URL)
    assert resp.status_code == 200
    messages = [n["message"] for n in resp.json()["results"]]
    assert messages == ["for A"]


@pytest.mark.django_db
def test_mark_read_and_unread_count():
    a = user("a", Role.ADMIN)
    notify(a, "k", "one")
    notify(a, "k", "two")
    c = client_for(a)

    assert c.get(f"{LIST_URL}unread-count/").json()["count"] == 2
    note_id = c.get(LIST_URL).json()["results"][0]["id"]
    assert c.post(f"{LIST_URL}{note_id}/read/").status_code == 200
    assert c.get(f"{LIST_URL}unread-count/").json()["count"] == 1
    assert c.post(f"{LIST_URL}mark-all-read/").status_code == 200
    assert c.get(f"{LIST_URL}unread-count/").json()["count"] == 0


@pytest.mark.django_db
def test_import_notifies_admins():
    admin = user("adm", Role.ADMIN, email="adm@example.com")
    fac = user("prof", Role.FACULTY)
    course = Course.objects.create(code="FS", name="Full Stack")
    Batch.objects.create(
        code="FS-1",
        name="B",
        course=course,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 4, 1),
    )
    csv = SimpleUploadedFile(
        "s.csv",
        b"registration_number,name,email,phone,batch,course,faculty\n"
        b"S1,Asha,asha@example.com,9876543210,FS-1,FS,prof\n",
        content_type="text/csv",
    )
    resp = client_for(admin).post("/api/v1/enrollments/import/", {"file": csv}, format="multipart")
    assert resp.status_code == 201
    assert Notification.objects.filter(recipient=admin, kind="students_imported").exists()
    assert fac.notifications.count() == 0
