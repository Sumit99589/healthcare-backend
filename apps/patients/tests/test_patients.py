from datetime import date, timedelta

import pytest

from apps.patients.models import Patient

URL = "/api/patients/"
pytestmark = pytest.mark.django_db


def detail(pk):
    return f"{URL}{pk}/"


VALID = {
    "name": "Ananya Rao",
    "date_of_birth": "1988-11-02",
    "gender": "female",
    "blood_group": "B+",
    "phone": "+91 99887 66554",
    "email": "Ananya.Rao@Example.com",
    "address": "12 MG Road, Bengaluru",
    "medical_history": "Type 2 diabetes, diagnosed 2019.",
    "allergies": "Penicillin",
}


class TestAuthRequired:
    @pytest.mark.parametrize(
        "method, url",
        [
            ("get", URL),
            ("post", URL),
            ("get", detail(1)),
            ("put", detail(1)),
            ("delete", detail(1)),
        ],
    )
    def test_anonymous_requests_are_rejected(self, api_client, method, url):
        response = getattr(api_client, method)(url, {})

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "not_authenticated"


class TestCreate:
    def test_creates_patient_owned_by_requesting_user(self, auth_client, user):
        response = auth_client.post(URL, VALID)

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Ananya Rao"
        assert body["email"] == "ananya.rao@example.com"
        assert isinstance(body["age"], int)
        assert Patient.objects.get(pk=body["id"]).created_by == user

    def test_client_cannot_choose_owner_or_id(self, auth_client, user, other_user):
        response = auth_client.post(URL, {**VALID, "created_by": other_user.id, "id": 999})

        assert response.status_code == 201
        patient = Patient.objects.get(pk=response.json()["id"])
        assert patient.created_by == user
        assert patient.pk != 999

    def test_optional_fields_can_be_omitted(self, auth_client):
        minimal = {k: VALID[k] for k in ("name", "date_of_birth", "gender", "phone")}

        response = auth_client.post(URL, minimal)

        assert response.status_code == 201
        assert response.json()["blood_group"] == ""

    def test_required_fields(self, auth_client):
        response = auth_client.post(URL, {})

        assert response.status_code == 400
        details = response.json()["error"]["details"]
        assert set(details) == {"name", "date_of_birth", "gender", "phone"}

    @pytest.mark.parametrize(
        "field, value",
        [
            ("date_of_birth", (date.today() + timedelta(days=1)).isoformat()),
            ("date_of_birth", "1800-01-01"),
            ("date_of_birth", "17/05/1990"),
            ("gender", "unknown"),
            ("blood_group", "Z+"),
            ("phone", "call me"),
            ("email", "nope"),
            ("name", "   "),
        ],
    )
    def test_invalid_values(self, auth_client, field, value):
        response = auth_client.post(URL, {**VALID, field: value})

        assert response.status_code == 400
        assert field in response.json()["error"]["details"]

    def test_rejects_non_json_body(self, auth_client):
        response = auth_client.post(URL, "name=x", content_type="application/x-www-form-urlencoded")

        assert response.status_code == 415
        assert response.json()["error"]["code"] == "unsupported_media_type"

    def test_malformed_json(self, auth_client):
        response = auth_client.post(URL, "{bad json", content_type="application/json")

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "parse_error"


class TestList:
    def test_only_lists_own_patients(self, auth_client, user, other_user, make_patient):
        mine = [make_patient(user, name="Mine A"), make_patient(user, name="Mine B")]
        make_patient(other_user, name="Not mine")

        response = auth_client.get(URL)

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 2
        assert {p["id"] for p in body["results"]} == {p.id for p in mine}

    def test_is_paginated(self, auth_client, user, make_patient):
        for i in range(3):
            make_patient(user, name=f"Patient {i}")

        body = auth_client.get(URL, {"page_size": 2}).json()

        assert body["count"] == 3
        assert len(body["results"]) == 2
        assert body["next"] is not None

    def test_search_and_filter(self, auth_client, user, make_patient):
        make_patient(user, name="Kavya Menon", gender="female", blood_group="A+")
        make_patient(user, name="Arjun Das", gender="male", blood_group="A+")

        by_name = auth_client.get(URL, {"search": "kavya"}).json()["results"]
        by_gender = auth_client.get(URL, {"gender": "male"}).json()["results"]
        by_blood = auth_client.get(URL, {"blood_group": "A+"}).json()["results"]

        assert [p["name"] for p in by_name] == ["Kavya Menon"]
        assert [p["name"] for p in by_gender] == ["Arjun Das"]
        assert len(by_blood) == 2

    def test_ordering(self, auth_client, user, make_patient):
        make_patient(user, name="Zara")
        make_patient(user, name="Aarav")

        names = [p["name"] for p in auth_client.get(URL, {"ordering": "name"}).json()["results"]]

        assert names == ["Aarav", "Zara"]


class TestDetail:
    def test_retrieve_own_patient(self, auth_client, user, make_patient):
        patient = make_patient(user)

        response = auth_client.get(detail(patient.id))

        assert response.status_code == 200
        assert response.json()["name"] == patient.name

    def test_other_users_patient_is_not_found(self, auth_client, other_user, make_patient):
        theirs = make_patient(other_user)

        response = auth_client.get(detail(theirs.id))

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"

    def test_missing_patient(self, auth_client):
        assert auth_client.get(detail(424242)).status_code == 404


class TestUpdate:
    def test_put_replaces_patient(self, auth_client, user, make_patient):
        patient = make_patient(user)

        response = auth_client.put(detail(patient.id), {**VALID, "name": "Updated Name"})

        assert response.status_code == 200
        patient.refresh_from_db()
        assert patient.name == "Updated Name"
        assert patient.allergies == "Penicillin"

    def test_put_requires_all_required_fields(self, auth_client, user, make_patient):
        patient = make_patient(user)

        response = auth_client.put(detail(patient.id), {"name": "Only a name"})

        assert response.status_code == 400

    def test_patch_updates_single_field(self, auth_client, user, make_patient):
        patient = make_patient(user)

        response = auth_client.patch(detail(patient.id), {"phone": "+1 415 555 0100"})

        assert response.status_code == 200
        patient.refresh_from_db()
        assert patient.phone == "+1 415 555 0100"
        assert patient.name == "Ravi Kumar"

    def test_cannot_update_other_users_patient(self, auth_client, other_user, make_patient):
        theirs = make_patient(other_user)

        response = auth_client.put(detail(theirs.id), VALID)

        assert response.status_code == 404
        theirs.refresh_from_db()
        assert theirs.name == "Ravi Kumar"


class TestDelete:
    def test_delete_own_patient(self, auth_client, user, make_patient):
        patient = make_patient(user)

        response = auth_client.delete(detail(patient.id))

        assert response.status_code == 204
        assert not Patient.objects.filter(pk=patient.id).exists()

    def test_cannot_delete_other_users_patient(self, auth_client, other_user, make_patient):
        theirs = make_patient(other_user)

        response = auth_client.delete(detail(theirs.id))

        assert response.status_code == 404
        assert Patient.objects.filter(pk=theirs.id).exists()
