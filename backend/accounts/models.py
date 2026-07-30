"""Custom user model.

Login identifier is ``username`` (a student's registration number, or a staff login id),
not email — because a person who enrols in a different course gets a separate student
record, so email is intentionally NOT unique. Role-bound login pages and the RBAC matrix
build on the ``role`` field.
"""

import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from core.models import TimeStampedModel
from core.roles import Role

from .managers import UserManager


class UserStatus(models.TextChoices):
    PENDING = "pending", "Pending setup"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    DEACTIVATED = "deactivated", "Deactivated"


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField("login id", max_length=150, unique=True)
    email = models.EmailField(blank=True)  # not unique by design (see module docstring)
    phone = models.CharField(max_length=20, blank=True)
    full_name = models.CharField(max_length=255, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    status = models.CharField(max_length=20, choices=UserStatus.choices, default=UserStatus.PENDING)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["role"]

    class Meta:
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self) -> str:
        return f"{self.username} ({self.get_role_display()})"


class SetupToken(TimeStampedModel):
    """A 48h single-use link for two-step account setup."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="setup_token")
    token = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    # How many email OTPs this link has sent. Opening the setup page sends one, and each
    # retry sends another, so this is a total-sends cap (not a resend cap like the reset
    # flow's ``resend_count``, where the first send happens outside the counter).
    send_count = models.PositiveSmallIntegerField(default=0)

    def __str__(self) -> str:
        return f"setup<{self.user_id}>"


class PasswordResetToken(TimeStampedModel):
    """A short-lived token for the two-step (email + phone OTP) forgot-password flow."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reset_tokens")
    token = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    resend_count = models.PositiveSmallIntegerField(default=0)

    def __str__(self) -> str:
        return f"reset<{self.user_id}>"


class OTPCode(TimeStampedModel):
    class Purpose(models.TextChoices):
        EMAIL = "email", "Email"
        PHONE = "phone", "Phone"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otp_codes")
    purpose = models.CharField(max_length=10, choices=Purpose.choices)
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["user", "purpose"])]


class DeviceBinding(TimeStampedModel):
    """A student is bound to the device they first sign in from."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="device_binding")
    device_id = models.CharField(max_length=64)

    def __str__(self) -> str:
        return f"device<{self.user_id}>"


class DeviceChangeRequest(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="device_change_requests")
    new_device_id = models.CharField(max_length=64)
    old_device_id = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    # Context captured when the request was raised: whether a live class was in session
    # (routes the approval to Faculty during class, MIS outside class).
    during_class = models.BooleanField(default=False)
    class_context = models.CharField(max_length=200, blank=True)
    decided_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    approver_role = models.CharField(max_length=20, blank=True)
    approval_reason = models.CharField(max_length=255, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"])]


class TOTPDevice(TimeStampedModel):
    """One authenticator-app secret per account — optional, staff-only by convention.

    ``confirmed`` only flips to True after one correct code during enrollment, so a
    mistyped or abandoned enrollment can never silently lock the account's login (an
    unconfirmed device is never consulted at login time).
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="totp_device")
    secret = models.CharField(max_length=32)
    confirmed = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"totp<{self.user_id}>"


class FacultyProfile(TimeStampedModel):
    """Skills and certifications a faculty maintains in their own portal.

    Surfaced wherever a faculty is chosen for a batch, so the right person can be matched
    to the right course (updated procedure).
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="faculty_profile")
    skills = models.TextField(blank=True)  # comma/newline-separated, e.g. "React, Django"
    certifications = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"faculty-profile<{self.user_id}>"
