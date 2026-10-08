from rest_framework.routers import DefaultRouter

from .views import PatientViewSet

app_name = "patients"

router = DefaultRouter()
router.include_root_view = False
router.register("", PatientViewSet, basename="patient")

urlpatterns = router.urls
