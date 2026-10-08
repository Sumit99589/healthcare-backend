import pytest

from apps.mappings.models import PatientDoctorMapping

URL = "/api/mappings/"
pytestmark = pytest.mark.django_db


def detail(pk):
    return f"{URL}{pk}/"


@pytest.fixture
def patient(user, make_patient):
    return make_patient(user)


@pytest.fixture
def doctor(other_user, make_doctor):
    # Created by someone else on purpose: the doctor directory is shared.
    return make_doctor(other_user)


def test_anonymous_requests_are_rejected(api_client):
    assert api_client.get(URL).status_code == 401
    assert api_client.post(URL, {}).status_code == 401
    assert api_client.get(detail(1)).status_code == 401
    assert api_client.delete(detail(1)).status_code == 401


class TestAssign:
    def test_assigns_doctor_to_patient(self, auth_client, user, patient, doctor):
        response = auth_client.post(
            URL, {"patient": patient.id, "doctor": doctor.id, "notes": "Referral"}
        )

        assert response.status_code == 201
        body = response.json()
        assert body["patient"]["id"] == patient.id
        assert body["patient"]["name"] == patient.name
        assert body["doctor"]["id"] == doctor.id
        assert body["doctor"]["specialization"] == "cardiology"
        assert body["notes"] == "Referral"
        assert "assigned_at" in body
        mapping = PatientDoctorMapping.objects.get(pk=body["id"])
        assert mapping.assigned_by == user

    def test_same_doctor_twice_is_a_conflict(self, auth_client, patient, doctor):
        auth_client.post(URL, {"patient": patient.id, "doctor": doctor.id})

        response = auth_client.post(URL, {"patient": patient.id, "doctor": doctor.id})

        assert response.status_code == 409
        assert response.json()["error"] == {
            "status": 409,
            "code": "conflict",
            "message": "This doctor is already assigned to this patient.",
        }
        assert PatientDoctorMapping.objects.count() == 1

    def test_several_doctors_for_one_patient(self, auth_client, user, patient, make_doctor):
        for _ in range(3):
            doctor = make_doctor(user)
            assert (
                auth_client.post(URL, {"patient": patient.id, "doctor": doctor.id}).status_code
                == 201
            )

        assert patient.doctor_assignments.count() == 3

    def test_cannot_assign_to_other_users_patient(
        self, auth_client, other_user, make_patient, doctor
    ):
        theirs = make_patient(other_user)

        response = auth_client.post(URL, {"patient": theirs.id, "doctor": doctor.id})

        assert response.status_code == 400
        assert response.json()["error"]["details"]["patient"] == [
            f"Patient {theirs.id} does not exist."
        ]

    def test_unknown_doctor(self, auth_client, patient):
        response = auth_client.post(URL, {"patient": patient.id, "doctor": 987654})

        assert response.status_code == 400
        assert response.json()["error"]["details"]["doctor"] == ["Doctor 987654 does not exist."]

    def test_unavailable_doctor(self, auth_client, user, patient, make_doctor):
        doctor = make_doctor(user, is_available=False)

        response = auth_client.post(URL, {"patient": patient.id, "doctor": doctor.id})

        assert response.status_code == 400
        assert "doctor" in response.json()["error"]["details"]

    def test_required_fields(self, auth_client):
        response = auth_client.post(URL, {})

        assert response.status_code == 400
        assert set(response.json()["error"]["details"]) == {"patient", "doctor"}


class TestList:
    def test_lists_only_mappings_of_own_patients(
        self, auth_client, user, other_user, make_patient, make_doctor
    ):
        doctor = make_doctor(user)
        mine = PatientDoctorMapping.objects.create(patient=make_patient(user), doctor=doctor)
        PatientDoctorMapping.objects.create(patient=make_patient(other_user), doctor=doctor)

        body = auth_client.get(URL).json()

        assert body["count"] == 1
        assert body["results"][0]["id"] == mine.id
        assert body["results"][0]["doctor"]["name"] == doctor.name

    def test_filter_by_doctor(self, auth_client, user, patient, make_doctor):
        first, second = make_doctor(user), make_doctor(user)
        PatientDoctorMapping.objects.create(patient=patient, doctor=first)
        PatientDoctorMapping.objects.create(patient=patient, doctor=second)

        results = auth_client.get(URL, {"doctor": second.id}).json()["results"]

        assert [m["doctor"]["id"] for m in results] == [second.id]


class TestDoctorsForPatient:
    def test_returns_assigned_doctors(self, auth_client, user, patient, make_doctor):
        cardio = make_doctor(user, name="Heart Doc", specialization="cardiology")
        neuro = make_doctor(user, name="Brain Doc", specialization="neurology")
        unrelated = make_doctor(user, name="Not Assigned")
        first = PatientDoctorMapping.objects.create(patient=patient, doctor=cardio)
        PatientDoctorMapping.objects.create(patient=patient, doctor=neuro)

        response = auth_client.get(detail(patient.id))

        assert response.status_code == 200
        body = response.json()
        assert body["patient"]["id"] == patient.id
        assert body["count"] == 2
        assert [d["doctor"]["name"] for d in body["doctors"]] == ["Heart Doc", "Brain Doc"]
        assert body["doctors"][0]["mapping_id"] == first.id
        assert unrelated.name not in str(body)

    def test_patient_without_doctors(self, auth_client, patient):
        body = auth_client.get(detail(patient.id)).json()

        assert body["count"] == 0
        assert body["doctors"] == []

    def test_other_users_patient_is_not_found(self, auth_client, other_user, make_patient):
        theirs = make_patient(other_user)

        assert auth_client.get(detail(theirs.id)).status_code == 404


class TestRemove:
    def test_removes_mapping(self, auth_client, patient, doctor):
        mapping = PatientDoctorMapping.objects.create(patient=patient, doctor=doctor)

        response = auth_client.delete(detail(mapping.id))

        assert response.status_code == 204
        assert not PatientDoctorMapping.objects.filter(pk=mapping.id).exists()
        # Only the assignment goes; patient and doctor stay.
        assert patient.__class__.objects.filter(pk=patient.id).exists()
        assert doctor.__class__.objects.filter(pk=doctor.id).exists()

    def test_cannot_remove_mapping_of_other_users_patient(
        self, auth_client, other_user, make_patient, doctor
    ):
        mapping = PatientDoctorMapping.objects.create(
            patient=make_patient(other_user), doctor=doctor
        )

        assert auth_client.delete(detail(mapping.id)).status_code == 404
        assert PatientDoctorMapping.objects.filter(pk=mapping.id).exists()

    def test_missing_mapping(self, auth_client):
        assert auth_client.delete(detail(123456)).status_code == 404


class TestCascades:
    def test_deleting_patient_removes_its_mappings(self, auth_client, patient, doctor):
        PatientDoctorMapping.objects.create(patient=patient, doctor=doctor)

        auth_client.delete(f"/api/patients/{patient.id}/")

        assert PatientDoctorMapping.objects.count() == 0

    def test_deleting_doctor_removes_its_mappings(self, other_client, patient, doctor):
        PatientDoctorMapping.objects.create(patient=patient, doctor=doctor)

        assert other_client.delete(f"/api/doctors/{doctor.id}/").status_code == 204

        assert PatientDoctorMapping.objects.count() == 0
