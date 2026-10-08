from django.contrib import admin

from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "gender", "date_of_birth", "phone", "created_by", "created_at"]
    list_filter = ["gender", "blood_group"]
    search_fields = ["name", "phone", "email"]
    list_select_related = ["created_by"]
    raw_id_fields = ["created_by"]
