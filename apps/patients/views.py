from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets

from .models import Patient
from .serializers import PatientSerializer


@extend_schema_view(
    list=extend_schema(summary="List the patients you created"),
    create=extend_schema(summary="Add a new patient"),
    retrieve=extend_schema(summary="Get a patient"),
    update=extend_schema(summary="Update a patient"),
    partial_update=extend_schema(summary="Partially update a patient"),
    destroy=extend_schema(summary="Delete a patient"),
)
@extend_schema(tags=["Patients"])
class PatientViewSet(viewsets.ModelViewSet):
    """
    CRUD for patients. Every query is scoped to the authenticated user, so another
    user's patient is indistinguishable from one that does not exist (404).
    """

    serializer_class = PatientSerializer
    filterset_fields = ["gender", "blood_group"]
    search_fields = ["name", "phone", "email"]
    ordering_fields = ["name", "date_of_birth", "created_at", "updated_at"]
    ordering = ["-created_at", "-id"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # OpenAPI schema generation
            return Patient.objects.none()
        return Patient.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
