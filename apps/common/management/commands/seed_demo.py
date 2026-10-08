from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.doctors.models import Doctor
from apps.mappings.models import PatientDoctorMapping
from apps.patients.models import Patient

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "DemoPass!2026"

DOCTORS = [
    ("Meera Iyer", "cardiology", "MCI-10231", 14, "Apollo Hospitals"),
    ("Arvind Rao", "neurology", "MCI-20877", 21, "AIIMS Delhi"),
    ("Fatima Sheikh", "pediatrics", "MCI-30452", 9, "Rainbow Children's Hospital"),
    ("Kunal Bose", "orthopedics", "MCI-41190", 17, "Fortis Hospital"),
    ("Nisha Kapoor", "dermatology", "MCI-52634", 6, "Max Healthcare"),
]

PATIENTS = [
    ("Ravi Kumar", date(1985, 3, 14), "male", "O+", "Hypertension since 2018."),
    ("Ananya Singh", date(1992, 7, 2), "female", "A-", "Migraine; allergic to sulfa drugs."),
    ("Aarav Patel", date(2016, 11, 23), "male", "B+", "Childhood asthma."),
]

ASSIGNMENTS = [(0, 0), (0, 3), (1, 1), (1, 4), (2, 2)]


class Command(BaseCommand):
    help = "Create a demo user with sample doctors, patients and assignments (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        user, created = User.objects.get_or_create(email=DEMO_EMAIL, defaults={"name": "Demo User"})
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save()

        doctors = [
            Doctor.objects.get_or_create(
                license_number=license_number,
                defaults={
                    "name": name,
                    "specialization": specialization,
                    "email": f"{name.split()[0].lower()}@hospital.example",
                    "phone": "+91 98000 00000",
                    "years_of_experience": years,
                    "hospital": hospital,
                    "created_by": user,
                },
            )[0]
            for name, specialization, license_number, years, hospital in DOCTORS
        ]

        patients = [
            Patient.objects.get_or_create(
                created_by=user,
                name=name,
                defaults={
                    "date_of_birth": dob,
                    "gender": gender,
                    "blood_group": blood_group,
                    "phone": "+91 99000 00000",
                    "medical_history": history,
                },
            )[0]
            for name, dob, gender, blood_group, history in PATIENTS
        ]

        for patient_index, doctor_index in ASSIGNMENTS:
            PatientDoctorMapping.objects.get_or_create(
                patient=patients[patient_index],
                doctor=doctors[doctor_index],
                defaults={"assigned_by": user},
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data ready: {len(doctors)} doctors, {len(patients)} patients, "
                f"{len(ASSIGNMENTS)} assignments.\n"
                f"Log in with {DEMO_EMAIL} / {DEMO_PASSWORD}"
            )
        )
