from rest_framework.routers import DefaultRouter

from .views import LiveClassViewSet

router = DefaultRouter()
router.register("liveclasses", LiveClassViewSet, basename="liveclass")

urlpatterns = router.urls
