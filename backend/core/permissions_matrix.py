"""Single source of truth for the role -> action permission matrix.

This mirrors section 6 of the execution plan. It is enforced server-side on every
endpoint (see core/permissions.py). It is intentionally code-defined for now; a later
module promotes it to a DB-backed, Super-Admin-editable matrix without changing callers
(``can`` stays the contract).

Conditions noted in the plan (handled by object-level checks in their own modules):
  * Class recordings are uploaded only by the faculty who taught them.
  * Faculty exports are limited to their own batches; Counselor to attendance/performance.
  * Forum: Tech Support is monitor-only; Admin/Super Admin/Faculty/Student/MIS per role.
  * Student suspension requires Super Admin approval; Admin can suspend faculty directly.
"""

from .roles import Role

SA, AD, MIS, CO, TS, FAC, STU = (
    Role.SUPER_ADMIN,
    Role.ADMIN,
    Role.MIS,
    Role.COUNSELOR,
    Role.TECH_SUPPORT,
    Role.FACULTY,
    Role.STUDENT,
)


class Action:
    CREATE_EDIT_BATCH = "create_edit_batch"
    DELETE_BATCH = "delete_batch"
    IMPORT_STUDENTS = "import_students"
    MANAGE_STAFF_ACCOUNTS = "manage_staff_accounts"
    CHANGE_USER_ROLE = "change_user_role"
    ASSIGN_FACULTY = "assign_faculty"
    UPLOAD_VIDEOS = "upload_videos"
    UPLOAD_NOTES = "upload_notes"
    CREATE_TESTS_TASKS = "create_tests_tasks"
    SUBMIT_TASKS_TESTS = "submit_tasks_tests"
    VIEW_PERFORMANCE = "view_performance"
    MANAGE_ATTENDANCE = "manage_attendance"
    EXPORT_REPORTS = "export_reports"
    ACCESS_AUDIT = "access_audit"
    MANAGE_FORUM = "manage_forum"
    SCHEDULE_LIVE_CLASSES = "schedule_live_classes"
    SEND_NOTIFICATIONS = "send_notifications"
    SUSPEND_STUDENT = "suspend_student"
    SUSPEND_FACULTY = "suspend_faculty"
    REVOKE_VIDEO_ACCESS = "revoke_video_access"
    MANAGE_SETTINGS = "manage_settings"


MATRIX: dict[str, frozenset[str]] = {
    Action.CREATE_EDIT_BATCH: frozenset({SA, AD, MIS}),
    Action.DELETE_BATCH: frozenset({SA}),
    Action.IMPORT_STUDENTS: frozenset({SA, AD, MIS}),
    Action.MANAGE_STAFF_ACCOUNTS: frozenset({SA}),
    Action.CHANGE_USER_ROLE: frozenset({SA}),
    Action.ASSIGN_FACULTY: frozenset({SA, AD, MIS, FAC}),
    Action.UPLOAD_VIDEOS: frozenset({SA, AD, MIS, FAC}),
    Action.UPLOAD_NOTES: frozenset({SA, AD, MIS, FAC}),
    Action.CREATE_TESTS_TASKS: frozenset({SA, AD, MIS, FAC}),
    Action.SUBMIT_TASKS_TESTS: frozenset({STU}),
    Action.VIEW_PERFORMANCE: frozenset({SA, AD, MIS, CO, FAC, STU}),
    Action.MANAGE_ATTENDANCE: frozenset({SA, AD, MIS, CO, FAC, STU}),
    Action.EXPORT_REPORTS: frozenset({SA, AD, MIS, CO, FAC}),
    Action.ACCESS_AUDIT: frozenset({SA, AD, MIS, FAC}),
    Action.MANAGE_FORUM: frozenset({SA, AD, MIS, TS, FAC, STU}),
    Action.SCHEDULE_LIVE_CLASSES: frozenset({SA, AD, MIS}),
    Action.SEND_NOTIFICATIONS: frozenset({SA, AD, MIS, CO, TS, FAC}),
    Action.SUSPEND_STUDENT: frozenset({SA, AD, MIS}),
    Action.SUSPEND_FACULTY: frozenset({SA, AD}),
    Action.REVOKE_VIDEO_ACCESS: frozenset({SA, AD}),
    Action.MANAGE_SETTINGS: frozenset({SA}),
}


def can(role: str, action: str) -> bool:
    """Return True if ``role`` is permitted to perform ``action``."""
    return role in MATRIX.get(action, frozenset())


def roles_for(action: str) -> frozenset[str]:
    """Return the set of roles permitted to perform ``action``."""
    return MATRIX.get(action, frozenset())
