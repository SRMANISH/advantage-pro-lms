from django.urls import path

from .views import UpsellView

urlpatterns = [
    path("upsell/", UpsellView.as_view(), name="upsell"),
]
