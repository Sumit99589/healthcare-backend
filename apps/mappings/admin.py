from django.contrib import admin

from .models import PatientDoctorMapping


@admin.register(PatientDoctorMapping)
class PatientDoctorMappingAdmin(admin.ModelAdmin):
    list_display = ["id", "patient", "doctor", "assigned_by", "created_at"]
    search_fields = ["patient__name", "doctor__name"]
    list_select_related = ["patient", "doctor", "assigned_by"]
    raw_id_fields = ["patient", "doctor", "assigned_by"]
