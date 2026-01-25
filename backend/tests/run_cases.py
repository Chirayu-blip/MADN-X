import json, requests, sys
from pathlib import Path

BASE = "http://127.0.0.1:8000"

def post(path, payload):
    r = requests.post(f"{BASE}{path}", json=payload, timeout=90)
    ok = r.status_code == 200
    return ok, r.status_code, (r.json() if ok else r.text)

def contains_any(text_or_dict, targets):
    s = json.dumps(text_or_dict).lower() if isinstance(text_or_dict, (dict, list)) else str(text_or_dict).lower()
    return any(t.lower() in s for t in targets)

def score_agent(name, output, expected):
    # output can be dict or string
    text = json.dumps(output).lower() if isinstance(output, (dict, list)) else str(output).lower()
    hits = sum(1 for e in expected if e.lower() in text)
    return {"agent": name, "hits": hits, "matched": [e for e in expected if e.lower() in text]}

def main():
    path = Path(__file__).with_name("sample_cases.json")
    cases = json.loads(path.read_text(encoding="utf-8"))
    summary = []
    for c in cases:
        print(f"\n=== Case {c['id']} ===")
        rad_ok, _, rad = post("/radiologist", {"radiology": c.get("radiology","")})
        car_ok, _, car = post("/cardiologist", {"ecg": c.get("ecg","")})
        pul_ok, _, pul = post("/pulmonologist", {"symptoms_text": c.get("symptoms_text","")})
        pat_ok, _, pat = post("/pathologist", {"lab_text": c.get("lab_text","")})

        diag_ok, _, diag = post("/diagnose", {
            "radiology": c.get("radiology"),
            "ecg": c.get("ecg"),
            "symptoms_text": c.get("symptoms_text"),
            "lab_text": c.get("lab_text")
        })

        print("Radiologist:", "OK" if rad_ok else "ERR", type(rad))
        print("Cardiologist:", "OK" if car_ok else "ERR", type(car))
        print("Pulmonologist:", "OK" if pul_ok else "ERR", type(pul))
        print("Pathologist:", "OK" if pat_ok else "ERR", type(pat))
        print("Diagnose:", "OK" if diag_ok else "ERR", type(diag))

        case_row = {"id": c["id"], "expected": c["expected"], "agents": []}
        if rad_ok: case_row["agents"].append(score_agent("radiology", rad, c["expected"]))
        if car_ok: case_row["agents"].append(score_agent("cardiology", car, c["expected"]))
        if pul_ok: case_row["agents"].append(score_agent("pulmonology", pul, c["expected"]))
        if pat_ok: case_row["agents"].append(score_agent("pathology", pat, c["expected"]))
        if diag_ok: case_row["consensus_hit"] = contains_any(diag, c["expected"])
        summary.append(case_row)

    print("\n=== SUMMARY ===")
    for row in summary:
        total_hits = sum(a["hits"] for a in row["agents"])
        print(f"{row['id']}: agent_hits={total_hits} | consensus_hit={row.get('consensus_hit')}")
        for a in row["agents"]:
            print(f"  - {a['agent']}: hits={a['hits']} matched={a['matched']}")

if __name__ == "__main__":
    sys.exit(main())
