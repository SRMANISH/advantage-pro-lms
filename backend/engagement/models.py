"""Engagement & re-engagement.

* LinkedIn follow — post-login reminder until the student confirms they followed.
* Google review — course-end reminder until the student submits a review.
* Course next plan — end-of-course marketing/re-engagement data for Admin/MIS.

None of these block learning access; they are reminder + reporting flows.
"""

from django.conf import settings
from django.db import models

from batches.models import Batch
from core.models import TimeStampedModel


class LinkedInFollow(TimeStampedModel):
    class Status(models.TextChoices):
        NOT_SHOWN = "not_shown", "Not shown"
        REMINDER_SHOWN = "reminder_shown", "Reminder shown"
        OPENED = "opened", "Opened LinkedIn"
        CONFIRMED = "confirmed", "Confirmed followed"
        SKIPPED = "skipped", "Reminder skipped"

    student = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="linkedin_follow"
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NOT_SHOWN)
    reminder_count = models.PositiveIntegerField(default=0)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    @property
    def done(self) -> bool:
        return self.status in {self.Status.CONFIRMED, self.Status.SKIPPED}


class GoogleReview(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        LINK_OPENED = "link_opened", "Link opened"
        SUBMITTED = "submitted", "Submitted"
        SKIPPED = "skipped", "Skipped"

    student = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="google_review"
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    reminder_count = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(null=True, blank=True)

    @property
    def done(self) -> bool:
        return self.status in {self.Status.SUBMITTED, self.Status.SKIPPED}


class CourseNextPlan(TimeStampedModel):
    """End-of-course re-engagement / marketing data — separate from certificate data."""

    class Goal(models.TextChoices):
        JOB_CHANGE = "job_change", "Job change"
        PROMOTION = "promotion", "Promotion"
        UPSKILLING = "upskilling", "Upskilling"
        OTHER = "other", "Other"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="next_plans"
    )
    batch = models.ForeignKey(
        Batch, null=True, blank=True, on_delete=models.SET_NULL, related_name="next_plans"
    )
    planning_another_course = models.BooleanField(default=False)
    interested_course = models.CharField(max_length=200, blank=True)
    expected_timing = models.CharField(max_length=100, blank=True)
    goal = models.CharField(max_length=16, choices=Goal.choices, blank=True)
    preferred_contact_time = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["student", "batch"], name="uniq_next_plan")]
        indexes = [models.Index(fields=["student"])]


class UtilityLink(TimeStampedModel):
    """MIS-curated notice-board links (YouTube sessions, resources) shown publicly on the
    landing page. MIS manages them; anyone can read."""

    title = models.CharField(max_length=200)
    url = models.URLField(max_length=500)
    pinned = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-pinned", "-created_at"]

    def __str__(self) -> str:
        return self.title
