"""The RBAC matrix is security-critical, so the full updated matrix is pinned here.

This mirrors the updated operating procedure. The parametrized ``test_matrix_is_exact``
is the single source of regression truth; the named tests below document the headline
rules in human-readable form.
"""

import pytest

from core.permissions_matrix import Action, can, roles_for
from core.roles import Role

SA, AD, MIS, CO, TS, FAC, STU = (
    Role.SUPER_ADMIN,
    Role.ADMIN,
    Role.MIS,
    Role.COUNSELOR,
    Role.TECH_SUPPORT,
    Role.FACULTY,
    Role.STUDENT,
)
ALL_ROLES = [SA, AD, MIS, CO, TS, FAC, STU]

# The authoritative expected matrix per the updated operating procedure.
EXPECTED: dict[str, set[str]] = {
    Action.CREATE_EDIT_BATCH: {AD},
    # Draft delete = Admin too; started-batch delete = SA only (state check in the view).
    Action.DELETE_BATCH: {SA, AD},
    Action.MANAGE_COURSES: {SA},
    Action.IMPORT_STUDENTS: {AD, MIS},
    Action.MANAGE_STAFF_ACCOUNTS: {SA},
    Action.CHANGE_USER_ROLE: {SA},
    Action.ASSIGN_FACULTY: {AD},
    Action.UPLOAD_VIDEOS: {FAC},
    Action.UPLOAD_NOTES: {MIS, FAC},
    Action.CREATE_TESTS: {MIS, FAC},
    Action.CREATE_TASKS: {MIS, FAC},
    Action.SUBMIT_TASKS_TESTS: {STU},
    Action.VIEW_PERFORMANCE: {SA, AD, MIS, CO, FAC, STU},
    Action.MANAGE_ATTENDANCE: {SA, AD, MIS, CO, FAC, STU},
    Action.EXPORT_REPORTS: {SA, AD, MIS, CO, FAC},
    Action.ACCESS_AUDIT: {MIS, FAC},
    Action.MANAGE_FORUM: {TS, FAC, STU},
    Action.SCHEDULE_LIVE_CLASSES: {FAC},
    Action.REVOKE_VIDEO_INDIVIDUAL: {MIS},
    Action.CLOSE_COURSE_VIDEO_ACCESS: {AD, MIS},
    Action.APPROVE_DEVICE_CHANGE: {FAC, TS, MIS},
    Action.SEND_NOTIFICATIONS: {SA, AD, MIS, CO, TS, FAC},
    Action.SUSPEND_STUDENT: {SA, AD, MIS},
    Action.SUSPEND_FACULTY: {SA, AD},
    Action.MANAGE_SETTINGS: {SA},
}


@pytest.mark.parametrize("action,allowed", list(EXPECTED.items()))
def test_matrix_is_exact(action, allowed):
    """For every action, exactly the expected roles are allowed and all others denied."""
    assert roles_for(action) == frozenset(allowed)
    for r in ALL_ROLES:
        assert can(r, action) is (r in allowed)


# --- Headline rules from the updated operating procedure (human-readable) ---


def test_super_admin_is_out_of_restricted_operational_flows():
    restricted = [
        Action.CREATE_EDIT_BATCH,
        Action.ASSIGN_FACULTY,
        Action.UPLOAD_NOTES,
        Action.CREATE_TESTS,
        Action.CREATE_TASKS,
        Action.UPLOAD_VIDEOS,
        Action.ACCESS_AUDIT,
        Action.REVOKE_VIDEO_INDIVIDUAL,
        Action.CLOSE_COURSE_VIDEO_ACCESS,
        Action.SCHEDULE_LIVE_CLASSES,
    ]
    assert all(not can(SA, a) for a in restricted)


def test_only_admin_creates_batches_and_assigns_faculty():
    assert can(AD, Action.CREATE_EDIT_BATCH)
    assert not can(MIS, Action.CREATE_EDIT_BATCH)
    assert not can(SA, Action.CREATE_EDIT_BATCH)
    assert can(AD, Action.ASSIGN_FACULTY)
    assert not can(FAC, Action.ASSIGN_FACULTY)


def test_notes_and_mcq_uploads_are_mis_and_faculty_only():
    for a in (Action.UPLOAD_NOTES, Action.CREATE_TESTS):
        assert can(MIS, a) and can(FAC, a)
        assert not can(AD, a) and not can(SA, a)


def test_tasks_created_by_mis_and_faculty():
    assert can(MIS, Action.CREATE_TASKS) and can(FAC, Action.CREATE_TASKS)
    assert not can(AD, Action.CREATE_TASKS) and not can(SA, Action.CREATE_TASKS)


def test_faculty_now_schedules_live_classes_and_uploads_videos():
    assert can(FAC, Action.SCHEDULE_LIVE_CLASSES)
    assert not can(AD, Action.SCHEDULE_LIVE_CLASSES)
    assert not can(MIS, Action.SCHEDULE_LIVE_CLASSES)
    assert can(FAC, Action.UPLOAD_VIDEOS)


def test_activity_audit_is_faculty_and_mis_only():
    assert can(FAC, Action.ACCESS_AUDIT) and can(MIS, Action.ACCESS_AUDIT)
    assert not can(SA, Action.ACCESS_AUDIT) and not can(AD, Action.ACCESS_AUDIT)


def test_video_revoke_and_closure_exclude_super_admin():
    assert roles_for(Action.REVOKE_VIDEO_INDIVIDUAL) == frozenset({MIS})
    assert roles_for(Action.CLOSE_COURSE_VIDEO_ACCESS) == frozenset({AD, MIS})


def test_tech_support_can_use_forum_but_not_unrelated_actions():
    assert can(TS, Action.MANAGE_FORUM)
    forbidden = [
        Action.CREATE_EDIT_BATCH,
        Action.UPLOAD_VIDEOS,
        Action.MANAGE_ATTENDANCE,
        Action.SCHEDULE_LIVE_CLASSES,
        Action.VIEW_PERFORMANCE,
    ]
    assert all(not can(TS, a) for a in forbidden)


def test_counselor_and_mis_both_handle_attendance_followup():
    assert can(CO, Action.MANAGE_ATTENDANCE) and can(MIS, Action.MANAGE_ATTENDANCE)
    assert not can(CO, Action.CREATE_EDIT_BATCH)
    assert not can(CO, Action.UPLOAD_VIDEOS)


def test_only_students_submit_tests_and_tasks():
    assert roles_for(Action.SUBMIT_TASKS_TESTS) == frozenset({STU})
    assert not can(FAC, Action.SUBMIT_TASKS_TESTS)


def test_unknown_action_denies_everyone():
    assert roles_for("nonexistent_action") == frozenset()
    assert not can(SA, "nonexistent_action")
