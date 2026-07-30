"""Suspend / reactivate and change-role staff endpoints (matrix-gated)."""

import pytest
from rest_framework.test import APIClient

from accounts.models import User, UserStatus
from core.roles import Role
from .helpers import client_for


def user(username, role, status=UserStatus.ACTIVE):
    return User.objects.create_user(username=username, password="x", role=role, status=status)


def _status_url(u):
    return f"/api/v1/auth/users/{u.id}/status/"


def _role_url(u):
    return f"/api/v1/auth/users/{u.id}/role/"


@pytest.mark.django_db
def test_admin_can_suspend_and_reactivate_student():
    admin = user("adm", Role.ADMIN)
    student = user("S1", Role.STUDENT)
    resp = client_for(admin).post(_status_url(student), {"suspend": True}, format="json")
    assert resp.status_code == 200
    student.refresh_from_db()
    assert student.status == UserStatus.SUSPENDED

    resp = client_for(admin).post(_status_url(student), {"suspend": False}, format="json")
    assert resp.status_code == 200
    student.refresh_from_db()
    assert student.status == UserStatus.ACTIVE


@pytest.mark.django_db
def test_suspended_student_cannot_log_in():
    user("adm", Role.ADMIN)
    student = user("S2", Role.STUDENT)
    student.set_password("Secret123!")
    student.save()
    student.status = UserStatus.SUSPENDED
    student.save(update_fields=["status"])
    resp = APIClient().post(
        "/api/v1/auth/login/",
        {"username": "S2", "password": "Secret123!", "role": Role.STUDENT},
        content_type="application/json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_admin_cannot_suspend_faculty():
    # SUSPEND_FACULTY is SA/AD... Admin *can*; MIS cannot.
    mis = user("mis", Role.MIS)
    faculty = user("prof", Role.FACULTY)
    assert client_for(mis).post(_status_url(faculty), {"suspend": True}).status_code == 403


@pytest.mark.django_db
def test_only_super_admin_changes_role():
    sa = user("sa", Role.SUPER_ADMIN)
    admin = user("adm", Role.ADMIN)
    target = user("mis1", Role.MIS)

    assert client_for(admin).post(_role_url(target), {"role": Role.COUNSELOR}).status_code == 403

    resp = client_for(sa).post(_role_url(target), {"role": Role.COUNSELOR}, format="json")
    assert resp.status_code == 200
    target.refresh_from_db()
    assert target.role == Role.COUNSELOR


@pytest.mark.django_db
def test_cannot_change_role_to_student():
    sa = user("sa", Role.SUPER_ADMIN)
    target = user("mis1", Role.MIS)
    resp = client_for(sa).post(_role_url(target), {"role": Role.STUDENT}, format="json")
    assert resp.status_code == 400
