from rest_framework import serializers

from apps.common.exceptions import Conflict
from apps.doctors.models import Doctor
from apps.doctors.serializers import DoctorSerializer, DoctorSummarySerializer
from apps.patients.models import Patient
from apps.patients.serializers import PatientSummarySerializer

from .models import PatientDoctorMapping


class OwnPatientField(serializers.PrimaryKeyRelatedField):
    """Accepts only the IDs of patients that belong to the requesting user."""

    default_error_messages = {
        "does_not_exist": "Patient {pk_value} does not exist.",
    }

    def get_queryset(self):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return Patient.objects.none()
        return Patient.objects.filter(created_by=request.user)


class MappingSerializer(serializers.ModelSerializer):
    """
    Write with IDs (`{"patient": 1, "doctor": 2}`); read back with the patient and the
    doctor embedded, so the client does not need follow-up requests.
    """

    patient = OwnPatientField()
    doctor = serializers.PrimaryKeyRelatedField(
        queryset=Doctor.objects.all(),
        error_messages={"does_not_exist": "Doctor {pk_value} does not exist."},
    )
    assigned_at = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = PatientDoctorMapping
        fields = ["id", "patient", "doctor", "notes", "assigned_at"]
        read_only_fields = ["id", "assigned_at"]
        # The duplicate check is done in validate() so it can answer 409 Conflict.
        validators = []

    def validate_doctor(self, doctor):
        if not doctor.is_available:
            raise serializers.ValidationError(
                "This doctor is not currently accepting new patients."
            )
        return doctor

    def validate(self, attrs):
        if PatientDoctorMapping.objects.filter(
            patient=attrs["patient"], doctor=attrs["doctor"]
        ).exists():
            raise Conflict("This doctor is already assigned to this patient.")
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["patient"] = PatientSummarySerializer(instance.patient).data
        data["doctor"] = DoctorSummarySerializer(instance.doctor).data
        return data


class MappingReadSerializer(serializers.ModelSerializer):
    """Read-only twin of MappingSerializer, used to describe responses in the API schema."""

    patient = PatientSummarySerializer()
    doctor = DoctorSummarySerializer()
    assigned_at = serializers.DateTimeField(source="created_at")

    class Meta:
        model = PatientDoctorMapping
        fields = ["id", "patient", "doctor", "notes", "assigned_at"]
        read_only_fields = fields


class AssignedDoctorSerializer(serializers.ModelSerializer):
    """One entry of `GET /api/mappings/<patient_id>/`: a doctor plus the assignment info."""

    mapping_id = serializers.IntegerField(source="id")
    assigned_at = serializers.DateTimeField(source="created_at")
    doctor = DoctorSerializer()

    class Meta:
        model = PatientDoctorMapping
        fields = ["mapping_id", "assigned_at", "notes", "doctor"]
        read_only_fields = fields


class PatientDoctorsSerializer(serializers.Serializer):
    patient = PatientSummarySerializer()
    count = serializers.IntegerField()
    doctors = AssignedDoctorSerializer(many=True)
