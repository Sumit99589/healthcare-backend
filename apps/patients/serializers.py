from datetime import date

from rest_framework import serializers

from .models import Patient

MAX_AGE_YEARS = 150


class PatientSerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(read_only=True)

    class Meta:
        model = Patient
        fields = [
            "id",
            "name",
            "date_of_birth",
            "age",
            "gender",
            "blood_group",
            "phone",
            "email",
            "address",
            "medical_history",
            "allergies",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "age", "created_at", "updated_at"]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name cannot be blank.")
        return value

    def validate_date_of_birth(self, value):
        today = date.today()
        if value > today:
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        if today.year - value.year > MAX_AGE_YEARS:
            raise serializers.ValidationError(
                f"Date of birth cannot be more than {MAX_AGE_YEARS} years ago."
            )
        return value

    def validate_email(self, value):
        return value.strip().lower()


class PatientSummarySerializer(serializers.ModelSerializer):
    """Compact representation used when a patient is embedded in another resource."""

    class Meta:
        model = Patient
        fields = ["id", "name", "date_of_birth", "gender"]
        read_only_fields = fields
