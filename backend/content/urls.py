from rest_framework.routers import DefaultRouter

from .views import MaterialViewSet, VideoViewSet

router = DefaultRouter()
router.register("videos", VideoViewSet, basename="video")
router.register("materials", MaterialViewSet, basename="material")

urlpatterns = router.urls
