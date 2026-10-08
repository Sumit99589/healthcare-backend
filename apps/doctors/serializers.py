import re

from rest_framework import serializers

from .models import Doctor

DR_PREFIX = re.compile(r"^dr\.?\s+", re.IGNORECASE)


class DoctorSerializer(serializers.ModelSerializer):
    specialization_display = serializers.CharField(
        source="get_specialization_display", read_only=True
    )
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Doctor
        fields = [
            "id",
            "name",
            "specialization",
            "specialization_display",
            "license_number",
            "email",
            "phone",
            "years_of_experience",
            "hospital",
            "is_available",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]
        extra_kwargs = {
            # Uniqueness is checked after normalisation in validate_<field> below, so the
            # automatic (case-sensitive) UniqueValidators are switched off.
            "email": {"validators": []},
            "license_number": {"validators": []},
        }

    def _others(self):
        qs = Doctor.objects.all()
        return qs.exclude(pk=self.instance.pk) if self.instance else qs

    def validate_name(self, value):
        # Store the bare name; "Dr." is added when the doctor is displayed.
        value = DR_PREFIX.sub("", value.strip())
        if not value:
            raise serializers.ValidationError("Name cannot be blank.")
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if self._others().filter(email__iexact=value).exists():
            raise serializers.ValidationError("A doctor with this email already exists.")
        return value

    def validate_license_number(self, value):
        value = value.strip().upper()
        if not value:
            raise serializers.ValidationError("License number cannot be blank.")
        if self._others().filter(license_number__iexact=value).exists():
            raise serializers.ValidationError("A doctor with this license number already exists.")
        return value


class DoctorSummarySerializer(serializers.ModelSerializer):
    """Compact representation used when a doctor is embedded in another resource."""

    specialization_display = serializers.CharField(
        source="get_specialization_display", read_only=True
    )

    class Meta:
        model = Doctor
        fields = ["id", "name", "specialization", "specialization_display", "hospital"]
        read_only_fields = fields
