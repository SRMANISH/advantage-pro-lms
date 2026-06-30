from typing import TYPE_CHECKING

from django.contrib.auth.models import BaseUserManager

from core.roles import Role

if TYPE_CHECKING:
    from .models import User  # noqa: F401  (used in the BaseUserManager["User"] generic)


class UserManager(BaseUserManager["User"]):
    """Manager for the username-keyed custom user."""

    use_in_migrations = True

    def create_user(self, username: str, password: str | None = None, **extra):
        if not username:
            raise ValueError("Users must have a username (login id).")
        user = self.model(username=username, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username: str, password: str | None = None, **extra):
        extra.setdefault("role", Role.SUPER_ADMIN)
        extra.setdefault("status", "active")
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        if extra.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(username, password, **extra)
