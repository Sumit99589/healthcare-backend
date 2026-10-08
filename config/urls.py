from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from apps.common.views import HealthCheckView

api_patterns = [
    path("auth/", include("apps.accounts.urls")),
    path("patients/", include("apps.patients.urls")),
    path("doctors/", include("apps.doctors.urls")),
    path("mappings/", include("apps.mappings.urls")),
    path("health/", HealthCheckView.as_view(), name="health"),
    # OpenAPI schema + interactive documentation
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="swagger-ui", permanent=False)),
    path("admin/", admin.site.urls),
    path("api/", include(api_patterns)),
]

handler404 = "apps.common.views.json_not_found"
handler500 = "apps.common.views.json_server_error"
