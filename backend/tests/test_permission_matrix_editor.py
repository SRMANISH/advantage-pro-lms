"""Super Admin editable permission matrix: overrides, resets, lockout guard, scoping."""

import pytest

from batches.models import Course
from core.models import PermissionOverride
from core.permissions_matrix import Action, can
from core.roles import Role
from .helpers import client_for, user

MATRIX_URL = "/api/v1/permissions/matrix/"


@pytest.mark.django_db
def test_only_super_admin_reads_matrix(db):
    sa = user("sa", Role.SUPER_ADMIN)
    admin = user("adm", Role.ADMIN)
    assert client_for(admin).get(MATRIX_URL).status_code == 403
    body = client_for(sa).get(MATRIX_URL).json()
    row = next(r for r in body["rows"] if r["action"] == Action.CREATE_EDIT_BATCH)
    assert row["roles"] == ["admin"] and row["overridden"] is False


@pytest.mark.django_db
def test_override_changes_enforcement_and_reset_reverts(db):
    sa = user("sa", Role.SUPER_ADMIN)
    mis = user("mis", Role.MIS)
    course = Course.objects.create(code="FS", name="Full Stack")
    c_sa, c_mis = client_for(sa), client_for(mis)
    batch_body = {
        "code": "FS-9",
        "name": "B",
        "course": str(course.id),
        "start_date": "2026-03-01",
        "end_date": "2026-06-01",
        "class_days": ["mon"],
        "class_start_time": "18:00",
        "class_end_time": "20:00",
    }

    # Default: MIS may not create batches.
    assert not can(Role.MIS, Action.CREATE_EDIT_BATCH)

    # Override to allow MIS as well -> enforcement flips (real endpoint honours it).
    resp = c_sa.put(
        f"{MATRIX_URL}{Action.CREATE_EDIT_BATCH}/",
        {"roles": [Role.ADMIN, Role.MIS]},
        format="json",
    )
    assert resp.status_code == 200 and resp.json()["overridden"] is True
    assert can(Role.MIS, Action.CREATE_EDIT_BATCH)
    created = c_mis.post("/api/v1/batches/", batch_body, format="json")
    assert created.status_code in (200, 201)

    # Reset -> default enforcement returns.
    assert c_sa.delete(f"{MATRIX_URL}{Action.CREATE_EDIT_BATCH}/").status_code == 200
    assert not can(Role.MIS, Action.CREATE_EDIT_BATCH)
    denied = c_mis.post("/api/v1/batches/", {**batch_body, "code": "FS-10"}, format="json")
    assert denied.status_code == 403


@pytest.mark.django_db
def test_saving_default_roles_stores_no_override_row(db):
    sa = user("sa", Role.SUPER_ADMIN)
    resp = client_for(sa).put(
        f"{MATRIX_URL}{Action.CREATE_EDIT_BATCH}/", {"roles": [Role.ADMIN]}, format="json"
    )
    assert resp.status_code == 200 and resp.json()["overridden"] is False
    assert not PermissionOverride.objects.exists()


@pytest.mark.django_db
def test_lockout_guard_keeps_super_admin_on_settings(db):
    sa = user("sa", Role.SUPER_ADMIN)
    resp = client_for(sa).put(
        f"{MATRIX_URL}{Action.MANAGE_SETTINGS}/", {"roles": [Role.ADMIN]}, format="json"
    )
    assert resp.status_code == 400
    assert "lockout" in resp.json()["detail"].lower()


@pytest.mark.django_db
def test_invalid_roles_and_unknown_action_rejected(db):
    sa = user("sa", Role.SUPER_ADMIN)
    c = client_for(sa)
    assert (
        c.put(
            f"{MATRIX_URL}{Action.CREATE_EDIT_BATCH}/", {"roles": ["wizard"]}, format="json"
        ).status_code
        == 400
    )
    assert c.put(f"{MATRIX_URL}not_an_action/", {"roles": []}, format="json").status_code == 404
