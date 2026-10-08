from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.serializers import tokens_for
from apps.doctors.models import Doctor
from apps.patients.models import Patient

PASSWORD = "Sunflower!Harbor42"


@pytest.fixture(autouse=True)
def _test_settings(settings):
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    # The manifest storage needs `collectstatic` first; tests don't need hashed names.
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    cache.clear()  # throttling counters live in the cache
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def make_user(db):
    def _make(email="alice@example.com", name="Alice Sharma", password=PASSWORD, **extra):
        return get_user_model().objects.create_user(
            email=email, name=name, password=password, **extra
        )

    return _make


@pytest.fixture
def user(make_user):
    return make_user()


@pytest.fixture
def other_user(make_user):
    return make_user(email="bob@example.com", name="Bob Mehta")


def _client_for(user):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens_for(user)['access']}")
    return client


@pytest.fixture
def client_for():
    """Factory: an APIClient authenticated as the given user."""
    return _client_for


@pytest.fixture
def auth_client(user):
    return _client_for(user)


@pytest.fixture
def other_client(other_user):
    return _client_for(other_user)


@pytest.fixture
def make_patient(db):
    def _make(owner, **overrides):
        data = {
            "name": "Ravi Kumar",
            "date_of_birth": date(1990, 5, 17),
            "gender": Patient.Gender.MALE,
            "blood_group": "O+",
            "phone": "+91 98765 43210",
        }
        data.update(overrides)
        return Patient.objects.create(created_by=owner, **data)

    return _make


@pytest.fixture
def make_doctor(db):
    counter = {"n": 0}

    def _make(creator, **overrides):
        counter["n"] += 1
        n = counter["n"]
        data = {
            "name": f"Meera Iyer {n}",
            "specialization": Doctor.Specialization.CARDIOLOGY,
            "license_number": f"MCI-{1000 + n}",
            "email": f"doctor{n}@hospital.example",
            "phone": "+91 91234 56789",
            "years_of_experience": 12,
            "hospital": "City General Hospital",
        }
        data.update(overrides)
        return Doctor.objects.create(created_by=creator, **data)

    return _make
