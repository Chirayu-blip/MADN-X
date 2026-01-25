# app/agents/radiologist.py
"""
Radiologist Agent for MADN-X Multi-Agent Diagnostic System

This agent interprets chest imaging (X-ray, CT) findings and provides
structured diagnostic hypotheses based on radiological patterns.

Supported Findings:
- Pneumonia patterns (consolidation, infiltrates, air bronchograms)
- Heart failure signs (cardiomegaly, pulmonary edema, effusions)
- COPD/Emphysema (hyperinflation, bullae)
- Pulmonary embolism (Hampton's hump, Westermark sign)
- Tuberculosis (cavitary lesions, upper lobe infiltrates)
- Pleural abnormalities (effusion, pneumothorax)
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from openai import OpenAI
import os

from app.core.evidence_layer import (
    Evidence, Finding, DiagnosticHypothesis, AgentReport,
    EvidenceType, EvidenceStrength, Severity, calculate_confidence
)
from app.core.disease_modules import (
    PNEUMONIA, HEART_FAILURE, COPD_EXACERBATION, PULMONARY_EMBOLISM,
    TUBERCULOSIS
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ============================================================================
# DEFINITIVE DIAGNOSTIC FINDINGS - Gold standard evidence that confirms diagnosis
# When these are found, the diagnosis is CONFIRMED, not suspected
# ============================================================================

DEFINITIVE_FINDINGS = {
    "pulmonary_embolism": {
        "patterns": [
            r"filling\s*defect\s*(in|of)\s*(the)?\s*(main|right|left|segmental|subsegmental)?\s*pulmonary\s*arter",
            r"ct(pa|\s*angiogra\w*)\s*(show\w*|reveal\w*|demonstrat\w*)?\s*.*filling\s*defect",
            r"thrombus\s*(in|within)\s*(the)?\s*pulmonary\s*arter",
            r"pulmonary\s*embol\w*\s*(confirm\w*|diagnos\w*|identified|seen|visuali)"
        ],
        "diagnosis": "Pulmonary Embolism",
        "confidence": 0.98,
        "explanation": "CTPA filling defect is DIAGNOSTIC of PE - gold standard imaging",
        "icd10": "I26.99"
    },
    "pneumothorax": {
        "patterns": [
            r"pneumothorax\s*(identified|confirmed|present|seen)",
            r"absence\s*of\s*lung\s*markings",
            r"visceral\s*pleural\s*line"
        ],
        "diagnosis": "Pneumothorax",
        "confidence": 0.95,
        "explanation": "Direct visualization of pneumothorax on imaging",
        "icd10": "J93.9"
    },
    "lobar_pneumonia": {
        "patterns": [
            r"lobar\s*consolidation\s*(with)?\s*air\s*bronchogram",
            r"complete\s*opacification\s*of\s*(the)?\s*\w+\s*lobe"
        ],
        "diagnosis": "Community-Acquired Pneumonia",
        "confidence": 0.92,
        "explanation": "Classic lobar consolidation pattern diagnostic of pneumonia",
        "icd10": "J18.1"
    },
    "consolidation_pneumonia": {
        "patterns": [
            r"consolidat\w*\s*(with)?\s*air\s*bronchogram",
            r"(right|left|lower|upper|middle)\s*(lobe)?\s*consolidat\w*",
            r"air\s*bronchogram\w*\s*(within|in)\s*consolidat"
        ],
        "diagnosis": "Community-Acquired Pneumonia",
        "confidence": 0.85,
        "explanation": "Consolidation with air bronchograms strongly suggests pneumonia",
        "icd10": "J18.9"
    }
}

# ============================================================================
# RADIOLOGICAL PATTERN RECOGNITION
# ============================================================================

IMAGING_PATTERNS = {
    # Pneumonia patterns
    "consolidation": {
        "patterns": [r"consolidat\w*", r"air\s*bronchogram", r"lobar\s*(opacity|infiltrate)"],
        "finding": "Consolidation",
        "significance": "Suggests airspace disease, commonly pneumonia",
        "severity": Severity.MODERATE,
        "diseases": ["pneumonia"]
    },
    "infiltrate": {
        "patterns": [r"infiltrat\w*", r"patchy\s*opacit\w*", r"airspace\s*disease"],
        "finding": "Pulmonary Infiltrate",
        "significance": "Suggests infection or inflammatory process",
        "severity": Severity.MODERATE,
        "diseases": ["pneumonia"]
    },
    # Heart failure patterns
    "cardiomegaly": {
        "patterns": [r"cardiomegal\w*", r"enlarged\s*heart", r"cardiac\s*enlargement", r"ctr\s*>\s*0\.5"],
        "finding": "Cardiomegaly",
        "significance": "Suggests cardiac disease, may indicate heart failure",
        "severity": Severity.MODERATE,
        "diseases": ["heart_failure"]
    },
    "pulmonary_edema": {
        "patterns": [r"pulmonary\s*edema", r"bat\s*wing", r"perihilar\s*haze", r"kerley\s*b\s*lines?"],
        "finding": "Pulmonary Edema",
        "significance": "Indicates fluid in lungs, commonly from heart failure",
        "severity": Severity.HIGH,
        "diseases": ["heart_failure"]
    },
    "cephalization": {
        "patterns": [r"cephalization", r"upper\s*lobe\s*diversion", r"pulmonary\s*vascular\s*congestion"],
        "finding": "Pulmonary Vascular Congestion",
        "significance": "Early sign of elevated left atrial pressure",
        "severity": Severity.MODERATE,
        "diseases": ["heart_failure"]
    },
    # Pleural abnormalities
    "pleural_effusion": {
        "patterns": [r"pleural\s*effusion", r"blunting\s*(of\s*)?(costophrenic|cp)\s*angle", r"pleural\s*fluid"],
        "finding": "Pleural Effusion",
        "significance": "Can be from CHF, infection, malignancy, or other causes",
        "severity": Severity.MODERATE,
        "diseases": ["heart_failure", "pneumonia"]
    },
    # COPD/Emphysema patterns
    "hyperinflation": {
        "patterns": [r"hyperinflat\w*", r"flattened\s*diaphragm", r"increased\s*ap\s*diameter"],
        "finding": "Hyperinflation",
        "significance": "Suggests obstructive lung disease (COPD/emphysema)",
        "severity": Severity.LOW,
        "diseases": ["copd_exacerbation"]
    },
    "emphysema": {
        "patterns": [r"emphysema\w*", r"bullae", r"bullous\s*change"],
        "finding": "Emphysematous Changes",
        "significance": "Indicates chronic obstructive lung disease",
        "severity": Severity.MODERATE,
        "diseases": ["copd_exacerbation"]
    },
    # PE patterns - CRITICAL: Filling defect on CTPA is DIAGNOSTIC
    "filling_defect": {
        "patterns": [
            r"filling\s*defect",
            r"pulmonary\s*embol\w*",
            r"thrombus\s*(in|within)\s*(the)?\s*pulmonary",
            r"ct\s*angiogra\w*\s*show\w*",
            r"ctpa\s*(show\w*|positive|confirm)"
        ],
        "finding": "Pulmonary Artery Filling Defect",
        "significance": "DIAGNOSTIC of pulmonary embolism - gold standard test",
        "severity": Severity.CRITICAL,
        "diseases": ["pulmonary_embolism"],
        "is_definitive": True  # This finding CONFIRMS the diagnosis
    },
    # TB patterns
    "cavitary_lesion": {
        "patterns": [r"cavit\w*\s*(lesion|opacity)?", r"cavity", r"cavern"],
        "finding": "Cavitary Lesion",
        "significance": "Consider TB, fungal infection, or malignancy",
        "severity": Severity.HIGH,
        "diseases": ["tuberculosis"]
    },
    "upper_lobe_infiltrate": {
        "patterns": [r"(upper|apical)\s*lobe\s*(infiltrate|opacity|lesion)", r"apical\s*scarring"],
        "finding": "Upper Lobe Abnormality",
        "significance": "TB reactivation commonly affects upper lobes",
        "severity": Severity.MODERATE,
        "diseases": ["tuberculosis"]
    },
    # Other findings
    "atelectasis": {
        "patterns": [r"atelectasis", r"volume\s*loss"],
        "finding": "Atelectasis",
        "significance": "Lung collapse, various causes",
        "severity": Severity.LOW,
        "diseases": []
    },
    "normal": {
        "patterns": [r"no\s*(acute|significant)\s*(cardiopulmonary|abnormality)", r"clear\s*lungs", 
                     r"normal\s*(chest|study|exam)", r"unremarkable"],
        "finding": "No Acute Abnormality",
        "significance": "No significant findings",
        "severity": Severity.NORMAL,
        "diseases": []
    }
}


def check_definitive_findings(text: str) -> Optional[Dict[str, Any]]:
    """
    Check for DEFINITIVE diagnostic findings that confirm a diagnosis.
    When these are found, the diagnosis is CONFIRMED (not suspected).
    Returns the definitive finding info if found, None otherwise.
    """
    text_lower = text.lower()
    
    for condition, config in DEFINITIVE_FINDINGS.items():
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


def _is_negated(text: str, match_start: int) -> bool:
    """Check if a finding is negated (e.g., 'no pulmonary edema')."""
    # Look at the 30 characters before the match
    prefix = text[max(0, match_start - 30):match_start].lower()
    negation_patterns = [
        r"\bno\b", r"\bnot\b", r"\bwithout\b", r"\babsent\b", r"\bnegative\b",
        r"\brules?\s*out\b", r"\bdenies?\b", r"\bexcludes?\b", r"\bno\s*evidence\b",
        r"\bunremarkable\b", r"\bnormal\b"
    ]
    for neg in negation_patterns:
        if re.search(neg, prefix):
            return True
    return False


def extract_findings(text: str) -> List[Finding]:
    """Extract radiological findings from text using pattern matching with negation detection."""
    findings = []
    text_lower = text.lower()
    
    for key, config in IMAGING_PATTERNS.items():
        for pattern in config["patterns"]:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                # Check if this finding is negated
                if _is_negated(text_lower, match.start()):
                    continue  # Skip negated findings
                    
                evidence = Evidence(
                    type=EvidenceType.IMAGING,
                    description=f"Pattern matched: {pattern}",
                    value=config["finding"],
                    is_abnormal=config["severity"] != Severity.NORMAL,
                    strength=EvidenceStrength.STRONG if config["severity"] in [Severity.HIGH, Severity.CRITICAL] else EvidenceStrength.MODERATE,
                    source="radiology_report"
                )
                finding = Finding(
                    name=config["finding"],
                    present=True,
                    evidence=[evidence],
                    clinical_significance=config["significance"],
                    severity=config["severity"]
                )
                findings.append(finding)
                break
    return findings


def build_hypotheses(findings: List[Finding]) -> List[DiagnosticHypothesis]:
    """Build diagnostic hypotheses based on findings."""
    disease_scores: Dict[str, Dict] = {}
    
    for finding in findings:
        for key, config in IMAGING_PATTERNS.items():
            if finding.name == config["finding"]:
                for disease_key in config["diseases"]:
                    if disease_key not in disease_scores:
                        disease_scores[disease_key] = {"findings": [], "critical": False, "definitive": False, "evidence": []}
                    disease_scores[disease_key]["findings"].append(finding.name)
                    disease_scores[disease_key]["evidence"].extend(finding.evidence)
                    if finding.severity == Severity.CRITICAL:
                        disease_scores[disease_key]["critical"] = True
                    # Check if this is a DEFINITIVE diagnostic finding
                    if config.get("is_definitive"):
                        disease_scores[disease_key]["definitive"] = True
    
    disease_map = {
        "pneumonia": PNEUMONIA,
        "heart_failure": HEART_FAILURE,
        "copd_exacerbation": COPD_EXACERBATION,
        "pulmonary_embolism": PULMONARY_EMBOLISM,
        "tuberculosis": TUBERCULOSIS
    }
    
    hypotheses = []
    for disease_key, score_data in disease_scores.items():
        if disease_key not in disease_map:
            continue
        disease = disease_map[disease_key]
        criteria_met = [c for c in disease.imaging_findings if any(c.lower() in f.lower() for f in score_data["findings"])]
        match_ratio = len(criteria_met) / max(len(disease.imaging_findings), 1)
        
        # CRITICAL FIX: Definitive findings = confirmed diagnosis (0.95+)
        # Critical findings = high probability (0.80-0.92)
        if score_data.get("definitive"):
            probability = 0.96  # Definitive diagnostic finding
        elif score_data["critical"]:
            probability = max(0.85, match_ratio * 0.8 + 0.15)  # Critical finding
        else:
            probability = min(0.75, match_ratio * 0.7 + 0.1)  # Supportive finding
        
        if probability > 0.2:
            hypotheses.append(DiagnosticHypothesis(
                diagnosis=disease.name,
                icd10_code=disease.icd10_code,
                probability=round(probability, 3),
                supporting_evidence=score_data["evidence"],
                required_for_diagnosis=disease.major_criteria[:3],
                criteria_met=criteria_met,
                differential_diagnoses=disease.differential_diagnoses[:3],
                urgency=Severity.CRITICAL if score_data["critical"] else Severity(disease.default_urgency)
            ))
    
    hypotheses.sort(key=lambda h: h.probability, reverse=True)
    return hypotheses


def get_gpt_interpretation(text: str, findings: List[Finding]) -> Dict[str, Any]:
    """Get GPT interpretation for complex cases."""
    findings_summary = "\n".join([f"- {f.name}: {f.clinical_significance}" for f in findings])
    
    prompt = f"""You are a radiologist interpreting chest imaging.

