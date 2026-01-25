# app/agents/pulmonologist.py
"""
Pulmonologist Agent for MADN-X Multi-Agent Diagnostic System

This agent interprets respiratory symptoms, physical exam findings, and 
clinical history to generate pulmonary diagnostic hypotheses.

Supported Conditions:
- Pneumonia (community-acquired, hospital-acquired)
- COPD Exacerbation
- Asthma Exacerbation
- Pulmonary Embolism
- Tuberculosis
- Respiratory infections
"""

import re
from typing import Dict, List, Any
from app.core.evidence_layer import (
    Evidence, Finding, DiagnosticHypothesis,
    EvidenceType, EvidenceStrength, Severity, calculate_confidence
)
from app.core.disease_modules import (
    PNEUMONIA, COPD_EXACERBATION, ASTHMA_EXACERBATION, 
    PULMONARY_EMBOLISM, TUBERCULOSIS
)

# ============================================================================
# SYMPTOM PATTERN RECOGNITION
# ============================================================================

SYMPTOM_PATTERNS = {
    # Respiratory symptoms
    "cough": {
        "patterns": [r"\bcough\w*\b", r"hacking", r"barking\s*cough"],
        "finding": "Cough",
        "significance": "Common respiratory symptom - assess duration and character",
        "severity": Severity.LOW,
        "diseases": ["pneumonia", "copd", "asthma", "tb"]
    },
    "productive_cough": {
        "patterns": [
            r"productive\s*cough",
            r"cough\w*\s*(with|producing)\s*sputum",
            r"sputum\s*production",
            r"phlegm",
            r"mucus\s*production"
        ],
        "finding": "Productive Cough",
        "significance": "Suggests lower respiratory infection or chronic bronchitis",
        "severity": Severity.MODERATE,
        "diseases": ["pneumonia", "copd"]
    },
    "purulent_sputum": {
        "patterns": [
            r"(yellow|green|purulent)\s*sputum",
            r"sputum\s*(is\s*)?(yellow|green|purulent)",
            r"colored\s*sputum"
        ],
        "finding": "Purulent Sputum",
        "significance": "Suggests bacterial infection",
        "severity": Severity.MODERATE,
        "diseases": ["pneumonia", "copd"]
    },
    "hemoptysis": {
        "patterns": [
            r"hemoptysis",
            r"blood.?(tinged|streaked)\s*sputum",
            r"coughing\s*(up\s*)?blood",
            r"bloody\s*sputum"
        ],
        "finding": "Hemoptysis",
        "significance": "Alarming symptom - consider TB, malignancy, PE, or severe infection",
        "severity": Severity.HIGH,
        "diseases": ["tb", "pulmonary_embolism"]
    },
    
    # Dyspnea patterns
    "dyspnea": {
        "patterns": [
            r"dyspnea",
            r"short(ness)?\s*(of\s*)?breath",
            r"\bsob\b",
            r"breathing\s*difficulty",
            r"breathless"
        ],
        "finding": "Dyspnea",
        "significance": "Cardinal respiratory symptom - assess onset, severity, and triggers",
        "severity": Severity.MODERATE,
        "diseases": ["pneumonia", "copd", "asthma", "pulmonary_embolism"]
    },
    "exertional_dyspnea": {
        "patterns": [
            r"dyspnea\s*(on|with)\s*exertion",
            r"exertional\s*dyspnea",
            r"short\s*of\s*breath\s*(on|with)\s*(exertion|activity|walking)"
        ],
        "finding": "Exertional Dyspnea",
        "significance": "Progressive disease - consider COPD, heart failure, or deconditioning",
        "severity": Severity.MODERATE,
        "diseases": ["copd"]
    },
    "sudden_dyspnea": {
        "patterns": [
            r"sudden\s*(onset\s*)?(of\s*)?(dyspnea|shortness|breathless)",
            r"acute\s*(onset\s*)?(of\s*)?(dyspnea|shortness)",
            r"abrupt\s*(onset\s*)?breathless"
        ],
        "finding": "Sudden Onset Dyspnea",
        "significance": "Red flag - consider PE, pneumothorax, or acute cardiac event",
        "severity": Severity.HIGH,
        "diseases": ["pulmonary_embolism"]
    },
    "orthopnea": {
        "patterns": [r"orthopnea", r"(can'?t|cannot|unable\s*to)\s*lie\s*flat", r"pillow\s*orthopnea"],
        "finding": "Orthopnea",
        "significance": "Suggests heart failure or severe respiratory disease",
        "severity": Severity.MODERATE,
        "diseases": []
    },
    
    # Chest symptoms
    "pleuritic_pain": {
        "patterns": [
            r"pleuritic\s*(chest\s*)?pain",
            r"sharp\s*chest\s*pain",
            r"chest\s*pain\s*(worse\s*)?(with|on)\s*breath",
            r"pain\s*on\s*(deep\s*)?inspiration"
        ],
        "finding": "Pleuritic Chest Pain",
        "significance": "Sharp pain worsening with breathing - consider pleurisy, PE, or pneumonia",
        "severity": Severity.MODERATE,
        "diseases": ["pneumonia", "pulmonary_embolism"]
    },
    "chest_tightness": {
        "patterns": [r"chest\s*tightness", r"tight\s*chest", r"constriction\s*in\s*chest"],
        "finding": "Chest Tightness",
        "significance": "Common in asthma and COPD exacerbations",
        "severity": Severity.LOW,
        "diseases": ["asthma", "copd"]
    },
    
    # Wheezing
    "wheezing": {
        "patterns": [r"wheez\w*", r"musical\s*breath\s*sounds?"],
        "finding": "Wheezing",
        "significance": "Indicates airway obstruction - asthma, COPD, or foreign body",
        "severity": Severity.MODERATE,
        "diseases": ["asthma", "copd"]
    },
    
    # Physical exam findings
    "crackles": {
        "patterns": [r"crackles?", r"crepitations?", r"rales?"],
        "finding": "Crackles/Rales",
        "significance": "Suggest alveolar or interstitial process - pneumonia, pulmonary edema, or fibrosis",
        "severity": Severity.MODERATE,
        "diseases": ["pneumonia"]
    },
    
    # Constitutional symptoms
    "fever": {
        "patterns": [
            r"\bfever\b",
            r"febrile",
            r"temperature\s*(of\s*)?\d+",
            r"pyrexia",
            r"(temp|temperature)\s*>\s*38",
            r"chills?"
        ],
        "finding": "Fever",
        "significance": "Suggests infectious process",
        "severity": Severity.MODERATE,
        "diseases": ["pneumonia", "tb"]
    },
    "night_sweats": {
        "patterns": [r"night\s*sweats?", r"nocturnal\s*(diaphoresis|sweating)"],
        "finding": "Night Sweats",
        "significance": "B symptom - consider TB, lymphoma, or other infections",
        "severity": Severity.MODERATE,
        "diseases": ["tb"]
    },
    "weight_loss": {
        "patterns": [r"weight\s*loss", r"lost\s*weight", r"unintentional\s*weight"],
        "finding": "Weight Loss",
        "significance": "B symptom - concerning for TB, malignancy, or chronic disease",
        "severity": Severity.MODERATE,
        "diseases": ["tb"]
    },
    
    # Risk factors
    "smoking": {
        "patterns": [
            r"smok\w*",
            r"(current|former|ex)\s*smoker",
            r"pack.?year",
            r"tobacco\s*use"
        ],
        "finding": "Smoking History",
        "significance": "Major risk factor for COPD, lung cancer, and cardiovascular disease",
        "severity": Severity.LOW,
        "diseases": ["copd"]
    },
    "dvt_risk": {
        "patterns": [
            r"(recent|leg)\s*surgery",
            r"immobil\w*",
            r"(long\s*)?(flight|travel)",
            r"leg\s*(swelling|pain|edema)",
            r"calf\s*(pain|tenderness|swelling)",
            r"dvt",
            r"deep\s*vein\s*thrombosis"
        ],
        "finding": "DVT Risk Factors",
        "significance": "Increases likelihood of pulmonary embolism",
        "severity": Severity.MODERATE,
        "diseases": ["pulmonary_embolism"]
    },
    "chronic_cough": {
        "patterns": [
            r"chronic\s*cough",
            r"cough\s*(for|>|more\s*than)\s*(2|3|4|\d+)\s*(weeks?|months?)",
            r"persistent\s*cough"
        ],
        "finding": "Chronic Cough",
        "significance": "Consider TB, COPD, or malignancy if >3 weeks",
        "severity": Severity.MODERATE,
        "diseases": ["tb", "copd"]
    }
}


