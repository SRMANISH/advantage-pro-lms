"""Staff account creation: Super Admin any staff role; Admin Counsellor only."""

import pytest
from rest_framework.test import APIClient

from accounts.models import SetupToken, User, UserStatus
from core.roles import Role

URL = "/api/v1/auth/staff/"


def user(username, role):
    return User.objects.create_user(
        username=username, password="x", role=role, status=UserStatus.ACTIVE
    )


def client_for(u):
    c = APIClient()
    c.force_authenticate(user=u)
    return c


def payload(username, role, email="new@example.com"):
    return {"username": username, "full_name": "New Staff", "email": email, "role": role}


@pytest.mark.django_db
def test_super_admin_creates_any_staff_and_triggers_setup(db):
    sa = user("sa", Role.SUPER_ADMIN)
    resp = client_for(sa).post(URL, payload("fac9", Role.FACULTY), format="json")
    assert resp.status_code == 201
    created = User.objects.get(username="fac9")
    assert created.role == Role.FACULTY
    assert created.status == UserStatus.PENDING  # must complete two-step setup
    assert SetupToken.objects.filter(user=created).exists()


@pytest.mark.django_db
def test_admin_cannot_create_staff_at_all(db):
    # Updated procedure: staff creation is removed from the Admin page — SA only.
    admin = user("ad", Role.ADMIN)
    blocked = client_for(admin).post(URL, payload("co9", Role.COUNSELOR), format="json")
    assert blocked.status_code == 403
    assert client_for(admin).get(URL).status_code == 403


@pytest.mark.django_db
def test_other_roles_cannot_create_staff(db):
    for role in (Role.MIS, Role.COUNSELOR, Role.TECH_SUPPORT, Role.FACULTY, Role.STUDENT):
        resp = client_for(user(f"u_{role}", role)).post(
            URL, payload(f"x_{role}", Role.COUNSELOR), format="json"
        )
        assert resp.status_code == 403


@pytest.mark.django_db
def test_duplicate_login_id_rejected(db):
    sa = user("sa", Role.SUPER_ADMIN)
    user("taken", Role.MIS)
    resp = client_for(sa).post(URL, payload("taken", Role.COUNSELOR), format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_cannot_create_student_or_super_admin_via_staff_endpoint(db):
    sa = user("sa", Role.SUPER_ADMIN)
    for role in (Role.STUDENT, Role.SUPER_ADMIN):
        resp = client_for(sa).post(URL, payload(f"x_{role}", role), format="json")
        assert resp.status_code == 400  # not an allowed ChoiceField value
