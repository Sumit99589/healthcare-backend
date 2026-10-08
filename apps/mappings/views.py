from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import mixins, viewsets
from rest_framework.response import Response

from apps.patients.models import Patient

from .filters import MappingFilter
from .models import PatientDoctorMapping
from .serializers import MappingReadSerializer, MappingSerializer, PatientDoctorsSerializer


def _id_param(description):
    return OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH, description=description)


@extend_schema(tags=["Patient-Doctor Mappings"])
class MappingViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Assign doctors to patients.

    Mappings are visible to (and removable by) the owner of the patient only. Following
    the assignment spec, `/api/mappings/<id>/` means a *patient* ID for GET and a
    *mapping* ID for DELETE.
    """

    serializer_class = MappingSerializer
    lookup_url_kwarg = "id"
    filterset_class = MappingFilter
    ordering_fields = ["created_at"]
    ordering = ["-created_at", "-id"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # OpenAPI schema generation
            return PatientDoctorMapping.objects.none()
        return PatientDoctorMapping.objects.filter(
            patient__created_by=self.request.user
        ).select_related("patient", "doctor")

    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)

    @extend_schema(summary="Assign a doctor to a patient", responses={201: MappingReadSerializer})
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="List all patient-doctor mappings for your patients",
        responses=MappingReadSerializer(many=True),
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Get all doctors assigned to a patient",
        parameters=[_id_param("ID of the patient")],
        responses={
            200: PatientDoctorsSerializer,
            404: OpenApiResponse(description="No such patient"),
        },
        filters=False,
    )
    def patient_doctors(self, request, id=None):
        patient = get_object_or_404(Patient, pk=id, created_by=request.user)
        assignments = (
            PatientDoctorMapping.objects.filter(patient=patient)
            .select_related("doctor")
            .order_by("created_at", "id")
        )
        data = {"patient": patient, "count": len(assignments), "doctors": assignments}
        return Response(PatientDoctorsSerializer(data).data)

    @extend_schema(
        summary="Remove a doctor from a patient",
        parameters=[_id_param("ID of the mapping (see `id` / `mapping_id` in responses)")],
        responses={204: None, 404: OpenApiResponse(description="No such mapping")},
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
