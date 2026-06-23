from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from content.access import can_access_batch

from .models import Choice, Question, Task, TaskSubmission, Test, TestAttempt


# --- Write (faculty builds a test) ---
class ChoiceWriteSerializer(serializers.Serializer):
    text = serializers.CharField()
    is_correct = serializers.BooleanField(default=False)


class QuestionWriteSerializer(serializers.Serializer):
    text = serializers.CharField()
    choices = ChoiceWriteSerializer(many=True)

    def validate_choices(self, choices):
        if len(choices) < 2:
            raise serializers.ValidationError("Each question needs at least two choices.")
        if not any(c["is_correct"] for c in choices):
            raise serializers.ValidationError("Each question needs a correct choice.")
        return choices


class TestWriteSerializer(serializers.ModelSerializer):
    questions = QuestionWriteSerializer(many=True, write_only=True)

    class Meta:
        model = Test
        fields = ["id", "batch", "title", "open_at", "close_at", "questions"]
        read_only_fields = ["id"]

    def validate_batch(self, batch):
        if not can_access_batch(self.context["request"].user, batch):
            raise serializers.ValidationError("You cannot add a test to this batch.")
        return batch

    def validate_questions(self, questions):
        if not questions:
            raise serializers.ValidationError("Add at least one question.")
        return questions

    @transaction.atomic
    def create(self, validated):
        questions = validated.pop("questions")
        test = Test.objects.create(created_by=self.context["request"].user, **validated)
        for qi, q in enumerate(questions):
            question = Question.objects.create(test=test, text=q["text"], order=qi)
            for ci, ch in enumerate(q["choices"]):
                Choice.objects.create(
                    question=question, text=ch["text"], is_correct=ch["is_correct"], order=ci
                )
        return test


# --- Read ---
def _is_open(test) -> bool:
    now = timezone.now()
    if test.open_at and now < test.open_at:
        return False
    if test.close_at and now > test.close_at:
        return False
    return True


class TestListSerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(read_only=True)
    attempt_count = serializers.IntegerField(read_only=True)
    is_open = serializers.SerializerMethodField()
    my_attempt = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = [
            "id",
            "batch",
            "title",
            "open_at",
            "close_at",
            "question_count",
            "attempt_count",
            "is_open",
            "my_attempt",
            "created_at",
        ]

    def get_is_open(self, obj) -> bool:
        return _is_open(obj)

    def get_my_attempt(self, obj):
        user = self.context["request"].user
        attempt = TestAttempt.objects.filter(test=obj, student=user).first()
        if not attempt:
            return None
        return {"score": attempt.score, "total": attempt.total}


class ChoiceTakeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ["id", "text"]  # is_correct intentionally hidden


class QuestionTakeSerializer(serializers.ModelSerializer):
    choices = ChoiceTakeSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "text", "choices"]


class TestTakeSerializer(serializers.ModelSerializer):
    questions = QuestionTakeSerializer(many=True, read_only=True)
    is_open = serializers.SerializerMethodField()
    my_attempt = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = ["id", "title", "open_at", "close_at", "is_open", "my_attempt", "questions"]

    def get_is_open(self, obj) -> bool:
        return _is_open(obj)

    def get_my_attempt(self, obj):
        attempt = TestAttempt.objects.filter(test=obj, student=self.context["request"].user).first()
        if not attempt:
            return None
        return {"score": attempt.score, "total": attempt.total}


# --- Submit ---
class SubmitAnswerSerializer(serializers.Serializer):
    question = serializers.UUIDField()
    choice = serializers.UUIDField()


class SubmitSerializer(serializers.Serializer):
    answers = SubmitAnswerSerializer(many=True)


# --- Tasks ---
class TaskWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ["id", "batch", "title", "description", "deadline"]
        read_only_fields = ["id"]

    def validate_batch(self, batch):
        if not can_access_batch(self.context["request"].user, batch):
            raise serializers.ValidationError("You cannot add a task to this batch.")
        return batch


class TaskSerializer(serializers.ModelSerializer):
    submission_count = serializers.IntegerField(read_only=True)
    my_submission = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "batch",
            "title",
            "description",
            "deadline",
            "submission_count",
            "my_submission",
            "is_overdue",
            "created_at",
        ]

    def get_is_overdue(self, obj) -> bool:
        return bool(obj.deadline and timezone.now() > obj.deadline)

    def get_my_submission(self, obj):
        user = self.context["request"].user
        sub = TaskSubmission.objects.filter(task=obj, student=user).first()
        if not sub:
            return None
        return {
            "submitted_at": sub.submitted_at,
            "is_late": sub.is_late,
            "score": sub.score,
            "feedback": sub.feedback,
            "text": sub.text,
            "has_file": bool(sub.file_key),
        }


class TaskSubmitSerializer(serializers.Serializer):
    text = serializers.CharField(required=False, allow_blank=True, default="")
    file = serializers.FileField(required=False)

    def validate(self, attrs):
        if not attrs.get("text") and not attrs.get("file"):
            raise serializers.ValidationError("Provide text or a file.")
        return attrs


class SubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    registration_number = serializers.CharField(source="student.username", read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = TaskSubmission
        fields = [
            "id",
            "student_name",
            "registration_number",
            "text",
            "file_url",
            "is_late",
            "score",
            "feedback",
            "submitted_at",
        ]
        read_only_fields = fields

    def get_file_url(self, obj) -> str:
        return f"/api/v1/task-submissions/{obj.id}/file/" if obj.file_key else ""


class GradeSerializer(serializers.Serializer):
    score = serializers.IntegerField(min_value=0)
    feedback = serializers.CharField(required=False, allow_blank=True, default="")
