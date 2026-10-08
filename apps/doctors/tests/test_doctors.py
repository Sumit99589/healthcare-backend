import pytest

from apps.doctors.models import Doctor

URL = "/api/doctors/"
pytestmark = pytest.mark.django_db


def detail(pk):
    return f"{URL}{pk}/"


VALID = {
    "name": "Dr. Sanjay Gupta",
    "specialization": "neurology",
    "license_number": " mci-77881 ",
    "email": "S.Gupta@Hospital.example",
    "phone": "+91 90000 11111",
    "years_of_experience": 15,
    "hospital": "Apollo Hospitals",
}


def test_anonymous_requests_are_rejected(api_client):
    assert api_client.get(URL).status_code == 401
    assert api_client.post(URL, VALID).status_code == 401


class TestCreate:
    def test_creates_and_normalises_doctor(self, auth_client, user):
        response = auth_client.post(URL, VALID)

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Sanjay Gupta"
        assert body["license_number"] == "MCI-77881"
        assert body["email"] == "s.gupta@hospital.example"
        assert body["specialization_display"] == "Neurology"
        assert body["is_available"] is True
        assert body["created_by"] == user.id

    def test_required_fields(self, auth_client):
        response = auth_client.post(URL, {})

        assert response.status_code == 400
        assert set(response.json()["error"]["details"]) == {
            "name",
            "specialization",
            "license_number",
            "email",
            "phone",
        }

    def test_duplicate_email_case_insensitive(self, auth_client, user, make_doctor):
        make_doctor(user, email="s.gupta@hospital.example")

        response = auth_client.post(URL, VALID)

        assert response.status_code == 400
        assert response.json()["error"]["details"]["email"] == [
            "A doctor with this email already exists."
        ]

    def test_duplicate_license_number(self, auth_client, user, make_doctor):
        make_doctor(user, license_number="MCI-77881")

        response = auth_client.post(URL, VALID)

        assert response.status_code == 400
        assert "license_number" in response.json()["error"]["details"]

    @pytest.mark.parametrize(
        "field, value",
        [
            ("specialization", "wizardry"),
            ("years_of_experience", 71),
            ("years_of_experience", -1),
            ("phone", "12"),
            ("license_number", "   "),
        ],
    )
    def test_invalid_values(self, auth_client, field, value):
        response = auth_client.post(URL, {**VALID, field: value})

        assert response.status_code == 400
        assert field in response.json()["error"]["details"]


class TestRead:
    def test_lists_all_doctors_from_all_users(self, auth_client, user, other_user, make_doctor):
        make_doctor(user)
        make_doctor(other_user)

        body = auth_client.get(URL).json()

        assert body["count"] == 2

    def test_filter_by_specialization_and_search(self, auth_client, user, make_doctor):
        make_doctor(user, name="Leela Pillai", specialization="pediatrics")
        make_doctor(user, name="Rahul Verma", specialization="cardiology")

        peds = auth_client.get(URL, {"specialization": "pediatrics"}).json()["results"]
        found = auth_client.get(URL, {"search": "verma"}).json()["results"]

        assert [d["name"] for d in peds] == ["Leela Pillai"]
        assert [d["name"] for d in found] == ["Rahul Verma"]

    def test_retrieve_doctor_created_by_someone_else(self, auth_client, other_user, make_doctor):
        doctor = make_doctor(other_user)

        response = auth_client.get(detail(doctor.id))

        assert response.status_code == 200
        assert response.json()["id"] == doctor.id

    def test_missing_doctor(self, auth_client):
        assert auth_client.get(detail(999999)).status_code == 404


class TestWrite:
    def test_creator_can_update(self, auth_client, user, make_doctor):
        doctor = make_doctor(user)

        response = auth_client.put(detail(doctor.id), VALID)

        assert response.status_code == 200
        doctor.refresh_from_db()
        assert doctor.specialization == "neurology"

    def test_update_can_keep_own_email_and_license(self, auth_client, user, make_doctor):
        doctor = make_doctor(user)

        response = auth_client.patch(
            detail(doctor.id),
            {"email": doctor.email.upper(), "license_number": doctor.license_number},
        )

        assert response.status_code == 200

    def test_update_cannot_take_another_doctors_email(self, auth_client, user, make_doctor):
        first, second = make_doctor(user), make_doctor(user)

        response = auth_client.patch(detail(second.id), {"email": first.email})

        assert response.status_code == 400

    def test_other_user_cannot_update(self, other_client, user, make_doctor):
        doctor = make_doctor(user)

        response = other_client.patch(detail(doctor.id), {"name": "Hijacked"})

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "permission_denied"
        doctor.refresh_from_db()
        assert doctor.name != "Hijacked"

    def test_other_user_cannot_delete(self, other_client, user, make_doctor):
        doctor = make_doctor(user)

        assert other_client.delete(detail(doctor.id)).status_code == 403
        assert Doctor.objects.filter(pk=doctor.id).exists()

    def test_staff_can_delete_any_doctor(self, client_for, make_user, user, make_doctor):
        doctor = make_doctor(user)
        admin = client_for(make_user(email="admin@example.com", is_staff=True))

        assert admin.delete(detail(doctor.id)).status_code == 204

    def test_creator_can_delete(self, auth_client, user, make_doctor):
        doctor = make_doctor(user)

        assert auth_client.delete(detail(doctor.id)).status_code == 204
        assert not Doctor.objects.filter(pk=doctor.id).exists()
