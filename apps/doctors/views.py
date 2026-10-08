from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.common.permissions import IsCreatorOrReadOnly

from .models import Doctor
from .serializers import DoctorSerializer


@extend_schema_view(
    list=extend_schema(summary="List all doctors"),
    create=extend_schema(summary="Add a new doctor"),
    retrieve=extend_schema(summary="Get a doctor"),
    update=extend_schema(summary="Update a doctor (creator only)"),
    partial_update=extend_schema(summary="Partially update a doctor (creator only)"),
    destroy=extend_schema(summary="Delete a doctor (creator only)"),
)
@extend_schema(tags=["Doctors"])
class DoctorViewSet(viewsets.ModelViewSet):
    """
    Doctors form a shared directory: any authenticated user can list and view them,
    but only the user who added a doctor can update or delete that record.
    """

    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [IsAuthenticated, IsCreatorOrReadOnly]
    filterset_fields = ["specialization", "is_available"]
    search_fields = ["name", "email", "hospital", "license_number"]
    ordering_fields = ["name", "years_of_experience", "created_at"]
    ordering = ["name", "id"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
