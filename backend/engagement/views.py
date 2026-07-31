"""Engagement APIs: student status + actions, Admin/MIS reports, and utility links."""

from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User, UserStatus
from audit.services import record_action
from content.delivery import deliver
from core.adapters.registry import get_storage
from core.permissions import has_any_role
from core.roles import Role
from core.schema import DetailResponse, OkResponse
from core.uploads import storage_name, validate_upload
from notifications.services import admins_and_mis, notify_many

from .models import CourseNextPlan, GoogleReview, LinkedInFollow, UtilityLink
from .services import has_completed_course

ReportRoles = has_any_role(Role.ADMIN, Role.MIS)
UtilityManageRoles = has_any_role(Role.MIS)


class UtilityLinkSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    url = serializers.URLField(max_length=500)
    pinned = serializers.BooleanField(required=False, default=False)


def _link_row(link) -> dict:
    return {
        "id": link.id,
        "title": link.title,
        "url": link.url,
        "pinned": link.pinned,
        "thumbnail_url": (
            f"/api/v1/utility-links/{link.id}/thumbnail/" if link.thumbnail_key else None
        ),
        "created_at": link.created_at,
    }


class PromptStateSerializer(serializers.Serializer):
    """Whether a nudge should be shown, and where the student got to with it."""

    status = serializers.CharField(allow_null=True, required=False)
    show = serializers.BooleanField()


class EngagementMeResponse(serializers.Serializer):
    """The three post-course nudges, as the student portal sees them."""

    linkedin = PromptStateSerializer()
    google_review = PromptStateSerializer()
    next_plan = PromptStateSerializer()


class PromptActionResponse(serializers.Serializer):
    ok = serializers.BooleanField()
    status = serializers.CharField()


class EngagementStudentRowSerializer(serializers.Serializer):
    registration_number = serializers.CharField()
    student_name = serializers.CharField()
    status = serializers.CharField()
    updated_at = serializers.DateTimeField(required=False)


class EngagementReportResponse(serializers.Serializer):
    """A confirmed/pending tally plus the students behind it."""

    confirmed = serializers.IntegerField(required=False)
    submitted = serializers.IntegerField(required=False)
    pending = serializers.IntegerField()
    students = EngagementStudentRowSerializer(many=True)


class NextPlanRowSerializer(serializers.Serializer):
    registration_number = serializers.CharField()
    student_name = serializers.CharField()
    batch_code = serializers.CharField(allow_null=True)
    planning_another_course = serializers.BooleanField()
    interested_course = serializers.CharField(allow_blank=True)
    expected_timing = serializers.CharField(allow_blank=True)
    goal = serializers.CharField(allow_blank=True)
    preferred_contact_time = serializers.CharField(allow_blank=True, required=False)


@extend_schema(
    request=UtilityLinkSerializer,
    responses={200: UtilityLinkSerializer(many=True), 201: UtilityLinkSerializer},
)
class UtilityLinksView(APIView):
    """Public notice board: anyone reads; MIS posts (optionally with a thumbnail image)."""

    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_permissions(self):
        return [AllowAny()] if self.request.method == "GET" else [UtilityManageRoles()]

    def get(self, request):
        return Response([_link_row(link) for link in UtilityLink.objects.all()[:50]])

    def post(self, request):
        serializer = UtilityLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        link = UtilityLink.objects.create(created_by=request.user, **serializer.validated_data)
        thumb = request.FILES.get("thumbnail")
        if thumb:
            validate_upload(thumb, "image")
            key = f"utility/{storage_name(thumb)}"
            get_storage().save(key, thumb)
            link.thumbnail_key = key
            link.thumbnail_content_type = getattr(thumb, "content_type", "") or ""
            link.save(update_fields=["thumbnail_key", "thumbnail_content_type", "updated_at"])
        record_action(actor=request.user, action="utility_link_added", target=link)
        return Response(_link_row(link), status=201)


@extend_schema(responses={204: None, 404: DetailResponse})
class UtilityLinkDetailView(APIView):
    permission_classes = [UtilityManageRoles]

    def delete(self, request, pk):
        link = UtilityLink.objects.filter(pk=pk).first()
        if not link:
            return Response({"detail": "Link not found."}, status=404)
        record_action(actor=request.user, action="utility_link_removed", target=link)
        link.delete()
        return Response(status=204)


@extend_schema(responses={200: OpenApiTypes.BINARY, 404: DetailResponse})
class UtilityLinkThumbnailView(APIView):
    """Public: serve a utility link's MIS-uploaded thumbnail (the board is public)."""

    permission_classes = [AllowAny]

    def get(self, request, pk):
        link = UtilityLink.objects.filter(pk=pk).first()
        if not link or not link.thumbnail_key:
            return Response({"detail": "No thumbnail."}, status=404)
        return deliver(request, link.thumbnail_key, link.thumbnail_content_type or "image/jpeg")


def _completed_students():
    from batches.models import BatchState

    return User.objects.filter(
        role=Role.STUDENT,
        status=UserStatus.ACTIVE,
        enrollments__batch__state=BatchState.COMPLETED,
    ).distinct()


