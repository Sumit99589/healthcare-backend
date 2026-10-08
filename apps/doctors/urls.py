from rest_framework.routers import DefaultRouter

from .views import DoctorViewSet

app_name = "doctors"

router = DefaultRouter()
router.include_root_view = False
router.register("", DoctorViewSet, basename="doctor")

urlpatterns = router.urls
