"""Suspend / reactivate and change-role staff endpoints (matrix-gated)."""

import pytest
from rest_framework.test import APIClient

from accounts.models import UserStatus
from core.roles import Role
from .helpers import client_for, user


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


# --------------------------- Super Admin lockout guards ---------------------------
# Super Admin is the only role that can grant roles, so a demotion that removes the last
# one is unrecoverable through the UI — there is nobody left who can appoint a replacement.
# (Suspension is not a second route to the same state: UserStatusView only accepts student
# and faculty targets, so a Super Admin cannot be suspended at all.)


@pytest.mark.django_db
def test_super_admin_cannot_demote_their_own_account():
    sa = user("sa_self", Role.SUPER_ADMIN)
    user("sa_other", Role.SUPER_ADMIN)  # a second one exists, so this is purely the self rule

    resp = client_for(sa).post(_role_url(sa), {"role": Role.MIS}, format="json")

    assert resp.status_code == 400
    assert "your own" in resp.data["detail"].lower()
    sa.refresh_from_db()
    assert sa.role == Role.SUPER_ADMIN


@pytest.mark.django_db
def test_last_super_admin_cannot_be_demoted():
    acting = user("sa_acting", Role.SUPER_ADMIN)
    target = user("sa_target", Role.SUPER_ADMIN)
    # Demoting `target` is fine while `acting` remains...
    assert (
        client_for(acting).post(_role_url(target), {"role": Role.MIS}, format="json").status_code
        == 200
    )

    # ...but `acting` is now the last one, and cannot be demoted by anyone.
    resp = client_for(acting).post(_role_url(acting), {"role": Role.MIS}, format="json")
    assert resp.status_code == 400
    acting.refresh_from_db()
    assert acting.role == Role.SUPER_ADMIN


@pytest.mark.django_db
def test_sole_active_super_admin_cannot_be_demoted_by_another_account():
    """Defence in depth — this branch is not reachable through login today.

    CHANGE_USER_ROLE is in ``LOCKED_SA_ACTIONS``, so it cannot be granted to another role by
    a PermissionOverride: any actor who reaches this view is a Super Admin. And if the actor
    is a *different* Super Admin who can sign in, then by definition a second active Super
    Admin exists and the guard never fires — the self-demotion rule above is the one that
    actually protects the live deployment.

    The check still earns its place: it is the invariant, not a restatement of the matrix. It
    is exercised here with a PENDING Super Admin (an account created but never set up, which
    cannot log in) to pin the intended behaviour if the matrix is ever widened.
    """
    pending_sa = user("sa_pending", Role.SUPER_ADMIN, status=UserStatus.PENDING)
    sole_active = user("sa_sole", Role.SUPER_ADMIN)

    resp = client_for(pending_sa).post(_role_url(sole_active), {"role": Role.MIS}, format="json")

    assert resp.status_code == 400
    assert "last active super admin" in resp.data["detail"].lower()
    sole_active.refresh_from_db()
    assert sole_active.role == Role.SUPER_ADMIN


@pytest.mark.django_db
def test_demoting_a_non_super_admin_is_unaffected():
    """The guard must not leak into ordinary role changes."""
    sa = user("sa_ok", Role.SUPER_ADMIN)
    mis = user("mis_ok", Role.MIS)
    resp = client_for(sa).post(_role_url(mis), {"role": Role.COUNSELOR}, format="json")
    assert resp.status_code == 200
    mis.refresh_from_db()
    assert mis.role == Role.COUNSELOR
