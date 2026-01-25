def process_case(data):
    return {
        "symptoms": data.get("symptoms", ""),
        "labs": data.get("labs", {}),
        "radiology": data.get("radiology", ""),
        "ecg": data.get("ecg", "")
    }
