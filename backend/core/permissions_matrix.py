"""Single source of truth for the role -> action permission matrix.

This mirrors section 6 of the execution plan. It is enforced server-side on every
endpoint (see core/permissions.py). It is intentionally code-defined for now; a later
module promotes it to a DB-backed, Super-Admin-editable matrix without changing callers
(``can`` stays the contract).

Conditions noted in the updated operating procedure (handled by object-level checks in
their own modules):
  * Class videos are uploaded only by the faculty who taught them.
  * Faculty exports/activity are limited to their own batches; Counselor to
    attendance/performance only.
  * Forum: Tech Support can reply/monitor; Faculty answers; Student asks; MIS monitors.
    Admin/Super Admin no longer moderate.
  * Live classes are scheduled by Faculty for their own batches.
  * Video access: individual revoke = MIS; course-end closure = Admin + MIS (never SA).
  * Device change: approved by Faculty during a live class, by MIS outside class hours.
  * Batch creation and faculty assignment are Admin-only (Faculty never assigns Faculty).
  * Notes/MCQ uploads and activity/audit access exclude Admin and Super Admin.
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
    CREATE_TESTS = "create_tests"
    CREATE_TASKS = "create_tasks"
    SUBMIT_TASKS_TESTS = "submit_tasks_tests"
    VIEW_PERFORMANCE = "view_performance"
    MANAGE_ATTENDANCE = "manage_attendance"
    EXPORT_REPORTS = "export_reports"
    ACCESS_AUDIT = "access_audit"
    MANAGE_FORUM = "manage_forum"
    SCHEDULE_LIVE_CLASSES = "schedule_live_classes"
    REVOKE_VIDEO_INDIVIDUAL = "revoke_video_individual"
    CLOSE_COURSE_VIDEO_ACCESS = "close_course_video_access"
    APPROVE_DEVICE_CHANGE = "approve_device_change"
    SEND_NOTIFICATIONS = "send_notifications"
    SUSPEND_STUDENT = "suspend_student"
    SUSPEND_FACULTY = "suspend_faculty"
    MANAGE_SETTINGS = "manage_settings"


# Updated operating procedure permission matrix. Super Admin is intentionally absent
# from operational flows (batch creation, faculty assignment, notes/MCQ upload,
# activity/audit, video revoke/closure, live-class scheduling).
MATRIX: dict[str, frozenset[str]] = {
    Action.CREATE_EDIT_BATCH: frozenset({AD}),
    Action.DELETE_BATCH: frozenset({AD}),
    Action.IMPORT_STUDENTS: frozenset({AD, MIS}),
    Action.MANAGE_STAFF_ACCOUNTS: frozenset({SA, AD}),
    Action.CHANGE_USER_ROLE: frozenset({SA}),
    Action.ASSIGN_FACULTY: frozenset({AD}),
    Action.UPLOAD_VIDEOS: frozenset({FAC}),
    Action.UPLOAD_NOTES: frozenset({MIS, FAC}),
    Action.CREATE_TESTS: frozenset({MIS, FAC}),
    Action.CREATE_TASKS: frozenset({FAC}),
    Action.SUBMIT_TASKS_TESTS: frozenset({STU}),
    Action.VIEW_PERFORMANCE: frozenset({SA, AD, MIS, CO, FAC, STU}),
    Action.MANAGE_ATTENDANCE: frozenset({SA, AD, MIS, CO, FAC, STU}),
    Action.EXPORT_REPORTS: frozenset({SA, AD, MIS, CO, FAC}),
    Action.ACCESS_AUDIT: frozenset({MIS, FAC}),
    Action.MANAGE_FORUM: frozenset({MIS, TS, FAC, STU}),
    Action.SCHEDULE_LIVE_CLASSES: frozenset({FAC}),
    Action.REVOKE_VIDEO_INDIVIDUAL: frozenset({MIS}),
    Action.CLOSE_COURSE_VIDEO_ACCESS: frozenset({AD, MIS}),
    Action.APPROVE_DEVICE_CHANGE: frozenset({FAC, MIS}),
    Action.SEND_NOTIFICATIONS: frozenset({SA, AD, MIS, CO, TS, FAC}),
    Action.SUSPEND_STUDENT: frozenset({SA, AD, MIS}),
    Action.SUSPEND_FACULTY: frozenset({SA, AD}),
    Action.MANAGE_SETTINGS: frozenset({SA}),
}


def can(role: str, action: str) -> bool:
    """Return True if ``role`` is permitted to perform ``action``."""
    return role in MATRIX.get(action, frozenset())


def roles_for(action: str) -> frozenset[str]:
    """Return the set of roles permitted to perform ``action``."""
    return MATRIX.get(action, frozenset())
