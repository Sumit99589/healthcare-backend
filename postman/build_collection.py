"""
Generates `Healthcare-Backend.postman_collection.json`.

The collection is a runnable end-to-end scenario: it registers a fresh user, stores the
JWT in a collection variable, then exercises every endpoint in order with assertions.
Run it in Postman (Collection > Run) or from the command line:

    npx newman run postman/Healthcare-Backend.postman_collection.json

Regenerate after changing this file:  python postman/build_collection.py
"""

import json
from pathlib import Path

OUTPUT = Path(__file__).with_name("Healthcare-Backend.postman_collection.json")


def script(*lines):
    return [{"listen": "test", "script": {"type": "text/javascript", "exec": list(lines)}}]


def prerequest(*lines):
    return {"listen": "prerequest", "script": {"type": "text/javascript", "exec": list(lines)}}


def expect_status(code):
    return f'pm.test("status is {code}", () => pm.response.to.have.status({code}));'


def request(name, method, path, body=None, tests=(), auth=True, events=(), description=""):
    url_path = [p for p in path.strip("/").split("/") if p]
    item = {
        "name": name,
        "request": {
            "method": method,
            "header": [],
            "url": {
                "raw": "{{base_url}}/" + "/".join(url_path) + "/",
                "host": ["{{base_url}}"],
                "path": [*url_path, ""],
            },
            "description": description,
        },
        "event": [*events, *script(*tests)] if tests else list(events),
    }
    if body is not None:
        item["request"]["header"].append({"key": "Content-Type", "value": "application/json"})
        item["request"]["body"] = {
            "mode": "raw",
            "raw": json.dumps(body, indent=2),
            "options": {"raw": {"language": "json"}},
        }
    if not auth:
        item["request"]["auth"] = {"type": "noauth"}
    return item


def folder(name, items, description=""):
    return {"name": name, "description": description, "item": items}


SAVE_TOKENS = (
    "const body = pm.response.json();",
    'pm.collectionVariables.set("access_token", body.tokens.access);',
    'pm.collectionVariables.set("refresh_token", body.tokens.refresh);',
)

auth = folder(
    "1. Auth",
    [
        request(
            "Register",
            "POST",
            "api/auth/register",
            {"name": "{{user_name}}", "email": "{{user_email}}", "password": "{{user_password}}"},
            auth=False,
            events=[
                prerequest(
                    "// A unique email per run so the collection can be re-run.",
                    'pm.collectionVariables.set("user_email", `user${Date.now()}@example.com`);',
                )
            ],
            tests=(
                expect_status(201),
                *SAVE_TOKENS,
                'pm.test("returns the user", () => {',
                '    pm.expect(body.user.email).to.eql(pm.collectionVariables.get("user_email"));',
                '    pm.expect(body.user).to.not.have.property("password");',
                "});",
            ),
            description="Create an account. Returns the user and a JWT pair.",
        ),
        request(
            "Register (duplicate email -> 400)",
            "POST",
            "api/auth/register",
            {"name": "{{user_name}}", "email": "{{user_email}}", "password": "{{user_password}}"},
            auth=False,
            tests=(
                expect_status(400),
                'pm.test("error envelope", () => {',
                "    const error = pm.response.json().error;",
                '    pm.expect(error.code).to.eql("validation_error");',
                '    pm.expect(error.details).to.have.property("email");',
                "});",
            ),
        ),
        request(
            "Login",
            "POST",
            "api/auth/login",
            {"email": "{{user_email}}", "password": "{{user_password}}"},
            auth=False,
            tests=(expect_status(200), *SAVE_TOKENS),
            description="Log in with email + password. Stores the tokens for later requests.",
        ),
        request(
            "Login (wrong password -> 401)",
            "POST",
            "api/auth/login",
            {"email": "{{user_email}}", "password": "not-the-password"},
            auth=False,
            tests=(expect_status(401),),
        ),
        request(
            "Refresh access token",
            "POST",
            "api/auth/token/refresh",
            {"refresh": "{{refresh_token}}"},
            auth=False,
            tests=(
                expect_status(200),
                "const body = pm.response.json();",
                'pm.collectionVariables.set("access_token", body.access);',
                'pm.collectionVariables.set("refresh_token", body.refresh);',
            ),
        ),
        request(
            "Me",
            "GET",
            "api/auth/me",
            tests=(
                expect_status(200),
                'pm.test("is the logged-in user", () => pm.expect(pm.response.json().email)'
                '.to.eql(pm.collectionVariables.get("user_email")));',
            ),
        ),
    ],
)

