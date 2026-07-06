from django.urls import path

from .views import MatrixActionView, MatrixView

urlpatterns = [
    path("permissions/matrix/", MatrixView.as_view(), name="permission-matrix"),
    path(
        "permissions/matrix/<str:action>/",
        MatrixActionView.as_view(),
        name="permission-matrix-action",
    ),
]
