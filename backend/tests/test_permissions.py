"""The RBAC matrix is security-critical, so it is pinned by tests."""

from core.permissions_matrix import Action, can, roles_for
from core.roles import Role


def test_only_super_admin_can_delete_batch_and_manage_settings():
    assert roles_for(Action.DELETE_BATCH) == frozenset({Role.SUPER_ADMIN})
    assert roles_for(Action.MANAGE_SETTINGS) == frozenset({Role.SUPER_ADMIN})


def test_only_students_submit_tests_and_tasks():
    assert roles_for(Action.SUBMIT_TASKS_TESTS) == frozenset({Role.STUDENT})
    assert not can(Role.FACULTY, Action.SUBMIT_TASKS_TESTS)


def test_tech_support_is_forum_only():
    assert can(Role.TECH_SUPPORT, Action.MANAGE_FORUM)
    forbidden = [
        Action.CREATE_EDIT_BATCH,
        Action.UPLOAD_VIDEOS,
        Action.MANAGE_ATTENDANCE,
        Action.SCHEDULE_LIVE_CLASSES,
        Action.VIEW_PERFORMANCE,
    ]
    assert all(not can(Role.TECH_SUPPORT, a) for a in forbidden)


def test_counselor_sees_attendance_and_performance_only():
    assert can(Role.COUNSELOR, Action.MANAGE_ATTENDANCE)
    assert can(Role.COUNSELOR, Action.VIEW_PERFORMANCE)
    assert not can(Role.COUNSELOR, Action.CREATE_EDIT_BATCH)
    assert not can(Role.COUNSELOR, Action.MANAGE_FORUM)
    assert not can(Role.COUNSELOR, Action.UPLOAD_VIDEOS)


def test_faculty_can_upload_and_assign_but_not_schedule_live_classes():
    assert can(Role.FACULTY, Action.UPLOAD_VIDEOS)
    assert can(Role.FACULTY, Action.ASSIGN_FACULTY)
    assert not can(Role.FACULTY, Action.SCHEDULE_LIVE_CLASSES)


def test_unknown_action_denies_everyone():
    assert roles_for("nonexistent_action") == frozenset()
    assert not can(Role.SUPER_ADMIN, "nonexistent_action")
