from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models.functions import Lower

from apps.common.models import TimeStampedModel
from apps.common.validators import phone_validator


class Doctor(TimeStampedModel):
    """
    A doctor in the shared directory. Every authenticated user can see all doctors (so
    they can assign them to patients); only the creator can edit or delete one.
    """

    class Specialization(models.TextChoices):
        GENERAL_PRACTICE = "general_practice", "General Practice"
        CARDIOLOGY = "cardiology", "Cardiology"
        DERMATOLOGY = "dermatology", "Dermatology"
        ENDOCRINOLOGY = "endocrinology", "Endocrinology"
        ENT = "ent", "ENT (Otorhinolaryngology)"
        GASTROENTEROLOGY = "gastroenterology", "Gastroenterology"
        GYNECOLOGY = "gynecology", "Gynecology & Obstetrics"
        NEPHROLOGY = "nephrology", "Nephrology"
        NEUROLOGY = "neurology", "Neurology"
        ONCOLOGY = "oncology", "Oncology"
        OPHTHALMOLOGY = "ophthalmology", "Ophthalmology"
        ORTHOPEDICS = "orthopedics", "Orthopedics"
        PEDIATRICS = "pediatrics", "Pediatrics"
        PSYCHIATRY = "psychiatry", "Psychiatry"
        PULMONOLOGY = "pulmonology", "Pulmonology"
        RADIOLOGY = "radiology", "Radiology"
        UROLOGY = "urology", "Urology"
        OTHER = "other", "Other"

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="doctors",
    )
    name = models.CharField(max_length=150)
    specialization = models.CharField(max_length=32, choices=Specialization.choices)
    license_number = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, validators=[phone_validator])
    years_of_experience = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(70)]
    )
    hospital = models.CharField(max_length=200, blank=True)
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(Lower("email"), name="doctor_email_ci_unique"),
            models.CheckConstraint(
                condition=models.Q(years_of_experience__lte=70),
                name="doctor_experience_lte_70",
            ),
        ]
        indexes = [models.Index(fields=["specialization"], name="doctor_specialization_idx")]

    def __str__(self):
        return f"Dr. {self.name} ({self.get_specialization_display()})"
