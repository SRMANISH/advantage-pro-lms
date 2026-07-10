"""MCQ tests: scheduled, auto-graded, one attempt per student."""

from django.conf import settings
from django.db import models

from batches.models import Batch
from core.models import TimeStampedModel


class TestKind(models.TextChoices):
    MCQ = "mcq", "Multiple choice (auto-graded)"
    FILE = "file", "File upload (e.g. Excel)"
    COLAB = "colab", "Colab / notebook link"


class Test(TimeStampedModel):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="tests")
    title = models.CharField(max_length=200)
    # MCQ = the classic auto-graded flow; FILE/COLAB = student submits an artefact
    # (an Excel workbook, a Colab notebook link) that faculty grade by hand out of max_score.
    kind = models.CharField(max_length=10, choices=TestKind.choices, default=TestKind.MCQ)
    instructions = models.TextField(blank=True)
    max_score = models.PositiveSmallIntegerField(default=100)
    open_at = models.DateTimeField(null=True, blank=True)
    close_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class Question(TimeStampedModel):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "created_at"]


class Choice(TimeStampedModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=400)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "created_at"]


class TestAttempt(TimeStampedModel):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="attempts")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="test_attempts"
    )
    score = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    # File/Colab submissions: the uploaded artefact or link, plus manual-grading state.
    file_key = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    link = models.URLField(max_length=500, blank=True)
    feedback = models.TextField(blank=True)
    # MCQ attempts are graded the instant they're submitted; file/colab wait for faculty.
    graded = models.BooleanField(default=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["test", "student"], name="uniq_test_student")
        ]


class AttemptAnswer(TimeStampedModel):
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="+")
    choice = models.ForeignKey(Choice, null=True, on_delete=models.SET_NULL, related_name="+")


class TaskDeadlineType(models.TextChoices):
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    CUSTOM = "custom", "Custom"


class Task(TimeStampedModel):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    deadline = models.DateTimeField(null=True, blank=True)
    deadline_type = models.CharField(
        max_length=10, choices=TaskDeadlineType.choices, default=TaskDeadlineType.CUSTOM
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class TaskSubmission(TimeStampedModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="task_submissions"
    )
    text = models.TextField(blank=True)
    file_key = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    is_late = models.BooleanField(default=False)
    score = models.PositiveSmallIntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["task", "student"], name="uniq_task_student")
        ]
