"""Account views, split by concern (auth, setup, password, staff, devices).

Everything is re-exported here so ``from .views import X`` (urls.py) and any external
``accounts.views.X`` reference keep working unchanged.
"""

from .auth import CSRFView, LoginView, LogoutView, MeView
from .devices import DeviceRequestDecideView, DeviceRequestListView
from .faculty import FacultyProfileView
from .password import (
    ChangePasswordView,
    ForgotPasswordCompleteView,
    ForgotPasswordResendView,
    ForgotPasswordStartView,
    ForgotPasswordVerifyEmailView,
    ForgotPasswordVerifyPhoneView,
)
from .setup import (
    SetupCompleteView,
    SetupResendView,
    SetupStartView,
    SetupVerifyEmailView,
    SetupVerifyPhoneView,
)
from .staff import StaffAccountsView, UserRoleView, UserStatusView
from .totp import (
    TOTPConfirmView,
    TOTPDisableView,
    TOTPEnrollView,
    TOTPResetView,
    TOTPStatusView,
)

__all__ = [
    "CSRFView",
    "LoginView",
    "LogoutView",
    "MeView",
    "SetupStartView",
    "SetupVerifyEmailView",
    "SetupVerifyPhoneView",
    "SetupCompleteView",
    "SetupResendView",
    "ForgotPasswordStartView",
    "ForgotPasswordVerifyEmailView",
    "ForgotPasswordVerifyPhoneView",
    "ForgotPasswordCompleteView",
    "ForgotPasswordResendView",
    "ChangePasswordView",
    "StaffAccountsView",
    "UserStatusView",
    "UserRoleView",
    "DeviceRequestListView",
    "DeviceRequestDecideView",
    "FacultyProfileView",
    "TOTPStatusView",
    "TOTPEnrollView",
    "TOTPConfirmView",
    "TOTPDisableView",
    "TOTPResetView",
]
