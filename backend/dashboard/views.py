"""Role-aware dashboard summary for each portal's home screen.

All numbers are real aggregates over existing models (no placeholders). Queries are
bounded; per-student composites reuse attendance.services.student_summary.
"""

from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Q
from django.db.models.functions import TruncWeek
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from attendance.models import AttendanceEvent, AttendanceSource
from attendance.services import student_summary
from batches.models import Batch, BatchState, Course
from core.roles import Role
from enrollments.models import Enrollment


def _weekly_logins(student=None, batch_ids=None) -> list[dict]:
    """Distinct login-days per week for the last 6 weeks (real attendance data).

    Login attendance is unique per (student, day), so a week's row count equals its
    distinct login-days — a single grouped TruncWeek query, not six per-week counts.
    """
    today = timezone.localdate()
    mondays = [today - timedelta(days=today.weekday() + 7 * i) for i in range(5, -1, -1)]
    qs = AttendanceEvent.objects.filter(
        source=AttendanceSource.LOGIN, date__gte=mondays[0], date__lte=today
    )
    if student is not None:
        qs = qs.filter(student=student)
    elif batch_ids is not None:
        qs = qs.filter(batch_id__in=batch_ids)
    counts = {
        row["week"]: row["n"]
        for row in qs.annotate(week=TruncWeek("date")).values("week").annotate(n=Count("id"))
    }
    return [{"label": m.strftime("%d %b"), "value": counts.get(m, 0)} for m in mondays]


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = request.user.role
        if role == Role.STUDENT:
            return Response(self._student(request.user))
        if role == Role.FACULTY:
            return Response(self._faculty(request.user))
        if role in {Role.SUPER_ADMIN, Role.ADMIN, Role.MIS}:
            return Response(self._ops(role))
        if role == Role.COUNSELOR:
            return Response(self._counselor())
        if role == Role.TECH_SUPPORT:
            return Response(self._tech_support())
        return Response({"role": role, "totals": {}})

    def _student(self, user) -> dict:
        from assessments.models import Task, Test
        from content.models import Video, VideoProgress
        from liveclasses.models import LiveClass, LiveClassStatus

        now = timezone.now()
        enrollments = list(
            Enrollment.objects.filter(student=user)
            .select_related("batch", "batch__course")
            .prefetch_related("batch__faculty")
        )
        batch_ids = [e.batch_id for e in enrollments]
        batches = [
            {
                "id": str(e.batch_id),
                "code": e.batch.code,
                "name": e.batch.name,
                "course": e.batch.course.name,
                "state": e.batch.state,
                "start_date": e.batch.start_date,
                "end_date": e.batch.end_date,
                "faculty": [f.full_name or f.username for f in e.batch.faculty.all()],
            }
            for e in enrollments
        ]
        pcts = [student_summary(user, e.batch)["percent"] for e in enrollments]
        attendance_pct = round(sum(pcts) / len(pcts)) if pcts else 0

        total_videos = Video.objects.filter(batch_id__in=batch_ids).count()
        done_videos = VideoProgress.objects.filter(
            student=user, video__batch_id__in=batch_ids, completed=True
        ).count()
        pending_tasks = (
            Task.objects.filter(batch_id__in=batch_ids).exclude(submissions__student=user).count()
        )
        upcoming_tests = (
            Test.objects.filter(batch_id__in=batch_ids)
            .filter(Q(open_at__isnull=True) | Q(open_at__lte=now))
            .filter(Q(close_at__isnull=True) | Q(close_at__gte=now))
            .exclude(attempts__student=user)
            .count()
        )

        login_days = set(
            AttendanceEvent.objects.filter(student=user, source=AttendanceSource.LOGIN)
            .values_list("date", flat=True)
            .distinct()
        )
        cursor = timezone.localdate()
        if cursor not in login_days and (cursor - timedelta(days=1)) in login_days:
            cursor -= timedelta(days=1)
        streak = 0
        while cursor in login_days:
            streak += 1
            cursor -= timedelta(days=1)

        up_next = [
            {"title": lc.title, "batch_code": lc.batch.code, "scheduled_at": lc.scheduled_at}
            for lc in LiveClass.objects.filter(
                batch_id__in=batch_ids,
                status=LiveClassStatus.SCHEDULED,
                scheduled_at__gte=now,
            )
            .select_related("batch")
            .order_by("scheduled_at")[:4]
        ]
        return {
            "role": Role.STUDENT,
            "kpis": {
                "attendance_pct": attendance_pct,
                "pending_tasks": pending_tasks,
                "upcoming_tests": upcoming_tests,
                "streak_days": streak,
            },
            "videos": {"completed": done_videos, "total": total_videos},
            "trend": _weekly_logins(student=user),
            "up_next": up_next,
            "batches": batches,
        }

    def _faculty(self, user) -> dict:
        from assessments.models import TaskSubmission
        from forum.models import Thread, ThreadStatus
        from liveclasses.models import LiveClass, LiveClassStatus

        now = timezone.now()
        batch_objs = list(
            Batch.objects.filter(faculty=user)
            .select_related("course")
            .annotate(student_count=Count("enrollments", distinct=True))
        )
        batch_ids = [b.id for b in batch_objs]
        batches = [
            {
                "id": str(b.id),
                "code": b.code,
                "name": b.name,
                "course": b.course.name,
                "state": b.state,
                "student_count": b.student_count,
            }
            for b in batch_objs
        ]
        unanswered = (
            Thread.objects.filter(batch_id__in=batch_ids)
            .exclude(status=ThreadStatus.RESOLVED)
            .annotate(rc=Count("replies"))
            .filter(rc=0)
            .count()
        )
        to_grade = TaskSubmission.objects.filter(
            task__batch_id__in=batch_ids, score__isnull=True
        ).count()
        up_next = [
            {"title": lc.title, "batch_code": lc.batch.code, "scheduled_at": lc.scheduled_at}
            for lc in LiveClass.objects.filter(
                batch_id__in=batch_ids,
                status=LiveClassStatus.SCHEDULED,
                scheduled_at__gte=now,
            )
            .select_related("batch")
            .order_by("scheduled_at")[:4]
        ]
        return {
            "role": Role.FACULTY,
            "totals": {
                "batches": len(batches),
                "students": sum(b["student_count"] for b in batches),
            },
            "attention": {"unanswered_doubts": unanswered, "submissions_to_grade": to_grade},
            "trend": _weekly_logins(batch_ids=batch_ids),
            "up_next": up_next,
            "batches": batches,
        }

    def _ops(self, role) -> dict:
        active = Batch.objects.filter(state=BatchState.ACTIVE).count()
        draft = Batch.objects.filter(state=BatchState.DRAFT).count()
        completed = Batch.objects.filter(state=BatchState.COMPLETED).count()
        cert_pending = Enrollment.objects.filter(
            batch__state=BatchState.COMPLETED, certificate__isnull=True
        ).count()
        attention = {"certificate_pending": cert_pending}
        if role == Role.MIS:
            from accounts.models import DeviceChangeRequest

            attention["device_requests"] = DeviceChangeRequest.objects.filter(
                status=DeviceChangeRequest.Status.PENDING
            ).count()
        return {
            "role": role,
            "totals": {
                "batches": Batch.objects.count(),
                "active_batches": active,
                "students": Enrollment.objects.count(),
                "courses": Course.objects.count(),
            },
            "batch_states": [
                {"name": "Draft", "value": draft},
                {"name": "Active", "value": active},
                {"name": "Completed", "value": completed},
            ],
            "trend": _weekly_logins(),
            "attention": attention,
        }

    def _counselor(self) -> dict:
        today = timezone.localdate()
        active_students = (
            Enrollment.objects.filter(batch__state=BatchState.ACTIVE)
            .values("student")
            .distinct()
            .count()
        )
        logged_today = (
            AttendanceEvent.objects.filter(
                source=AttendanceSource.LOGIN, date=today, batch__state=BatchState.ACTIVE
            )
            .values("student")
            .distinct()
            .count()
        )
        return {
            "role": Role.COUNSELOR,
            "totals": {
                "students": Enrollment.objects.count(),
                "batches": Batch.objects.count(),
            },
            "kpis": {
                "active_students": active_students,
                "logged_in_today": logged_today,
                "absentees_today": max(0, active_students - logged_today),
            },
            "trend": _weekly_logins(),
        }

    def _tech_support(self) -> dict:
        from accounts.models import DeviceChangeRequest
        from forum.models import Thread, ThreadStatus

        window = settings.FORUM_RESPONSE_WINDOW_HOURS
        now = timezone.now()
        counts = {
            s: Thread.objects.filter(status=s).count()
            for s in (
                ThreadStatus.OPEN,
                ThreadStatus.ANSWERED,
                ThreadStatus.ESCALATED,
                ThreadStatus.RESOLVED,
            )
        }
        unanswered = (
            Thread.objects.exclude(status=ThreadStatus.RESOLVED)
            .annotate(rc=Count("replies"))
            .filter(rc=0)
        )
        overdue = sum(
            1 for t in unanswered if (now - t.created_at).total_seconds() / 3600 >= window
        )
        # Tech Support now owns outside-class device-change approvals, so surface the
        # pending queue here the same way the MIS ops dashboard does.
        device_requests = DeviceChangeRequest.objects.filter(
            status=DeviceChangeRequest.Status.PENDING
        ).count()
        return {
            "role": Role.TECH_SUPPORT,
            "kpis": {
                "open": counts[ThreadStatus.OPEN],
                "unanswered": unanswered.count(),
                "overdue": overdue,
                "resolved": counts[ThreadStatus.RESOLVED],
            },
            "attention": {"device_requests": device_requests},
            "forum_status": [
                {"name": "Open", "value": counts[ThreadStatus.OPEN]},
                {"name": "Answered", "value": counts[ThreadStatus.ANSWERED]},
                {"name": "Escalated", "value": counts[ThreadStatus.ESCALATED]},
                {"name": "Resolved", "value": counts[ThreadStatus.RESOLVED]},
            ],
        }
