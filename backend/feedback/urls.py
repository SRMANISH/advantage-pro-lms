from django.urls import path

from .views import FeedbackCreateView, FeedbackListView

urlpatterns = [
    path("feedback/", FeedbackCreateView.as_view(), name="feedback-create"),
    path("feedback/inbox/", FeedbackListView.as_view(), name="feedback-inbox"),
]
