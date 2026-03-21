from rest_framework.routers import DefaultRouter
from visits.viewsets.viewsets import VisitViewSet

router = DefaultRouter()
router.register("visits", VisitViewSet, basename="visit")

urlpatterns = router.urls
