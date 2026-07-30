"""Activity/audit access is restricted to Faculty and MIS (updated procedure)."""

import pytest

from audit.models import AuditLog
from core.roles import Role

from .helpers import client_for, user

URL = "/api/v1/activity/"


@pytest.mark.django_db
def test_activity_access_is_mis_and_faculty_only(db):
    AuditLog.objects.create(action="login_success")
    allowed = [user("mis", Role.MIS), user("fac", Role.FACULTY)]
    denied = [
        user("ad", Role.ADMIN),
        user("sa", Role.SUPER_ADMIN),
        user("co", Role.COUNSELOR),
        user("ts", Role.TECH_SUPPORT),
        user("stu", Role.STUDENT),
    ]
    for u in allowed:
        assert client_for(u).get(URL).status_code == 200
    for u in denied:
        assert client_for(u).get(URL).status_code == 403


@pytest.mark.django_db
def test_mis_sees_all_activity(db):
    AuditLog.objects.create(action="batch_created", target_type="batch", target_id="x")
    resp = client_for(user("mis", Role.MIS)).get(URL)
    assert resp.status_code == 200
    assert any(r["action"] == "batch_created" for r in resp.json()["results"])