Report: "{text}"

Identified findings:
{findings_summary if findings else "No specific patterns identified"}

Provide interpretation in JSON format:
{{
    "impression": "Brief overall impression",
    "primary_diagnosis": "Most likely diagnosis",
    "confidence": 0.0-1.0,
    "recommendations": ["Clinical recommendations"]
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
    
    return {"impression": "Unable to generate interpretation", "primary_diagnosis": "Requires review", "confidence": 0.3, "recommendations": []}


def radiologist_agent(radiology_text: str) -> Dict[str, Any]:
    """Main radiologist agent function."""
    if not radiology_text or not radiology_text.strip():
        return {
            "agent": "radiologist",
            "input_snippet": "",
            "diagnoses": {},
            "top_diagnosis": "No imaging data provided",
            "confidence": 0.0,
            "explanation": "No radiology report provided",
            "findings": [],
            "hypotheses": [],
            "flags": ["INCOMPLETE_DATA"],
            "is_definitive": False
        }
    
    # STEP 1: Check for DEFINITIVE diagnostic findings first
    # These are gold-standard findings that CONFIRM a diagnosis
    definitive = check_definitive_findings(radiology_text)
    
    if definitive:
        # When definitive finding found, diagnosis is CONFIRMED
        return {
            "agent": "radiologist",
            "input_snippet": radiology_text[:200],
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
    
    # STEP 2: Standard pattern matching for non-definitive cases
    findings = extract_findings(radiology_text)
    hypotheses = build_hypotheses(findings)
    gpt_result = get_gpt_interpretation(radiology_text, findings)
    
    if hypotheses:
        top = hypotheses[0]
        primary_impression = f"{top.diagnosis} (probability: {top.probability:.0%})"
        # If any hypothesis has critical severity, boost confidence
        has_critical = any(h.urgency == Severity.CRITICAL for h in hypotheses)
    else:
        primary_impression = gpt_result.get("primary_diagnosis", "No significant abnormality")
        has_critical = False
    
    strong_evidence = sum(1 for f in findings if f.severity in [Severity.HIGH, Severity.CRITICAL])
    
    # Confidence calculation - higher for critical findings
    if has_critical and strong_evidence > 0:
        confidence = min(0.92, 0.75 + (strong_evidence * 0.1))
    elif strong_evidence > 0:
        confidence = calculate_confidence(
            evidence_count=len(findings),
            strong_evidence_count=strong_evidence,
            weak_evidence_count=len(findings) - strong_evidence,
            criteria_met_ratio=len(hypotheses) / 5 if hypotheses else 0.0
        )
    else:
        confidence = 0.4 if findings else 0.3
    
    flags = [f"CRITICAL: {f.name}" for f in findings if f.severity == Severity.CRITICAL]
    
    return {
        "agent": "radiologist",
        "input_snippet": radiology_text[:200],
        "diagnoses": {h.diagnosis: h.probability for h in hypotheses},
        "top_diagnosis": primary_impression,
        "confidence": confidence,
        "explanation": gpt_result.get("impression", primary_impression),
        "findings": [f.to_dict() for f in findings],
        "hypotheses": [h.to_dict() for h in hypotheses],
        "flags": flags,
        "is_definitive": False,
        "diagnostic_certainty": "suspected",
        "recommendations": gpt_result.get("recommendations", [])
    }
