"""Composite performance: tests + tasks + video + attendance, with batch rank."""

from __future__ import annotations

from django.db.models import Count

from assessments.models import Task, TaskSubmission, Test, TestAttempt
from attendance.services import batch_attendance_summaries, student_summary
from content.models import Video, VideoProgress


def _avg(nums: list[int]) -> int:
    return round(sum(nums) / len(nums)) if nums else 0


def batch_totals(batch) -> dict:
    return {
        "videos": Video.objects.filter(batch=batch).count(),
        "tests": Test.objects.filter(batch=batch).count(),
        "tasks": Task.objects.filter(batch=batch).count(),
    }


def student_metrics(student, batch, totals: dict | None = None) -> dict:
    totals = totals or batch_totals(batch)
    tv, tt, tk = totals["videos"], totals["tests"], totals["tasks"]

    completed_videos = VideoProgress.objects.filter(
        student=student, video__batch=batch, completed=True
    ).count()
    video_pct = round(completed_videos / tv * 100) if tv else 0

    attempts = TestAttempt.objects.filter(student=student, test__batch=batch)
    test_pcts = [round(a.score / a.total * 100) for a in attempts if a.total]
    test_pct = _avg(test_pcts)

    submitted = TaskSubmission.objects.filter(student=student, task__batch=batch).count()
    task_pct = round(submitted / tk * 100) if tk else 0

    attendance_pct = student_summary(student, batch)["percent"]

    # Composite over the components that actually exist in this batch (+ attendance).
    components = []
    if tt:
        components.append(test_pct)
    if tk:
        components.append(task_pct)
    if tv:
        components.append(video_pct)
    components.append(attendance_pct)

    return {
        "test_pct": test_pct,
        "task_pct": task_pct,
        "video_pct": video_pct,
        "attendance_pct": attendance_pct,
        "overall": _avg(components),
    }


def batch_performance(batch) -> list[dict]:
    """Ranked performance for every student in a batch.

    Set-based: a fixed handful of grouped queries (videos, tasks, tests, attendance) rather
    than ~5 per student, so a 1,000-student batch stays a handful of queries instead of
    thousands. Output shape matches :func:`student_metrics` for a single student.
    """
    from accounts.models import User

    totals = batch_totals(batch)
    tv, tt, tk = totals["videos"], totals["tests"], totals["tasks"]
    students = list(User.objects.filter(enrollments__batch=batch).distinct())
    ids = [s.id for s in students]

    # Completed videos per student (1 query).
    vids = dict(
        VideoProgress.objects.filter(video__batch=batch, completed=True, student_id__in=ids)
        .values("student_id")
        .annotate(n=Count("id"))
        .values_list("student_id", "n")
    )
    # Task submissions per student (1 query).
    tasks = dict(
        TaskSubmission.objects.filter(task__batch=batch, student_id__in=ids)
        .values("student_id")
        .annotate(n=Count("id"))
        .values_list("student_id", "n")
    )
    # Test attempts per student — average of per-attempt percentages (1 query).
    test_scores: dict = {}
    for sid, score, total in TestAttempt.objects.filter(
        test__batch=batch, student_id__in=ids
    ).values_list("student_id", "score", "total"):
        if total:
            test_scores.setdefault(sid, []).append(round(score / total * 100))
    # Login attendance per student (1 query).
    attendance = batch_attendance_summaries(batch, students)

    rows = []
    for s in students:
        video_pct = round(vids.get(s.id, 0) / tv * 100) if tv else 0
        test_pct = _avg(test_scores.get(s.id, []))
        task_pct = round(tasks.get(s.id, 0) / tk * 100) if tk else 0
        attendance_pct = attendance.get(s.id, {}).get("percent", 0)
        components = []
        if tt:
            components.append(test_pct)
        if tk:
            components.append(task_pct)
        if tv:
            components.append(video_pct)
        components.append(attendance_pct)
        rows.append(
            {
                "student": str(s.id),
                "student_name": s.full_name or s.username,
                "registration_number": s.username,
                "test_pct": test_pct,
                "task_pct": task_pct,
                "video_pct": video_pct,
                "attendance_pct": attendance_pct,
                "overall": _avg(components),
            }
        )
    rows.sort(key=lambda r: r["overall"], reverse=True)

    rank, prev = 0, None
    for r in rows:
        if r["overall"] != prev:
            rank += 1
            prev = r["overall"]
        r["rank"] = rank
    return rows
