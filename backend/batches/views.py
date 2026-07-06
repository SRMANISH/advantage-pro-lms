"""Course & batch APIs with role-scoped access and a guarded lifecycle."""

from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from accounts.models import User, UserStatus
from audit.services import record_action
from core.permissions import MatrixPermission, has_any_role
from core.permissions_matrix import Action
from core.roles import Role
from core.utils import get_client_ip

from .models import ALLOWED_TRANSITIONS, Batch, BatchState, Course
from .serializers import (
    BatchSerializer,
    CourseSerializer,
    FacultyAssignSerializer,
    FacultyBriefSerializer,
    TransitionSerializer,
)

# Counselor/Tech Support/Student reach batch data through their own modules later.
StaffOrFaculty = has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS, Role.FACULTY)


class CertificatesExistError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = (
        "This batch has issued certificates and cannot be deleted — those are legal "
        "academic records. Archive the batch instead of deleting it."
    )
    default_code = "certificates_exist"


class FacultyListView(ListAPIView):
    """Active faculty, for the assign-faculty dropdown."""

    serializer_class = FacultyBriefSerializer
    permission_classes = [StaffOrFaculty]
    queryset = User.objects.filter(role=Role.FACULTY, status=UserStatus.ACTIVE).order_by(
        "full_name"
    )


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [StaffOrFaculty, MatrixPermission]

    _ACTIONS = {
        "create": Action.CREATE_EDIT_BATCH,
        "update": Action.CREATE_EDIT_BATCH,
        "partial_update": Action.CREATE_EDIT_BATCH,
        "destroy": Action.CREATE_EDIT_BATCH,
    }

    def get_required_action(self):
        return self._ACTIONS.get(self.action)

    def perform_create(self, serializer):
        course = serializer.save()
        record_action(
            actor=self.request.user,
            action="course_created",
            target=course,
            ip_address=get_client_ip(self.request),
        )


class BatchViewSet(viewsets.ModelViewSet):
    serializer_class = BatchSerializer
    permission_classes = [StaffOrFaculty, MatrixPermission]

    _ACTIONS = {
        "create": Action.CREATE_EDIT_BATCH,
        "update": Action.CREATE_EDIT_BATCH,
        "partial_update": Action.CREATE_EDIT_BATCH,
        "destroy": Action.DELETE_BATCH,
        "assign_faculty": Action.ASSIGN_FACULTY,
        "transition": Action.CREATE_EDIT_BATCH,
    }

    def get_required_action(self):
        return self._ACTIONS.get(self.action)

    def get_queryset(self):
        user = self.request.user
        qs = Batch.objects.select_related("course").prefetch_related("faculty")
        if user.role in {Role.SUPER_ADMIN, Role.ADMIN, Role.MIS}:
            return qs
        if user.role == Role.FACULTY:
            return qs.filter(faculty=user)
        return qs.none()

    def perform_create(self, serializer):
        batch = serializer.save()
        record_action(
            actor=self.request.user,
            action="batch_created",
            target=batch,
            ip_address=get_client_ip(self.request),
        )

    def perform_destroy(self, instance):
        from certification.models import Certificate

        if Certificate.objects.filter(enrollment__batch=instance).exists():
            raise CertificatesExistError()
        record_action(
            actor=self.request.user,
            action="batch_deleted",
            target=instance,
            ip_address=get_client_ip(self.request),
        )
        instance.delete()

    @action(detail=True, methods=["post"], url_path="assign-faculty")
    def assign_faculty(self, request, pk=None):
        # get_object() is queryset-scoped: faculty can only assign within their own batches.
        batch = self.get_object()
        serializer = FacultyAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        faculty = serializer.validated_data["faculty_ids"]
        batch.faculty.add(*faculty)
        record_action(
            actor=request.user,
            action="batch_faculty_assigned",
            target=batch,
            metadata={"faculty_ids": [str(f.id) for f in faculty]},
            ip_address=get_client_ip(request),
        )
        return Response(self.get_serializer(batch).data)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        batch = self.get_object()
        serializer = TransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        to_state = serializer.validated_data["to_state"]
        if to_state not in ALLOWED_TRANSITIONS[batch.state]:
            return Response(
                {"detail": f"Cannot move a batch from {batch.state} to {to_state}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            batch.state = to_state
            batch.save(update_fields=["state", "updated_at"])
            # Course-end video closure (Admin completing the batch — matrix allows AD + MIS).
            if to_state == BatchState.COMPLETED:
                from content.models import VideoAccessRevocation

                VideoAccessRevocation.objects.get_or_create(
                    student=None,
                    batch=batch,
                    defaults={"revoked_by": request.user, "reason": "course-end closure"},
                )
            record_action(
                actor=request.user,
                action="batch_transitioned",
                target=batch,
                metadata={"to_state": to_state},
                ip_address=get_client_ip(request),
            )
        return Response(self.get_serializer(batch).data)
