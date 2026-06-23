"""The seven platform roles."""

from django.db import models


class Role(models.TextChoices):
    SUPER_ADMIN = "super_admin", "Super Admin"
    ADMIN = "admin", "Admin"
    MIS = "mis", "MIS Executive"
    COUNSELOR = "counselor", "Counselor"
    TECH_SUPPORT = "tech_support", "Tech Support"
    FACULTY = "faculty", "Faculty"
    STUDENT = "student", "Student"


# Roles that sign in through a staff login page (everyone except Student).
STAFF_ROLES = frozenset(
    {
        Role.SUPER_ADMIN,
        Role.ADMIN,
        Role.MIS,
        Role.COUNSELOR,
        Role.TECH_SUPPORT,
        Role.FACULTY,
    }
)