@extend_schema(responses={200: EngagementMeResponse, 403: DetailResponse})
class EngagementMeView(APIView):
    """Status a student's portal needs to drive the LinkedIn / review / next-plan popups."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != Role.STUDENT:
            return Response({"detail": "Students only."}, status=403)
        follow, _ = LinkedInFollow.objects.get_or_create(student=request.user)
        completed = has_completed_course(request.user)
        review = None
        if completed:
            review, _ = GoogleReview.objects.get_or_create(student=request.user)
        next_plan_done = CourseNextPlan.objects.filter(student=request.user).exists()
        return Response(
            {
                "linkedin": {"status": follow.status, "show": not follow.done},
                "google_review": {
                    "status": review.status if review else None,
                    "show": bool(review and not review.done),
                },
                "next_plan": {"show": completed and not next_plan_done},
            }
        )


@extend_schema(request=None, responses={200: PromptActionResponse, 400: DetailResponse})
class LinkedInActionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        follow, _ = LinkedInFollow.objects.get_or_create(student=request.user)
        action = request.data.get("action")
        mapping = {
            "opened": LinkedInFollow.Status.OPENED,
            "confirmed": LinkedInFollow.Status.CONFIRMED,
            "skipped": LinkedInFollow.Status.SKIPPED,
        }
        if action not in mapping:
            return Response({"detail": "Action must be opened, confirmed or skipped."}, status=400)
        follow.status = mapping[action]
        if action == "confirmed":
            follow.confirmed_at = timezone.now()
        follow.save(update_fields=["status", "confirmed_at", "updated_at"])
        return Response({"ok": True, "status": follow.status})


@extend_schema(request=None, responses={200: PromptActionResponse, 400: DetailResponse})
class GoogleReviewActionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        review, _ = GoogleReview.objects.get_or_create(student=request.user)
        action = request.data.get("action")
        mapping = {
            "opened": GoogleReview.Status.LINK_OPENED,
            "submitted": GoogleReview.Status.SUBMITTED,
            "skipped": GoogleReview.Status.SKIPPED,
        }
        if action not in mapping:
            return Response({"detail": "Action must be opened, submitted or skipped."}, status=400)
        review.status = mapping[action]
        if action == "submitted":
            review.submitted_at = timezone.now()
        review.save(update_fields=["status", "submitted_at", "updated_at"])
        return Response({"ok": True, "status": review.status})


@extend_schema(request=None, responses={200: OkResponse, 400: DetailResponse})
class NextPlanView(APIView):
    """Student submits their end-of-course next plan; Admin is notified."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from batches.models import Batch

        batch = None
        if request.data.get("batch"):
            batch = Batch.objects.filter(id=request.data["batch"]).first()
        plan, _ = CourseNextPlan.objects.update_or_create(
            student=request.user,
            batch=batch,
            defaults={
                "planning_another_course": bool(request.data.get("planning_another_course")),
                "interested_course": request.data.get("interested_course", ""),
                "expected_timing": request.data.get("expected_timing", ""),
                "goal": request.data.get("goal", ""),
                "preferred_contact_time": request.data.get("preferred_contact_time", ""),
                "notes": request.data.get("notes", ""),
            },
        )
        notify_many(
            admins_and_mis(),
            "next_plan_submitted",
            f"{request.user.full_name or request.user.username} submitted their next-course plan.",
            subject="Next-plan submitted",
            channels=("in_app",),
        )
        record_action(actor=request.user, action="next_plan_submitted", target=plan)
        return Response({"ok": True})


@extend_schema(responses=EngagementReportResponse)
class LinkedInReportView(APIView):
    permission_classes = [ReportRoles]

    def get(self, request):
        rows = LinkedInFollow.objects.select_related("student")
        batch_id = request.query_params.get("batch")
        if batch_id:
            rows = rows.filter(student__enrollments__batch_id=batch_id).distinct()
        confirmed = sum(1 for r in rows if r.status == LinkedInFollow.Status.CONFIRMED)
        return Response(
            {
                "confirmed": confirmed,
                "pending": rows.count() - confirmed,
                "students": [
                    {
                        "registration_number": r.student.username,
                        "student_name": r.student.full_name or r.student.username,
                        "status": r.status,
                        "reminder_count": r.reminder_count,
                    }
                    for r in rows
                ],
            }
        )


@extend_schema(responses=EngagementReportResponse)
class GoogleReviewReportView(APIView):
    permission_classes = [ReportRoles]

    def get(self, request):
        rows = GoogleReview.objects.select_related("student")
        batch_id = request.query_params.get("batch")
        if batch_id:
            rows = rows.filter(student__enrollments__batch_id=batch_id).distinct()
        submitted = sum(1 for r in rows if r.status == GoogleReview.Status.SUBMITTED)
        return Response(
            {
                "submitted": submitted,
                "pending": rows.count() - submitted,
                "students": [
                    {
                        "registration_number": r.student.username,
                        "student_name": r.student.full_name or r.student.username,
                        "status": r.status,
                        "reminder_count": r.reminder_count,
                    }
                    for r in rows
                ],
            }
        )


@extend_schema(responses=NextPlanRowSerializer(many=True))
class NextPlanListView(APIView):
    permission_classes = [ReportRoles]

    def get(self, request):
        plans = CourseNextPlan.objects.select_related("student", "batch").order_by("-created_at")
        batch_id = request.query_params.get("batch")
        if batch_id:
            plans = plans.filter(batch_id=batch_id)
        return Response(
            [
                {
                    "registration_number": p.student.username,
                    "student_name": p.student.full_name or p.student.username,
                    "batch_code": p.batch.code if p.batch else None,
                    "planning_another_course": p.planning_another_course,
                    "interested_course": p.interested_course,
                    "expected_timing": p.expected_timing,
                    "goal": p.goal,
                    "preferred_contact_time": p.preferred_contact_time,
                    "notes": p.notes,
                    "submitted_at": p.created_at,
                }
                for p in plans
            ]
        )
