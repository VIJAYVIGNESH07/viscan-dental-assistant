import re
from app.data_store import get_patients


def normalize(value: str) -> str:
    value = re.sub(r"(?i)([a-z])['’]s\b", r"\1", value or "")
    return re.sub(r"[^a-z0-9 ]+", " ", value.lower()).strip()


def find_patient_matches(name_query: str) -> list[dict]:
    query = normalize(name_query)
    if not query:
        return []
    patients = get_patients()
    # Full-name exact match takes precedence.
    exact = [p for p in patients if normalize(p["name"]) == query]
    if exact:
        return exact
    tokens = query.split()
    # Require every query token to occur in the patient's normalized name.
    matches = [
        p for p in patients
        if all(token in normalize(p["name"]).split() for token in tokens)
    ]
    # First-name-only queries naturally return all matching patients.
    return matches


def public_patient(patient: dict) -> dict:
    return {
        "patient_id": patient["patient_id"],
        "name": patient["name"],
        "date_of_birth": patient.get("date_of_birth"),
    }
