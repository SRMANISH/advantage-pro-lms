"""Engagement reminders + completed-course helper."""

from __future__ import annotations


def has_completed_course(student) -> bool:
    from batches.models import BatchState
    from enrollments.models import Enrollment

    return Enrollment.objects.filter(student=student, batch__state=BatchState.COMPLETED).exists()


def remind_linkedin() -> int:
    """Remind active students who have not yet confirmed/skipped the LinkedIn follow."""
    from accounts.models import User, UserStatus
    from core.roles import Role
    from notifications.services import notify

    from .models import LinkedInFollow

    sent = 0
    students = User.objects.filter(role=Role.STUDENT, status=UserStatus.ACTIVE)
    for student in students:
        follow, _ = LinkedInFollow.objects.get_or_create(student=student)
        if follow.done:
            continue
        notify(
            student,
            "linkedin_follow",
            "Please follow our LinkedIn page to stay updated. Tap to open and confirm.",
            link="/student",
            subject="Follow us on LinkedIn",
            channels=("in_app", "email", "whatsapp"),
        )
        follow.reminder_count += 1
        if follow.status == LinkedInFollow.Status.NOT_SHOWN:
            follow.status = LinkedInFollow.Status.REMINDER_SHOWN
        follow.save(update_fields=["reminder_count", "status", "updated_at"])
        sent += 1
    return sent


def remind_google_review() -> int:
    """Remind completed-course students who have not submitted a Google review."""
    from notifications.services import notify

    from .models import GoogleReview
    from .views import _completed_students

    sent = 0
    for student in _completed_students():
        review, _ = GoogleReview.objects.get_or_create(student=student)
        if review.done:
            continue
        notify(
            student,
            "google_review",
            "You've completed your course — please share a Google review of your experience.",
            link="/student/certificate",
            subject="Please leave a Google review",
            channels=("in_app", "email", "whatsapp"),
        )
        review.reminder_count += 1
        review.save(update_fields=["reminder_count", "updated_at"])
        sent += 1
    return sent


def remind_next_plan() -> int:
    """Remind completed-course students who have not submitted their next-plan form."""
    from notifications.services import notify

    from .models import CourseNextPlan
    from .views import _completed_students

    sent = 0
    for student in _completed_students():
        if CourseNextPlan.objects.filter(student=student).exists():
            continue
        notify(
            student,
            "next_plan",
            "Tell us your next learning plan so we can guide you — it only takes a minute.",
            link="/student/certificate",
            subject="What's your next plan?",
            channels=("in_app", "email"),
        )
        sent += 1
    return sent


def run_engagement_reminders() -> dict:
    return {
        "linkedin": remind_linkedin(),
        "google_review": remind_google_review(),
        "next_plan": remind_next_plan(),
    }