doctors = folder(
    "2. Doctors",
    [
        request(
            "Create doctor",
            "POST",
            "api/doctors",
            {
                "name": "Dr. Meera Iyer",
                "specialization": "cardiology",
                "license_number": "MCI-{{run_id}}",
                "email": "meera.{{run_id}}@hospital.example",
                "phone": "+91 98765 43210",
                "years_of_experience": 14,
                "hospital": "Apollo Hospitals",
            },
            events=[
                prerequest('pm.collectionVariables.set("run_id", Date.now().toString());'),
            ],
            tests=(
                expect_status(201),
                'pm.collectionVariables.set("doctor_id", pm.response.json().id);',
                'pm.test("name is stored without the title", () => '
                'pm.expect(pm.response.json().name).to.eql("Meera Iyer"));',
            ),
        ),
        request(
            "Create doctor (invalid -> 400)",
            "POST",
            "api/doctors",
            {"name": "", "specialization": "wizardry", "years_of_experience": 99},
            tests=(
                expect_status(400),
                'pm.test("lists every invalid field", () => {',
                "    const details = pm.response.json().error.details;",
                '    pm.expect(details).to.include.keys("name", "specialization", '
                '"years_of_experience", "email");',
                "});",
            ),
        ),
        request(
            "List doctors",
            "GET",
            "api/doctors",
            tests=(
                expect_status(200),
                'pm.test("paginated", () => pm.expect(pm.response.json()).to.include.keys('
                '"count", "next", "previous", "results"));',
            ),
            description="Supports ?search=, ?specialization=, ?is_available=, ?ordering=, ?page=.",
        ),
        request("Get doctor", "GET", "api/doctors/{{doctor_id}}", tests=(expect_status(200),)),
        request(
            "Update doctor (PUT)",
            "PUT",
            "api/doctors/{{doctor_id}}",
            {
                "name": "Meera Iyer",
                "specialization": "cardiology",
                "license_number": "MCI-{{run_id}}",
                "email": "meera.{{run_id}}@hospital.example",
                "phone": "+91 98765 43210",
                "years_of_experience": 15,
                "hospital": "Apollo Hospitals, Chennai",
            },
            tests=(
                expect_status(200),
                'pm.test("updated", () => pm.expect(pm.response.json().years_of_experience)'
                ".to.eql(15));",
            ),
        ),
    ],
)

patients = folder(
    "3. Patients",
    [
        request(
            "Create patient",
            "POST",
            "api/patients",
            {
                "name": "Ravi Kumar",
                "date_of_birth": "1985-03-14",
                "gender": "male",
                "blood_group": "O+",
                "phone": "+91 99887 76655",
                "email": "ravi.kumar@example.com",
                "address": "12 MG Road, Bengaluru",
                "medical_history": "Hypertension since 2018.",
                "allergies": "Penicillin",
            },
            tests=(
                expect_status(201),
                'pm.collectionVariables.set("patient_id", pm.response.json().id);',
                'pm.test("age is computed", () => pm.expect(pm.response.json().age)'
                '.to.be.a("number"));',
            ),
        ),
        request(
            "Create patient (future birth date -> 400)",
            "POST",
            "api/patients",
            {
                "name": "Time Traveller",
                "date_of_birth": "2999-01-01",
                "gender": "other",
                "phone": "+91 99887 76655",
            },
            tests=(
                expect_status(400),
                'pm.test("date_of_birth rejected", () => pm.expect(pm.response.json().error'
                '.details).to.have.property("date_of_birth"));',
            ),
        ),
        request(
            "List my patients",
            "GET",
            "api/patients",
            tests=(
                expect_status(200),
                'pm.test("only my patient", () => pm.expect(pm.response.json().count).to.eql(1));',
            ),
            description="Supports ?search=, ?gender=, ?blood_group=, ?ordering=, ?page=.",
        ),
        request("Get patient", "GET", "api/patients/{{patient_id}}", tests=(expect_status(200),)),
        request(
            "Update patient (PUT)",
            "PUT",
            "api/patients/{{patient_id}}",
            {
                "name": "Ravi Kumar",
                "date_of_birth": "1985-03-14",
                "gender": "male",
                "blood_group": "O+",
                "phone": "+91 99887 76655",
                "email": "ravi.kumar@example.com",
                "address": "45 Residency Road, Bengaluru",
                "medical_history": "Hypertension since 2018. On amlodipine 5 mg.",
                "allergies": "Penicillin",
            },
            tests=(
                expect_status(200),
                'pm.test("updated", () => pm.expect(pm.response.json().address)'
                '.to.eql("45 Residency Road, Bengaluru"));',
            ),
        ),
    ],
)

