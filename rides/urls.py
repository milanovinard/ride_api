from rest_framework.routers import DefaultRouter

from .views import RideEventViewSet, RideViewSet

router = DefaultRouter()
router.register("rides", RideViewSet, basename="ride")
router.register("ride-events", RideEventViewSet, basename="rideevent")

urlpatterns = router.urls
