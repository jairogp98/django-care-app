from rest_framework.routers import DefaultRouter
from clients.viewsets.client_viewset import ClientViewSet

router = DefaultRouter()
router.register("clients", ClientViewSet, basename="client")

urlpatterns = router.urls
