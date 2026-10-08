from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class PatientDoctorMapping(TimeStampedModel):
    """Assignment of a doctor to a patient. A doctor can be assigned to a patient once."""

    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE, related_name="doctor_assignments"
    )
    doctor = models.ForeignKey(
        "doctors.Doctor", on_delete=models.CASCADE, related_name="patient_assignments"
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "patient-doctor mapping"
        constraints = [
            models.UniqueConstraint(fields=["patient", "doctor"], name="unique_patient_doctor"),
        ]

    def __str__(self):
        return f"{self.patient} -> {self.doctor}"
