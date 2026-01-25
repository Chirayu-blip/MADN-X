# app/agents/cardiologist.py
"""
Cardiologist Agent for MADN-X Multi-Agent Diagnostic System

This agent interprets ECG findings and provides structured diagnostic
hypotheses based on electrocardiographic patterns.

Supported Conditions:
- Acute Coronary Syndromes (STEMI, NSTEMI)
- Arrhythmias (AF, VT, bradycardia, tachycardia)
- Pericarditis
- Heart failure indicators
- Pulmonary embolism ECG signs
"""

import json
import re
from typing import Dict, List, Any, Optional
from openai import OpenAI
import os

from app.core.evidence_layer import (
    Evidence, Finding, DiagnosticHypothesis, AgentReport,
    EvidenceType, EvidenceStrength, Severity, calculate_confidence
)
from app.core.disease_modules import (
    STEMI, NSTEMI, ATRIAL_FIBRILLATION, PERICARDITIS, PULMONARY_EMBOLISM, HEART_FAILURE
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ============================================================================
# DEFINITIVE CARDIAC FINDINGS - Gold standard evidence that confirms diagnosis
# ============================================================================

DEFINITIVE_CARDIAC_FINDINGS = {
    "stemi": {
        "patterns": [
            r"st\s*(segment)?\s*elevation\s*(in\s*)?(leads?)?\s*(v[1-6]|i|ii|iii|avf|avl|avr)",
            r"stemi",
            r"st\s*elevat\w*\s*(with|and)\s*reciprocal",
            r"acute\s*(anterior|inferior|lateral)\s*(wall)?\s*(stemi|mi|infarct)"
        ],
        "diagnosis": "ST-Elevation Myocardial Infarction",
        "confidence": 0.92,
        "explanation": "ST elevation in contiguous leads with reciprocal changes is diagnostic of STEMI",
        "icd10": "I21.3"
    },
    "atrial_fibrillation": {
        "patterns": [
            r"atrial\s*fibrillation",
            r"a\s*fib",
            r"afib",
            r"irregularly\s*irregular\s*(rhythm)?\s*(with)?\s*(absent|no)\s*p\s*waves?"
        ],
        "diagnosis": "Atrial Fibrillation",
        "confidence": 0.90,
        "explanation": "Irregularly irregular rhythm with absent P waves is diagnostic of atrial fibrillation",
        "icd10": "I48.91"
    }
}


def check_definitive_cardiac_findings(text: str) -> Optional[Dict[str, Any]]:
    """Check for definitive cardiac diagnostic findings."""
    text_lower = text.lower()
    
    for condition, config in DEFINITIVE_CARDIAC_FINDINGS.items():
        for pattern in config["patterns"]:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return {
                    "condition": condition,
                    "diagnosis": config["diagnosis"],
                    "confidence": config["confidence"],
                    "explanation": config["explanation"],
                    "icd10": config["icd10"],
                    "is_definitive": True
                }
    return None


# ============================================================================
# ECG PATTERN RECOGNITION - Based on clinical ECG interpretation guidelines
# ============================================================================

ECG_PATTERNS = {
    # STEMI patterns - CRITICAL
    "st_elevation": {
        "patterns": [
            r"st\s*(segment)?\s*elevation",
            r"stemi",
            r"st\s*elevat\w*\s*(in|lead)",
            r"acute\s*mi",
            r"transmural\s*(infarct|ischemia)"
        ],
        "finding": "ST Elevation",
        "significance": "Acute transmural ischemia - STEMI until proven otherwise",
        "severity": Severity.CRITICAL,
        "diseases": ["stemi"],
        "leads_matter": True  # Location-specific interpretation
    },
    "reciprocal_depression": {
        "patterns": [r"reciprocal\s*(st)?\s*depression", r"mirror\s*image\s*change"],
        "finding": "Reciprocal ST Depression",
        "significance": "Supports diagnosis of acute STEMI",
        "severity": Severity.HIGH,
        "diseases": ["stemi"]
    },
    "hyperacute_t": {
        "patterns": [r"hyperacute\s*t\s*wave", r"tall\s*peaked\s*t\s*wave"],
        "finding": "Hyperacute T Waves",
        "significance": "Very early sign of acute MI",
        "severity": Severity.CRITICAL,
        "diseases": ["stemi"]
    },
    
    # NSTEMI/Ischemia patterns
    "st_depression": {
        "patterns": [
            r"st\s*(segment)?\s*depression",
            r"st\s*depress\w*",
            r"horizontal\s*st\s*depression",
            r"downsloping\s*st"
        ],
        "finding": "ST Depression",
        "significance": "Suggests subendocardial ischemia or NSTEMI",
        "severity": Severity.HIGH,
        "diseases": ["nstemi"]
    },
    "t_wave_inversion": {
        "patterns": [
            r"t\s*wave\s*inversion",
            r"inverted\s*t\s*wave",
            r"deep\s*t\s*wave\s*inversion",
            r"wellens"  # Wellens syndrome
        ],
        "finding": "T Wave Inversion",
        "significance": "May indicate ischemia, prior infarct, or other pathology",
        "severity": Severity.MODERATE,
        "diseases": ["nstemi"]
    },
    
    # Arrhythmias
    "atrial_fibrillation": {
        "patterns": [
            r"atrial\s*fibrillation",
            r"a\s*fib",
            r"afib",
            r"irregularly\s*irregular",
            r"no\s*p\s*waves?\s*(with|and)\s*irregular",
            r"fibrillatory\s*waves?"
        ],
        "finding": "Atrial Fibrillation",
        "significance": "Irregular rhythm with stroke risk - needs rate/rhythm control and anticoagulation assessment",
        "severity": Severity.MODERATE,
        "diseases": ["atrial_fibrillation"]
    },
    "atrial_flutter": {
        "patterns": [r"atrial\s*flutter", r"sawtooth\s*(pattern|waves?)", r"flutter\s*waves?"],
        "finding": "Atrial Flutter",
        "significance": "Regular atrial tachyarrhythmia, often 2:1 or 4:1 block",
        "severity": Severity.MODERATE,
        "diseases": ["atrial_fibrillation"]  # Similar management
    },
    "ventricular_tachycardia": {
        "patterns": [
            r"ventricular\s*tachycardia",
            r"\bvt\b",
            r"wide\s*complex\s*tachycardia",
            r"monomorphic\s*vt",
            r"polymorphic\s*vt"
        ],
        "finding": "Ventricular Tachycardia",
        "significance": "Life-threatening arrhythmia - immediate intervention may be needed",
        "severity": Severity.CRITICAL,
        "diseases": []
    },
    "sinus_tachycardia": {
        "patterns": [
            r"sinus\s*tachycardia",
            r"(rate|hr)\s*(of\s*)?1[0-4]\d\s*bpm",
            r"(rate|hr)\s*(of\s*)?15\d\s*bpm",
            r"tachycardia\s*\d{3}"
        ],
        "finding": "Sinus Tachycardia",
        "significance": "May be physiologic or indicate underlying condition (infection, PE, pain, anxiety)",
        "severity": Severity.LOW,
        "diseases": ["pulmonary_embolism"]
    },
    "bradycardia": {
        "patterns": [r"bradycardia", r"(rate|hr)\s*(of\s*)?[3-5]\d\s*bpm", r"slow\s*(rate|rhythm)"],
        "finding": "Bradycardia",
        "significance": "May be physiologic or pathologic (heart block, medication, hypothyroidism)",
        "severity": Severity.MODERATE,
        "diseases": []
    },
    
    # Conduction abnormalities
    "lbbb": {
        "patterns": [r"left\s*bundle\s*branch\s*block", r"\blbbb\b", r"new\s*lbbb"],
        "finding": "Left Bundle Branch Block",
        "significance": "New LBBB with symptoms is STEMI equivalent",
        "severity": Severity.HIGH,
        "diseases": ["stemi", "heart_failure"]
    },
    "rbbb": {
        "patterns": [r"right\s*bundle\s*branch\s*block", r"\brbbb\b"],
        "finding": "Right Bundle Branch Block",
        "significance": "May be normal variant or indicate RV strain (PE, pulmonary HTN)",
        "severity": Severity.LOW,
        "diseases": ["pulmonary_embolism"]
    },
    "heart_block": {
        "patterns": [
            r"(complete|third|3rd)\s*(degree)?\s*(heart|av)\s*block",
            r"(second|2nd)\s*(degree)?\s*(heart|av)\s*block",
            r"mobitz\s*(type)?\s*(i|ii|1|2)",
            r"wenckebach"
        ],
        "finding": "AV Block",
        "significance": "Conduction system disease - may need pacing",
        "severity": Severity.HIGH,
        "diseases": []
    },
    
    # PE signs - NOTE: ECG is SUPPORTIVE evidence, not diagnostic for PE
    # CTPA is the gold standard. ECG signs suggest PE but don't confirm it.
    "s1q3t3": {
        "patterns": [r"s1q3t3", r"s1\s*q3\s*t3", r"s1\s*,?\s*q3\s*,?\s*t3"],
        "finding": "S1Q3T3 Pattern",
        "significance": "Classic sign suggesting PE, but low sensitivity (~20%). Supportive, not diagnostic.",
        "severity": Severity.HIGH,
        "diseases": ["pulmonary_embolism"],
        "evidence_role": "supportive"  # NOT diagnostic - needs CTPA for confirmation
    },
    "right_axis_deviation": {
        "patterns": [r"right\s*axis\s*deviation", r"rad\b"],
        "finding": "Right Axis Deviation",
        "significance": "May indicate RV strain from PE. Supportive evidence only.",
        "severity": Severity.LOW,
        "diseases": ["pulmonary_embolism"],
        "evidence_role": "supportive"
    },
    
    # Pericarditis
    "diffuse_st_elevation": {
        "patterns": [
            r"diffuse\s*st\s*elevation",
            r"widespread\s*st\s*elevation",
            r"st\s*elevation\s*(in\s*)?(multiple|all|many)\s*leads"
        ],
        "finding": "Diffuse ST Elevation",
        "significance": "Suggests pericarditis rather than focal ischemia",
        "severity": Severity.MODERATE,
        "diseases": ["pericarditis"]
    },
    "pr_depression": {
        "patterns": [r"pr\s*(segment)?\s*depression", r"depressed\s*pr"],
        "finding": "PR Depression",
        "significance": "Highly specific for acute pericarditis",
        "severity": Severity.MODERATE,
        "diseases": ["pericarditis"]
    },
    
    # LVH
    "lvh": {
        "patterns": [
            r"left\s*ventricular\s*hypertrophy",
            r"\blvh\b",
            r"voltage\s*criteria\s*(for|of)\s*lvh"
        ],
        "finding": "Left Ventricular Hypertrophy",
        "significance": "Suggests chronic hypertension or cardiomyopathy",
        "severity": Severity.LOW,
        "diseases": ["heart_failure"]
    },
    
    # PVCs
    "pvcs": {
        "patterns": [r"premature\s*ventricular\s*contraction", r"\bpvc\b", r"ventricular\s*ectop\w*"],
        "finding": "Premature Ventricular Contractions",
        "significance": "Usually benign, but frequent PVCs may indicate underlying disease",
        "severity": Severity.LOW,
        "diseases": []
    },
    
    # Normal
    "normal_sinus": {
        "patterns": [
            r"normal\s*sinus\s*rhythm",
            r"\bnsr\b",
            r"sinus\s*rhythm\s*(at\s*)?\d{2}\s*bpm",
            r"regular\s*rhythm"
        ],
        "finding": "Normal Sinus Rhythm",
        "significance": "Normal cardiac rhythm",
        "severity": Severity.NORMAL,
        "diseases": []
    }
}


def _is_negated_ecg(text: str, match_start: int) -> bool:
    """Check if an ECG finding is negated (e.g., 'no ST elevation')."""
    prefix = text[max(0, match_start - 30):match_start].lower()
    negation_patterns = [
        r"\bno\b", r"\bnot\b", r"\bwithout\b", r"\babsent\b", r"\bnegative\b",
        r"\brules?\s*out\b", r"\bno\s*evidence\b"
    ]
    for neg in negation_patterns:
        if re.search(neg, prefix):
            return True
    return False


def extract_ecg_findings(text: str) -> List[Finding]:
    """Extract ECG findings using clinical pattern matching with negation detection."""
    findings = []
    text_lower = text.lower()
    matched_keys = set()
    
    for key, config in ECG_PATTERNS.items():
        if key in matched_keys:
            continue
        for pattern in config["patterns"]:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                # Check for negation
                if _is_negated_ecg(text_lower, match.start()):
                    continue
                    
                evidence = Evidence(
                    type=EvidenceType.ECG,
                    description=f"ECG pattern: {config['finding']}",
                    value=config["finding"],
                    is_abnormal=config["severity"] != Severity.NORMAL,
                    strength=EvidenceStrength.STRONG if config["severity"] in [Severity.HIGH, Severity.CRITICAL] else EvidenceStrength.MODERATE,
                    source="ecg_interpretation"
                )
                finding = Finding(
                    name=config["finding"],
                    present=True,
                    evidence=[evidence],
                    clinical_significance=config["significance"],
                    severity=config["severity"]
                )
                findings.append(finding)
                matched_keys.add(key)
                break
    
    return findings


def build_cardiac_hypotheses(findings: List[Finding]) -> List[DiagnosticHypothesis]:
    """Build cardiac diagnostic hypotheses based on ECG findings."""
    disease_scores: Dict[str, Dict] = {}
    
    for finding in findings:
        for key, config in ECG_PATTERNS.items():
            if finding.name == config["finding"]:
                for disease_key in config["diseases"]:
                    if disease_key not in disease_scores:
                        disease_scores[disease_key] = {"findings": [], "critical": False, "evidence": []}
                    disease_scores[disease_key]["findings"].append(finding.name)
                    disease_scores[disease_key]["evidence"].extend(finding.evidence)
                    if finding.severity == Severity.CRITICAL:
                        disease_scores[disease_key]["critical"] = True
    
    disease_map = {
        "stemi": STEMI,
        "nstemi": NSTEMI,
        "atrial_fibrillation": ATRIAL_FIBRILLATION,
        "pericarditis": PERICARDITIS,
        "pulmonary_embolism": PULMONARY_EMBOLISM,
        "heart_failure": HEART_FAILURE
    }
    
    hypotheses = []
    for disease_key, score_data in disease_scores.items():
        if disease_key not in disease_map:
            continue
        disease = disease_map[disease_key]
        
        criteria_met = [c for c in disease.ecg_findings if any(c.lower() in f.lower() for f in score_data["findings"])]
        match_ratio = len(criteria_met) / max(len(disease.ecg_findings), 1)
        
        # ECG alone typically provides moderate probability - needs clinical correlation
        # BUT critical findings like STEMI should have high probability
        if score_data["critical"]:
            probability = min(0.90, match_ratio * 0.6 + 0.35)  # Critical findings get higher base
        else:
            probability = min(0.75, match_ratio * 0.5 + 0.15)
        
        if probability > 0.15:
            hypotheses.append(DiagnosticHypothesis(
                diagnosis=disease.name,
                icd10_code=disease.icd10_code,
                probability=round(probability, 3),
                supporting_evidence=score_data["evidence"],
                required_for_diagnosis=disease.major_criteria[:3],
                criteria_met=criteria_met,
                differential_diagnoses=disease.differential_diagnoses[:3],
                recommended_workup=["Troponin", "Clinical correlation", "Serial ECGs"] if "mi" in disease_key.lower() or disease_key == "stemi" or disease_key == "nstemi" else ["Clinical correlation"],
                urgency=Severity.CRITICAL if score_data["critical"] else Severity(disease.default_urgency)
            ))
    
    hypotheses.sort(key=lambda h: h.probability, reverse=True)
    return hypotheses


def get_gpt_ecg_interpretation(text: str, findings: List[Finding]) -> Dict[str, Any]:
    """Get GPT interpretation for ECG analysis."""
    findings_summary = "\n".join([f"- {f.name}: {f.clinical_significance}" for f in findings])
    
    prompt = f"""You are a cardiologist interpreting an ECG.

ECG Description: "{text}"

Identified findings:
{findings_summary if findings else "No specific abnormalities identified"}

Provide interpretation in JSON format:
{{
    "interpretation": "Brief ECG interpretation",
    "rhythm": "Identified rhythm",
    "rate_assessment": "Normal/Tachycardia/Bradycardia",
    "concerning_features": ["List any concerning features"],
    "confidence": 0.0-1.0,
    "urgent_action_needed": true/false
}}

Return ONLY valid JSON."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            timeout=15
        )
        raw = response.choices[0].message.content
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
    except:
        pass
    
    return {"interpretation": "Unable to generate interpretation", "rhythm": "Unknown", "confidence": 0.3}


def cardiologist_agent(ecg_text: str) -> Dict[str, Any]:
    """Main cardiologist agent function for ECG interpretation."""
    if not ecg_text or not ecg_text.strip():
        return {
            "agent": "cardiologist",
            "input_snippet": "",
            "diagnoses": {},
            "top_diagnosis": "No ECG data provided",
            "confidence": 0.0,
            "explanation": "No ECG report provided",
            "findings": [],
            "hypotheses": [],
            "flags": ["INCOMPLETE_DATA"]
        }
    
    # STEP 1: Check for DEFINITIVE cardiac findings first
    definitive = check_definitive_cardiac_findings(ecg_text)
    
    if definitive:
        return {
            "agent": "cardiologist",
            "input_snippet": ecg_text[:200],
            "diagnoses": {definitive["diagnosis"]: definitive["confidence"]},
            "top_diagnosis": f"{definitive['diagnosis']} - CONFIRMED",
            "confidence": definitive["confidence"],
            "explanation": definitive["explanation"],
            "findings": [{
                "name": f"Definitive finding for {definitive['diagnosis']}",
                "clinical_significance": definitive["explanation"],
                "severity": "critical"
            }],
            "hypotheses": [{
                "diagnosis": definitive["diagnosis"],
                "probability": definitive["confidence"],
                "icd10_code": definitive["icd10"],
                "is_confirmed": True
            }],
            "flags": [f"CONFIRMED DIAGNOSIS: {definitive['diagnosis']}"],
            "is_definitive": True,
            "diagnostic_certainty": "confirmed"
        }
    
    # STEP 2: Standard pattern matching
    findings = extract_ecg_findings(ecg_text)
    hypotheses = build_cardiac_hypotheses(findings)
    gpt_result = get_gpt_ecg_interpretation(ecg_text, findings)
    
    if hypotheses:
        top = hypotheses[0]
        primary_impression = f"{top.diagnosis} (probability: {top.probability:.0%})"
    elif findings:
        primary_impression = findings[0].name
    else:
        primary_impression = gpt_result.get("rhythm", "Normal Sinus Rhythm")
    
    strong_evidence = sum(1 for f in findings if f.severity in [Severity.HIGH, Severity.CRITICAL])
    confidence = calculate_confidence(
        evidence_count=len(findings),
        strong_evidence_count=strong_evidence,
        weak_evidence_count=len(findings) - strong_evidence,
        criteria_met_ratio=len(hypotheses) / 4 if hypotheses else 0.0
    ) if findings else 0.5
    
    flags = []
    for finding in findings:
        if finding.severity == Severity.CRITICAL:
            flags.append(f"CRITICAL: {finding.name} - Immediate attention required")
    if gpt_result.get("urgent_action_needed"):
        flags.append("GPT flagged urgent action needed")
    
    return {
        "agent": "cardiologist",
        "input_snippet": ecg_text[:200],
        "diagnoses": {h.diagnosis: h.probability for h in hypotheses},
        "top_diagnosis": primary_impression,
        "confidence": confidence,
        "explanation": gpt_result.get("interpretation", primary_impression),
        "findings": [f.to_dict() for f in findings],
        "hypotheses": [h.to_dict() for h in hypotheses],
        "flags": flags,
        "rhythm": gpt_result.get("rhythm", "Unknown"),
        "concerning_features": gpt_result.get("concerning_features", [])
    }
