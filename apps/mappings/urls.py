from django.urls import path

from .views import MappingViewSet

app_name = "mappings"

mapping_list = MappingViewSet.as_view({"get": "list", "post": "create"})
# Per the spec, GET takes a patient ID and DELETE takes a mapping ID on the same URL.
mapping_detail = MappingViewSet.as_view({"get": "patient_doctors", "delete": "destroy"})

urlpatterns = [
    path("", mapping_list, name="mapping-list"),
    path("<int:id>/", mapping_detail, name="mapping-detail"),
]
