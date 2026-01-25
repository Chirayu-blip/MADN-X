# app/core/utils.py
from typing import Dict, Any

REQUIRED_FIELDS = ["radiology", "ecg", "symptoms_text", "lab_text"]

def validate_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensures keys exist & normalizes None → "" for text fields.
    """
    clean = {}
    for field in REQUIRED_FIELDS:
        val = payload.get(field)
        if val is None:
            clean[field] = ""
        else:
            clean[field] = val
    return clean


def detect_missing(payload: Dict[str, Any]) -> Dict[str, str]:
    """
    Returns hints on what is missing.
    """
    messages = {}

    if not payload.get("radiology"):
        messages["radiology"] = "Radiology report is missing."

    if not payload.get("ecg"):
        messages["ecg"] = "ECG description missing."

    if not payload.get("symptoms_text"):
        messages["symptoms_text"] = "Symptoms text missing."

    if not payload.get("lab_text"):
        messages["lab_text"] = "Lab information missing."

    return messages
