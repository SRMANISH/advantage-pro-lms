"""In-video upsell: a truthful next-course prompt using the student's own situation.

Per the plan, messaging stays honest — it uses the student's employment as gentle
social proof and points to real courses we offer; it never fabricates outcomes.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from batches.models import Course
from core.roles import Role
from enrollments.models import Enrollment


@extend_schema(responses=OpenApiTypes.OBJECT)
class UpsellView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != Role.STUDENT:
            return Response({"prompt": None})

        enrollments = list(Enrollment.objects.filter(student=user).select_related("batch"))
        company = next((e.employment_company for e in enrollments if e.employment_company), "")
        enrolled_course_ids = [e.batch.course_id for e in enrollments]
        next_courses = list(Course.objects.exclude(id__in=enrolled_course_ids)[:3])
        if not next_courses:
            return Response({"prompt": None})

        if company:
            message = (
                f"Colleagues at {company} have advanced with Advantage Pro — "
                "keep your momentum going with your next course."
            )
        else:
            message = "Ready for the next step? Advantage Pro offers more courses to help you grow."

        return Response(
            {
                "prompt": {
                    "message": message,
                    "courses": [{"code": c.code, "name": c.name} for c in next_courses],
                }
            }
        )