mappings = folder(
    "4. Patient-Doctor Mappings",
    [
        request(
            "Assign doctor to patient",
            "POST",
            "api/mappings",
            {
                "patient": "{{patient_id}}",
                "doctor": "{{doctor_id}}",
                "notes": "Cardiology referral",
            },
            tests=(
                expect_status(201),
                'pm.collectionVariables.set("mapping_id", pm.response.json().id);',
                'pm.test("embeds patient and doctor", () => {',
                "    const body = pm.response.json();",
                "    const vars = pm.collectionVariables;",
                '    pm.expect(body.patient.id).to.eql(Number(vars.get("patient_id")));',
                '    pm.expect(body.doctor.id).to.eql(Number(vars.get("doctor_id")));',
                "});",
            ),
        ),
        request(
            "Assign same doctor again (-> 409)",
            "POST",
            "api/mappings",
            {"patient": "{{patient_id}}", "doctor": "{{doctor_id}}"},
            tests=(expect_status(409),),
        ),
        request(
            "List mappings",
            "GET",
            "api/mappings",
            tests=(expect_status(200),),
            description="Supports ?patient=<id> and ?doctor=<id>.",
        ),
        request(
            "Get doctors of a patient",
            "GET",
            "api/mappings/{{patient_id}}",
            tests=(
                expect_status(200),
                'pm.test("one doctor assigned", () => '
                "pm.expect(pm.response.json().count).to.eql(1));",
            ),
            description="Note: for GET the ID in this URL is a PATIENT id.",
        ),
        request(
            "Remove doctor from patient",
            "DELETE",
            "api/mappings/{{mapping_id}}",
            tests=(expect_status(204),),
            description="Note: for DELETE the ID in this URL is a MAPPING id.",
        ),
        request(
            "Get doctors of a patient (after removal)",
            "GET",
            "api/mappings/{{patient_id}}",
            tests=(
                expect_status(200),
                'pm.test("no doctors left", () => pm.expect(pm.response.json().count).to.eql(0));',
            ),
        ),
    ],
)

cleanup = folder(
    "5. Cleanup & logout",
    [
        request(
            "No token (-> 401)",
            "GET",
            "api/patients",
            auth=False,
            tests=(expect_status(401),),
        ),
        request(
            "Delete patient", "DELETE", "api/patients/{{patient_id}}", tests=(expect_status(204),)
        ),
        request(
            "Get deleted patient (-> 404)",
            "GET",
            "api/patients/{{patient_id}}",
            tests=(expect_status(404),),
        ),
        request(
            "Delete doctor", "DELETE", "api/doctors/{{doctor_id}}", tests=(expect_status(204),)
        ),
        request(
            "Logout",
            "POST",
            "api/auth/logout",
            {"refresh": "{{refresh_token}}"},
            tests=(expect_status(205),),
        ),
        request(
            "Refresh with revoked token (-> 401)",
            "POST",
            "api/auth/token/refresh",
            {"refresh": "{{refresh_token}}"},
            auth=False,
            tests=(expect_status(401),),
        ),
    ],
)

collection = {
    "info": {
        "name": "Healthcare Backend API",
        "description": (
            "End-to-end scenario for the Healthcare Backend. Run the whole collection in order: "
            "it registers a new user, stores the JWT automatically and exercises every endpoint."
        ),
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "auth": {
        "type": "bearer",
        "bearer": [{"key": "token", "value": "{{access_token}}", "type": "string"}],
    },
    "variable": [
        {"key": "base_url", "value": "http://localhost:8000"},
        {"key": "user_name", "value": "Postman Tester"},
        {"key": "user_email", "value": ""},
        {"key": "user_password", "value": "Sunflower!Harbor42"},
        {"key": "access_token", "value": ""},
        {"key": "refresh_token", "value": ""},
        {"key": "run_id", "value": ""},
        {"key": "doctor_id", "value": ""},
        {"key": "patient_id", "value": ""},
        {"key": "mapping_id", "value": ""},
    ],
    "item": [auth, doctors, patients, mappings, cleanup],
}

if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(collection, indent=2) + "\n")
    print(f"Wrote {OUTPUT}")
