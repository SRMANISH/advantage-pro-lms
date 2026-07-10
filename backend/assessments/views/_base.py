"""Shared bits for the assessments view modules."""

from core.permissions import has_any_role
from core.roles import Role

AssessmentRoles = has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS, Role.FACULTY, Role.STUDENT)
