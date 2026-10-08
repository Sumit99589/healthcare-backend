from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import IntegrityError
from rest_framework import exceptions

from apps.common.exceptions import _first_message, api_exception_handler
from apps.mappings.models import PatientDoctorMapping
from apps.patients.views import PatientViewSet

pytestmark = pytest.mark.django_db


def test_health_check(api_client):
    response = api_client.get("/api/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_unknown_url_returns_json_404(api_client, settings):
    settings.DEBUG = False

    response = api_client.get("/api/does-not-exist/")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_method_not_allowed(auth_client):
    response = auth_client.put("/api/mappings/", {})

    assert response.status_code == 405
    assert response.json()["error"] == {
        "status": 405,
        "code": "method_not_allowed",
        "message": 'Method "PUT" not allowed.',
    }


def test_unexpected_errors_are_hidden_behind_a_500(auth_client, monkeypatch):
    def explode(self, request, *args, **kwargs):
        raise RuntimeError("database password is hunter2")

    monkeypatch.setattr(PatientViewSet, "list", explode)

    response = auth_client.get("/api/patients/")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "server_error"
    assert "hunter2" not in response.content.decode()


def test_integrity_error_becomes_409():
    response = api_exception_handler(IntegrityError("duplicate key"), {})

    assert response.status_code == 409
    assert response.data["error"]["code"] == "conflict"


def test_validation_error_envelope_for_list_payload():
    response = api_exception_handler(exceptions.ValidationError(["Something is wrong."]), {})

    assert response.status_code == 400
    assert response.data["error"] == {
        "status": 400,
        "code": "validation_error",
        "message": "Something is wrong.",
        "details": {"non_field_errors": ["Something is wrong."]},
    }


@pytest.mark.parametrize(
    "data, expected",
    [
        ({"email": ["Taken."]}, "email: Taken."),
        ({"non_field_errors": ["Bad combo."]}, "Bad combo."),
        ({"address": {"city": ["Required."]}}, "address.city: Required."),
        ({"items": [{}, {"qty": ["Too many."]}]}, "items.qty: Too many."),
        ({}, None),
    ],
)
def test_first_message(data, expected):
    assert _first_message(data) == expected


def test_openapi_schema_is_served(api_client):
    response = api_client.get("/api/schema/", HTTP_ACCEPT="application/vnd.oai.openapi+json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    for path in (
        "/api/auth/register/",
        "/api/auth/login/",
        "/api/patients/{id}/",
        "/api/doctors/{id}/",
        "/api/mappings/{id}/",
    ):
        assert path in paths


@pytest.mark.parametrize(
    "url",
    [
        "/admin/",
        "/admin/accounts/user/",
        "/admin/accounts/user/add/",
        "/admin/patients/patient/",
        "/admin/doctors/doctor/",
        "/admin/mappings/patientdoctormapping/",
    ],
)
def test_admin_pages_render(client, make_user, url):
    client.force_login(make_user(email="root@example.com", is_staff=True, is_superuser=True))

    assert client.get(url).status_code == 200


def test_admin_can_create_user(client, make_user):
    client.force_login(make_user(email="root@example.com", is_staff=True, is_superuser=True))

    response = client.post(
        "/admin/accounts/user/add/",
        {
            "email": "staff@example.com",
            "name": "Staff Member",
            "usable_password": "true",
            "password1": "Sunflower!Harbor42",
            "password2": "Sunflower!Harbor42",
        },
    )

    assert response.status_code == 302
    assert get_user_model().objects.filter(email="staff@example.com").exists()


def test_seed_demo_is_idempotent():
    call_command("seed_demo", stdout=StringIO())
    call_command("seed_demo", stdout=StringIO())

    assert PatientDoctorMapping.objects.count() == 5
