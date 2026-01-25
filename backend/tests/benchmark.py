"""
MADN-X Benchmarking Suite
==========================
Run clinical test cases and measure diagnostic accuracy.

This script demonstrates MADN-X's diagnostic capabilities on a variety
of clinical scenarios, measuring:
- Diagnostic accuracy
- Confidence calibration  
- Latency performance
- Definitive finding detection

Run: python tests/benchmark.py
"""

import requests
import json
import time
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime

API_URL = "http://localhost:8000"


@dataclass
class TestCase:
    """Represents a clinical test case with expected outcome."""
    name: str
    description: str
    radiology: str
    ecg: str
    symptoms: str
    labs: str
    expected_diagnosis: str
    expected_min_confidence: float
    should_be_definitive: bool = False


# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARK TEST CASES
# ═══════════════════════════════════════════════════════════════════════════════

BENCHMARK_CASES: List[TestCase] = [
    # ─────────── PULMONARY EMBOLISM CASES ───────────
    TestCase(
        name="PE_CTPA_Positive",
        description="Classic PE with positive CTPA - should CONFIRM",
        radiology="CT angiography shows filling defect in right main pulmonary artery",
        ecg="Sinus tachycardia 110 bpm, S1Q3T3 pattern",
        symptoms="Sudden onset dyspnea, pleuritic chest pain, recent DVT",
        labs="D-dimer 2500, troponin mildly elevated",
        expected_diagnosis="Pulmonary Embolism",
        expected_min_confidence=0.95,
        should_be_definitive=True
    ),
    TestCase(
        name="PE_Clinical_Suspicion",
        description="PE suspicion without definitive imaging - lower confidence expected",
        radiology="Chest X-ray shows Hampton hump",
        ecg="Sinus tachycardia, right axis deviation",
        symptoms="Dyspnea, leg swelling, recent long flight",
        labs="D-dimer elevated 1800",
        expected_diagnosis="Pulmonary Embolism",
        expected_min_confidence=0.15,  # Lower threshold for clinical suspicion
        should_be_definitive=False
    ),
    
    # ─────────── PNEUMONIA CASES ───────────
    TestCase(
        name="Pneumonia_Classic",
        description="Classic community-acquired pneumonia",
        radiology="Chest X-ray shows right lower lobe consolidation with air bronchograms",
        ecg="Normal sinus rhythm 88 bpm",
        symptoms="Productive cough with yellow sputum, fever 102F, chills, dyspnea",
        labs="WBC 15,000 with left shift, procalcitonin elevated",
        expected_diagnosis="Pneumonia",
        expected_min_confidence=0.80,  # High confidence for classic presentation
        should_be_definitive=True  # Consolidation + air bronchograms is diagnostic
    ),
    
    # ─────────── CARDIAC CASES ───────────
    TestCase(
        name="MI_STEMI",
        description="Acute STEMI presentation",
        radiology="Chest X-ray normal, no pulmonary edema",
        ecg="ST elevation in leads V1-V4 with reciprocal changes in II, III, aVF",
        symptoms="Crushing chest pain radiating to left arm, diaphoresis, nausea",
        labs="Troponin I 5.2 (highly elevated), CK-MB 85",
        expected_diagnosis="Myocardial Infarction",
        expected_min_confidence=0.80,  # High confidence for STEMI
        should_be_definitive=True  # ST elevation + troponin is diagnostic
    ),
    TestCase(
        name="Afib_New_Onset",
        description="New onset atrial fibrillation",
        radiology="Chest X-ray normal",
        ecg="Atrial fibrillation with irregularly irregular rhythm, absent P waves, ventricular rate 130",
        symptoms="Palpitations, fatigue, mild dyspnea on exertion",
        labs="TSH normal, BNP mildly elevated",
        expected_diagnosis="Atrial Fibrillation",
        expected_min_confidence=0.80,  # High confidence for classic AFib
        should_be_definitive=True  # Clear ECG findings
    ),
    
    # ─────────── NEGATIVE CASES ───────────
    TestCase(
        name="Normal_Workup",
        description="Patient with anxiety, all tests normal",
        radiology="Chest X-ray normal, no acute cardiopulmonary abnormality",
        ecg="Normal sinus rhythm at 72 bpm, normal axis, no ST changes",
        symptoms="Chest discomfort, anxiety, no risk factors",
        labs="CBC normal, BMP normal, troponin negative, D-dimer normal",
        expected_diagnosis="",  # No significant diagnosis expected
        expected_min_confidence=0.0,  # Accept any confidence since no diagnosis expected
        should_be_definitive=False
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARK RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

def run_diagnosis(case: TestCase) -> Tuple[Dict, float]:
    """Run a single diagnosis and return result with latency."""
    payload = {
        "radiology": case.radiology,
        "ecg": case.ecg,
        "symptoms_text": case.symptoms,
        "lab_text": case.labs,
        "explain": True
    }
    
    start = time.time()
    response = requests.post(f"{API_URL}/diagnose", json=payload)
    latency = (time.time() - start) * 1000  # ms
    
    return response.json(), latency


def check_diagnosis_match(result: Dict, expected: str) -> bool:
    """Check if expected diagnosis is in the result."""
    if not expected:
        # For negative cases, check that no significant diagnosis was made
        # Accept if top_diagnosis is None or empty or confidence is low
        top_diag = result.get("consensus", {}).get("top_diagnosis") or ""
        confidence = result.get("consensus", {}).get("confidence", 1.0)
        diagnoses = result.get("consensus", {}).get("diagnoses", {})
        # Pass if: no diagnosis, or empty diagnoses, or low confidence
        return (not top_diag or top_diag == "None" or not diagnoses or confidence < 0.5)
    
    top_diagnosis = result.get("consensus", {}).get("top_diagnosis", "") or ""
    diagnoses = result.get("consensus", {}).get("diagnoses", {}) or {}
    
    # Check if expected diagnosis is in top diagnosis or diagnoses
    expected_lower = expected.lower()
    return (expected_lower in top_diagnosis.lower() or 
            any(expected_lower in k.lower() for k in diagnoses.keys()))


def print_header():
    """Print benchmark header."""
    print("\n" + "═" * 80)
    print("                    MADN-X DIAGNOSTIC BENCHMARK SUITE")
    print("═" * 80)
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  API: {API_URL}")
    print("═" * 80 + "\n")


def print_result(case: TestCase, result: Dict, latency: float, passed: bool):
    """Print result for a single test case."""
    status = "✅ PASS" if passed else "❌ FAIL"
    
    consensus = result.get("consensus", {})
    top_diag = consensus.get("top_diagnosis", "N/A")
    confidence = consensus.get("confidence", 0)
    is_definitive = consensus.get("diagnostic_certainty", "") == "confirmed"
    
    print(f"  {status}  {case.name}")
    print(f"         Expected: {case.expected_diagnosis or 'Low confidence'}")
    print(f"         Got:      {top_diag}")
    print(f"         Confidence: {confidence:.1%} (min: {case.expected_min_confidence:.0%})")
    print(f"         Definitive: {is_definitive} (expected: {case.should_be_definitive})")
    print(f"         Latency: {latency:.0f}ms")
    print()


def run_benchmark():
    """Run the full benchmark suite."""
    print_header()
    
    results = []
    total_latency = 0
    passed_count = 0
    
    for case in BENCHMARK_CASES:
        print(f"  Running: {case.name}...")
        
        try:
            result, latency = run_diagnosis(case)
            total_latency += latency
            
            # Check if diagnosis matches
            diagnosis_match = check_diagnosis_match(result, case.expected_diagnosis)
            
            # Check confidence threshold
            confidence = result.get("consensus", {}).get("confidence", 0)
            confidence_ok = confidence >= case.expected_min_confidence
            
            # Check definitive status
            is_definitive = result.get("consensus", {}).get("diagnostic_certainty", "") == "confirmed"
            definitive_ok = is_definitive == case.should_be_definitive
            
            passed = diagnosis_match and confidence_ok and definitive_ok
            if passed:
                passed_count += 1
            
            results.append({
                "case": case.name,
                "passed": passed,
                "diagnosis_match": diagnosis_match,
                "confidence_ok": confidence_ok,
                "definitive_ok": definitive_ok,
                "latency_ms": latency,
                "result": result
            })
            
            print_result(case, result, latency, passed)
            
        except Exception as e:
            print(f"  ❌ ERROR: {case.name} - {str(e)}\n")
            results.append({
                "case": case.name,
                "passed": False,
                "error": str(e)
            })
    
    # Print summary
    print("═" * 80)
    print("                              BENCHMARK SUMMARY")
    print("═" * 80)
    print(f"  Total Cases:     {len(BENCHMARK_CASES)}")
    print(f"  Passed:          {passed_count}")
    print(f"  Failed:          {len(BENCHMARK_CASES) - passed_count}")
    print(f"  Pass Rate:       {passed_count / len(BENCHMARK_CASES):.1%}")
    print(f"  Avg Latency:     {total_latency / len(BENCHMARK_CASES):.0f}ms")
    print("═" * 80)
    
    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": len(BENCHMARK_CASES),
            "passed": passed_count,
            "failed": len(BENCHMARK_CASES) - passed_count,
            "pass_rate": passed_count / len(BENCHMARK_CASES),
            "avg_latency_ms": total_latency / len(BENCHMARK_CASES)
        },
        "results": results
    }
    
    with open("tests/benchmark_results.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"\n  Results saved to: tests/benchmark_results.json")
    print("═" * 80 + "\n")
    
    return output


if __name__ == "__main__":
    run_benchmark()
