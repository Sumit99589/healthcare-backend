from django.contrib import admin

from .models import Doctor


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "specialization", "license_number", "email", "is_available"]
    list_filter = ["specialization", "is_available"]
    search_fields = ["name", "email", "license_number", "hospital"]
    list_select_related = ["created_by"]
    raw_id_fields = ["created_by"]
