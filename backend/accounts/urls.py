from django.urls import path

from .views import (
    ChangePasswordView,
    CSRFView,
    DeviceRequestDecideView,
    DeviceRequestListView,
    ForgotPasswordCompleteView,
    ForgotPasswordResendView,
    ForgotPasswordStartView,
    ForgotPasswordVerifyEmailView,
    ForgotPasswordVerifyPhoneView,
    LoginView,
    LogoutView,
    MeView,
    SetupCompleteView,
    SetupResendView,
    SetupStartView,
    SetupVerifyEmailView,
    SetupVerifyPhoneView,
)

urlpatterns = [
    path("csrf/", CSRFView.as_view(), name="auth-csrf"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("setup/start/", SetupStartView.as_view(), name="setup-start"),
    path("setup/verify-email/", SetupVerifyEmailView.as_view(), name="setup-verify-email"),
    path("setup/verify-phone/", SetupVerifyPhoneView.as_view(), name="setup-verify-phone"),
    path("setup/complete/", SetupCompleteView.as_view(), name="setup-complete"),
    path("setup/resend/", SetupResendView.as_view(), name="setup-resend"),
    path("password/forgot/", ForgotPasswordStartView.as_view(), name="password-forgot"),
    path(
        "password/verify-email/",
        ForgotPasswordVerifyEmailView.as_view(),
        name="password-verify-email",
    ),
    path(
        "password/verify-phone/",
        ForgotPasswordVerifyPhoneView.as_view(),
        name="password-verify-phone",
    ),
    path("password/reset/", ForgotPasswordCompleteView.as_view(), name="password-reset"),
    path("password/resend/", ForgotPasswordResendView.as_view(), name="password-resend"),
    path("password/change/", ChangePasswordView.as_view(), name="password-change"),
    path("devices/requests/", DeviceRequestListView.as_view(), name="device-requests"),
    path(
        "devices/requests/<uuid:pk>/decide/",
        DeviceRequestDecideView.as_view(),
        name="device-decide",
    ),
]