def extract_symptoms(text: str) -> List[Finding]:
    """Extract symptom findings from clinical text."""
    findings = []
    text_lower = text.lower()
    matched_keys = set()
    
    for key, config in SYMPTOM_PATTERNS.items():
        if key in matched_keys:
            continue
        for pattern in config["patterns"]:
            if re.search(pattern, text_lower, re.IGNORECASE):
                evidence = Evidence(
                    type=EvidenceType.SYMPTOM,
                    description=f"Symptom identified: {config['finding']}",
                    value=config["finding"],
                    is_abnormal=True,
                    strength=EvidenceStrength.MODERATE,
                    source="clinical_history"
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


def build_pulmonary_hypotheses(findings: List[Finding]) -> List[DiagnosticHypothesis]:
    """Build pulmonary diagnostic hypotheses based on symptoms."""
    disease_scores: Dict[str, Dict] = {}
    
    # Map findings to diseases
    disease_key_map = {
        "pneumonia": PNEUMONIA,
        "copd": COPD_EXACERBATION,
        "asthma": ASTHMA_EXACERBATION,
        "pulmonary_embolism": PULMONARY_EMBOLISM,
        "tb": TUBERCULOSIS
    }
    
    for finding in findings:
        for key, config in SYMPTOM_PATTERNS.items():
            if finding.name == config["finding"]:
                for disease_key in config["diseases"]:
                    if disease_key not in disease_scores:
                        disease_scores[disease_key] = {"findings": [], "evidence": [], "severity_max": Severity.NORMAL}
                    disease_scores[disease_key]["findings"].append(finding.name)
                    disease_scores[disease_key]["evidence"].extend(finding.evidence)
                    if finding.severity.value > disease_scores[disease_key]["severity_max"].value:
                        disease_scores[disease_key]["severity_max"] = finding.severity
    
    hypotheses = []
    for disease_key, score_data in disease_scores.items():
        if disease_key not in disease_key_map:
            continue
        disease = disease_key_map[disease_key]
        
        # Check symptom criteria match
        criteria_met = []
        for symptom in disease.typical_symptoms:
            if any(symptom.lower() in f.lower() for f in score_data["findings"]):
                criteria_met.append(symptom)
        
        # Symptoms alone provide moderate probability
        finding_count = len(score_data["findings"])
        criteria_match = len(criteria_met) / max(len(disease.typical_symptoms), 1)
        probability = min(0.65, criteria_match * 0.4 + (finding_count * 0.05))
        
        # Boost for high severity findings
        if score_data["severity_max"] == Severity.HIGH:
            probability += 0.1
        
        if probability > 0.15:
            hypotheses.append(DiagnosticHypothesis(
                diagnosis=disease.name,
                icd10_code=disease.icd10_code,
                probability=round(probability, 3),
                supporting_evidence=score_data["evidence"],
                required_for_diagnosis=disease.major_criteria[:3],
                criteria_met=criteria_met,
                differential_diagnoses=disease.differential_diagnoses[:4],
                recommended_workup=["Chest X-ray", "Complete blood count", "Basic metabolic panel"],
                urgency=Severity(disease.default_urgency)
            ))
    
    hypotheses.sort(key=lambda h: h.probability, reverse=True)
    return hypotheses


def pulmonologist_agent(symptoms_text: str) -> Dict[str, Any]:
    """Main pulmonologist agent function."""
    if not symptoms_text or not symptoms_text.strip():
        return {
            "agent": "pulmonologist",
            "input_snippet": "",
            "diagnoses": {},
            "top_diagnosis": "No symptom data provided",
            "confidence": 0.0,
            "explanation": "No clinical history or symptoms provided",
            "findings": [],
            "hypotheses": [],
            "flags": ["INCOMPLETE_DATA"]
        }
    
    findings = extract_symptoms(symptoms_text)
    hypotheses = build_pulmonary_hypotheses(findings)
    
    if hypotheses:
        top = hypotheses[0]
        primary_impression = f"{top.diagnosis} (probability: {top.probability:.0%})"
        explanation = f"Based on symptoms: {', '.join([f.name for f in findings[:4]])}"
    elif findings:
        primary_impression = f"Respiratory symptoms: {findings[0].name}"
        explanation = "Symptoms identified but no specific diagnosis pattern matched"
    else:
        primary_impression = "No specific pulmonary abnormality identified"
        explanation = "No concerning respiratory symptoms identified in the provided text"
    
    # Calculate confidence
    high_severity = sum(1 for f in findings if f.severity == Severity.HIGH)
    confidence = calculate_confidence(
        evidence_count=len(findings),
        strong_evidence_count=high_severity,
        weak_evidence_count=len(findings) - high_severity,
        criteria_met_ratio=len(hypotheses) / 5 if hypotheses else 0.0
    ) if findings else 0.3
    
    # Build flags
    flags = []
    for finding in findings:
        if finding.severity == Severity.HIGH:
            flags.append(f"ALERT: {finding.name} - {finding.clinical_significance}")
    
    return {
        "agent": "pulmonologist",
        "input_snippet": symptoms_text[:200],
        "diagnoses": {h.diagnosis: h.probability for h in hypotheses},
        "top_diagnosis": primary_impression,
        "confidence": confidence,
        "explanation": explanation,
        "findings": [f.to_dict() for f in findings],
        "hypotheses": [h.to_dict() for h in hypotheses],
        "flags": flags
    }
