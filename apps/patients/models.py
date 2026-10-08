from datetime import date

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel
from apps.common.validators import phone_validator


class Patient(TimeStampedModel):
    """A patient record. Patients are private to the user who created them."""

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"

    class BloodGroup(models.TextChoices):
        A_POS = "A+", "A+"
        A_NEG = "A-", "A-"
        B_POS = "B+", "B+"
        B_NEG = "B-", "B-"
        AB_POS = "AB+", "AB+"
        AB_NEG = "AB-", "AB-"
        O_POS = "O+", "O+"
        O_NEG = "O-", "O-"

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="patients"
    )
    name = models.CharField(max_length=150)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=Gender.choices)
    blood_group = models.CharField(max_length=3, choices=BloodGroup.choices, blank=True)
    phone = models.CharField(max_length=20, validators=[phone_validator])
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    medical_history = models.TextField(blank=True)
    allergies = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["created_by", "name"], name="patient_owner_name_idx")]

    def __str__(self):
        return self.name

    @property
    def age(self):
        today = date.today()
        born = self.date_of_birth
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
