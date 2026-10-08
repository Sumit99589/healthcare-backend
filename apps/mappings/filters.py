import django_filters

from .models import PatientDoctorMapping


class MappingFilter(django_filters.FilterSet):
    # Plain ID filters: a ModelChoiceFilter would validate against every patient in the
    # database and reveal whether another user's patient ID exists.
    patient = django_filters.NumberFilter(field_name="patient_id")
    doctor = django_filters.NumberFilter(field_name="doctor_id")

    class Meta:
        model = PatientDoctorMapping
        fields = ["patient", "doctor"]
