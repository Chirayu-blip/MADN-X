# app/agents/pathologist.py
"""
Pathologist Agent for MADN-X Multi-Agent Diagnostic System

This agent interprets laboratory findings to support diagnostic hypotheses.
It focuses on labs relevant to respiratory and cardiac conditions.

Key Lab Categories:
- Inflammatory markers (WBC, CRP, ESR, Procalcitonin)
- Cardiac biomarkers (Troponin, BNP, NT-proBNP)
- Blood gases (pH, PaCO2, PaO2)
- Coagulation (D-dimer, PT/INR)
- Metabolic panel
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from app.core.evidence_layer import (
    Evidence, Finding, DiagnosticHypothesis,
    EvidenceType, EvidenceStrength, Severity, calculate_confidence
)
from app.core.disease_modules import (
    PNEUMONIA, COPD_EXACERBATION, PULMONARY_EMBOLISM,
    STEMI, NSTEMI, HEART_FAILURE
)

# ============================================================================
# LABORATORY PATTERN RECOGNITION
# Reference ranges and clinical significance based on standard guidelines
# ============================================================================

LAB_PATTERNS = {
    # Inflammatory Markers
    "leukocytosis": {
        "patterns": [
            r"wbc\s*(>|greater|elevated|high|\d+[,.]?\d*)\s*(\d+)?",
            r"leukocytosis",
            r"white\s*(blood\s*)?(cell|count)\s*(>|elevated|high)",
            r"wbc\s*\d+[,.]?\d*\s*(k|thousand|×10)"
        ],
        "finding": "Leukocytosis",
        "significance": "WBC >11,000/μL suggests infection or inflammation",
        "severity": Severity.MODERATE,
        "diseases": ["pneumonia"],
        "normal_range": "4,500-11,000/μL"
    },
    "leukopenia": {
        "patterns": [r"leukopenia", r"wbc\s*<\s*4", r"low\s*wbc", r"wbc\s*(decreased|low)"],
        "finding": "Leukopenia",
        "significance": "WBC <4,000/μL - may indicate overwhelming sepsis or viral infection",
        "severity": Severity.MODERATE,
        "diseases": ["pneumonia"]
    },
    "elevated_crp": {
        "patterns": [
            r"crp\s*(>|elevated|high|\d+)",
            r"c.?reactive\s*protein\s*(>|elevated|high)",
            r"elevated\s*crp"
        ],
        "finding": "Elevated CRP",
        "significance": "C-reactive protein elevation indicates inflammation/infection",
        "severity": Severity.MODERATE,
        "diseases": ["pneumonia"],
        "normal_range": "<3 mg/L"
    },
    "elevated_procalcitonin": {
        "patterns": [
            r"procalcitonin\s*(>|elevated|high|\d+)",
            r"pct\s*(>|elevated|\d+\.\d+)",
            r"elevated\s*procalcitonin"
        ],
        "finding": "Elevated Procalcitonin",
        "significance": "PCT >0.25 ng/mL suggests bacterial infection; >0.5 ng/mL strongly suggests bacterial etiology",
        "severity": Severity.MODERATE,
        "diseases": ["pneumonia"]
    },
    "elevated_esr": {
        "patterns": [r"esr\s*(>|elevated|high)", r"elevated\s*esr", r"sed\s*rate\s*(elevated|high)"],
        "finding": "Elevated ESR",
        "significance": "Erythrocyte sedimentation rate elevation - nonspecific inflammation",
        "severity": Severity.LOW,
        "diseases": []
    },
    
    # Cardiac Biomarkers
    "elevated_troponin": {
        "patterns": [
            r"troponin\s*(i|t)?\s*(>|elevated|positive|high|\d+)",
            r"elevated\s*troponin",
            r"trop\s*(positive|elevated|>)",
            r"troponin\s*\d+\.?\d*"
        ],
        "finding": "Elevated Troponin",
        "significance": "Cardiac troponin elevation indicates myocardial injury - CRITICAL for ACS",
        "severity": Severity.CRITICAL,
        "diseases": ["stemi", "nstemi", "pulmonary_embolism"],
        "normal_range": "<0.04 ng/mL (varies by assay)"
    },
    "elevated_bnp": {
        "patterns": [
            r"bnp\s*(>|elevated|high|\d+)",
            r"(nt.?pro.?)?bnp\s*(>|elevated|\d+)",
            r"elevated\s*(nt.?pro.?)?bnp",
            r"brain\s*natriuretic\s*peptide"
        ],
        "finding": "Elevated BNP/NT-proBNP",
        "significance": "BNP >100 pg/mL or NT-proBNP >300 pg/mL suggests heart failure",
        "severity": Severity.MODERATE,
        "diseases": ["heart_failure", "pulmonary_embolism"],
        "normal_range": "BNP <100 pg/mL; NT-proBNP <300 pg/mL"
    },
    "elevated_ck_mb": {
        "patterns": [r"ck.?mb\s*(>|elevated|high)", r"elevated\s*ck.?mb"],
        "finding": "Elevated CK-MB",
        "significance": "Creatine kinase MB elevation suggests myocardial injury",
        "severity": Severity.HIGH,
        "diseases": ["stemi", "nstemi"]
    },
    
    # Coagulation
    "elevated_ddimer": {
        "patterns": [
            r"d.?dimer\s*(>|elevated|positive|high|\d+)",
            r"elevated\s*d.?dimer",
            r"d.?dimer\s*\d+\s*(ng|μg|mcg)"
        ],
        "finding": "Elevated D-dimer",
        "significance": "D-dimer >500 ng/mL is sensitive (not specific) for VTE/PE",
        "severity": Severity.MODERATE,
        "diseases": ["pulmonary_embolism"],
        "normal_range": "<500 ng/mL (age-adjusted: age × 10 ng/mL if >50)"
    },
    
    # Blood Gases
    "hypoxemia": {
        "patterns": [
            r"(pao2|po2)\s*(<|low|\d+\s*mmhg)",
            r"hypoxemia",
            r"hypoxia",
            r"(oxygen|o2)\s*sat\w*\s*(<|low|\d+%?)",
            r"spo2\s*<\s*9\d"
        ],
        "finding": "Hypoxemia",
        "significance": "Low blood oxygen - indicates respiratory or cardiac dysfunction",
        "severity": Severity.HIGH,
        "diseases": ["pneumonia", "copd", "pulmonary_embolism"],
        "normal_range": "PaO2 80-100 mmHg; SpO2 95-100%"
    },
    "hypercapnia": {
        "patterns": [
            r"(paco2|pco2)\s*(>|elevated|high|\d+)",
            r"hypercapnia",
            r"co2\s*retention",
            r"respiratory\s*acidosis"
        ],
        "finding": "Hypercapnia",
        "significance": "Elevated CO2 suggests hypoventilation - common in COPD exacerbation",
        "severity": Severity.MODERATE,
        "diseases": ["copd"]
    },
    "respiratory_alkalosis": {
        "patterns": [r"respiratory\s*alkalosis", r"hyperventilat\w*", r"low\s*(paco2|pco2)"],
        "finding": "Respiratory Alkalosis",
        "significance": "Hyperventilation - may be seen in PE, anxiety, or compensation",
        "severity": Severity.LOW,
        "diseases": ["pulmonary_embolism"]
    },
    "acidosis": {
        "patterns": [
            r"(metabolic|respiratory)?\s*acidosis",
            r"ph\s*<\s*7\.3",
            r"low\s*ph"
        ],
        "finding": "Acidosis",
        "significance": "pH <7.35 - requires immediate assessment of etiology",
        "severity": Severity.HIGH,
        "diseases": []
    },
    
    # Metabolic
    "elevated_lactate": {
        "patterns": [
            r"lactate\s*(>|elevated|high|\d+)",
            r"elevated\s*lactate",
            r"lactic\s*acid\s*(>|elevated|high)"
        ],
        "finding": "Elevated Lactate",
        "significance": "Lactate >2 mmol/L suggests tissue hypoperfusion - sepsis marker",
        "severity": Severity.HIGH,
        "diseases": ["pneumonia"],  # Severe pneumonia with sepsis
        "normal_range": "<2 mmol/L"
    },
    "elevated_creatinine": {
        "patterns": [
            r"creatinine\s*(>|elevated|high|\d+)",
            r"elevated\s*creatinine",
            r"(acute\s*)?(kidney|renal)\s*(injury|failure|insufficiency)",
            r"aki"
        ],
        "finding": "Elevated Creatinine",
        "significance": "Renal dysfunction - may indicate cardiorenal syndrome or sepsis",
        "severity": Severity.MODERATE,
        "diseases": ["heart_failure"]
    },
    "hyponatremia": {
        "patterns": [r"hyponatremia", r"(sodium|na)\s*<\s*13\d", r"low\s*(sodium|na)"],
        "finding": "Hyponatremia",
        "significance": "Low sodium - may be dilutional in heart failure",
        "severity": Severity.MODERATE,
        "diseases": ["heart_failure"]
    },
    
    # Hematology
    "anemia": {
        "patterns": [
            r"anemia",
            r"(hb|hemoglobin)\s*<\s*\d+",
            r"(hgb|hb)\s*(low|decreased)",
            r"low\s*hemoglobin"
        ],
        "finding": "Anemia",
        "significance": "Low hemoglobin - various etiologies, may worsen cardiac conditions",
        "severity": Severity.MODERATE,
        "diseases": [],
        "normal_range": "Men: 13.5-17.5 g/dL; Women: 12-16 g/dL"
    },
    "thrombocytopenia": {
        "patterns": [r"thrombocytopenia", r"(platelet|plt)\s*<\s*15\d", r"low\s*platelet"],
        "finding": "Thrombocytopenia",
        "significance": "Low platelets - may indicate DIC in sepsis",
        "severity": Severity.MODERATE,
        "diseases": []
    },
    
    # TB specific
    "positive_afb": {
        "patterns": [r"afb\s*(smear\s*)?(positive|\+)", r"acid.?fast\s*(positive|\+)"],
        "finding": "Positive AFB Smear",
        "significance": "Acid-fast bacilli seen - highly suggestive of tuberculosis",
        "severity": Severity.HIGH,
        "diseases": ["tb"]
    }
}


def extract_lab_findings(text: str) -> List[Finding]:
    """Extract laboratory findings from text."""
    findings = []
    text_lower = text.lower()
    matched_keys = set()
    
    for key, config in LAB_PATTERNS.items():
        if key in matched_keys:
            continue
        for pattern in config["patterns"]:
            if re.search(pattern, text_lower, re.IGNORECASE):
                evidence = Evidence(
                    type=EvidenceType.LAB,
                    description=f"Lab finding: {config['finding']}",
                    value=config["finding"],
                    normal_range=config.get("normal_range"),
                    is_abnormal=True,
                    strength=EvidenceStrength.STRONG if config["severity"] in [Severity.HIGH, Severity.CRITICAL] else EvidenceStrength.MODERATE,
                    source="laboratory_results"
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


def build_lab_hypotheses(findings: List[Finding]) -> List[DiagnosticHypothesis]:
    """Build diagnostic hypotheses based on lab findings."""
    disease_scores: Dict[str, Dict] = {}
    
    disease_key_map = {
        "pneumonia": PNEUMONIA,
        "copd": COPD_EXACERBATION,
        "pulmonary_embolism": PULMONARY_EMBOLISM,
        "stemi": STEMI,
        "nstemi": NSTEMI,
        "heart_failure": HEART_FAILURE
    }
    
    for finding in findings:
        for key, config in LAB_PATTERNS.items():
            if finding.name == config["finding"]:
                for disease_key in config["diseases"]:
                    if disease_key not in disease_scores:
                        disease_scores[disease_key] = {
                            "findings": [],
                            "evidence": [],
                            "has_critical": False
                        }
                    disease_scores[disease_key]["findings"].append(finding.name)
                    disease_scores[disease_key]["evidence"].extend(finding.evidence)
                    if finding.severity == Severity.CRITICAL:
                        disease_scores[disease_key]["has_critical"] = True
    
    hypotheses = []
    for disease_key, score_data in disease_scores.items():
        if disease_key not in disease_key_map:
            continue
        disease = disease_key_map[disease_key]
        
        # Check lab criteria match
        criteria_met = []
        for lab, threshold in disease.lab_findings.items():
            if any(lab.lower() in f.lower() for f in score_data["findings"]):
                criteria_met.append(f"{lab}: {threshold}")
        
        # Labs alone typically provide supportive evidence, not definitive diagnosis
        finding_count = len(score_data["findings"])
        criteria_match = len(criteria_met) / max(len(disease.lab_findings), 1)
        probability = min(0.60, criteria_match * 0.35 + (finding_count * 0.08))
        
        # Critical findings boost probability
        if score_data["has_critical"]:
            probability = min(0.75, probability + 0.2)
        
        if probability > 0.15:
            hypotheses.append(DiagnosticHypothesis(
                diagnosis=disease.name,
                icd10_code=disease.icd10_code,
                probability=round(probability, 3),
                supporting_evidence=score_data["evidence"],
                required_for_diagnosis=list(disease.lab_findings.items())[:3],
                criteria_met=criteria_met,
                differential_diagnoses=disease.differential_diagnoses[:3],
                recommended_workup=["Clinical correlation", "Imaging as indicated"],
                urgency=Severity.CRITICAL if score_data["has_critical"] else Severity(disease.default_urgency)
            ))
    
    hypotheses.sort(key=lambda h: h.probability, reverse=True)
    return hypotheses


def pathologist_agent(lab_text: str) -> Dict[str, Any]:
    """Main pathologist agent function for laboratory interpretation."""
    if not lab_text or not lab_text.strip():
        return {
            "agent": "pathologist",
            "input_snippet": "",
            "diagnoses": {},
            "top_diagnosis": "No laboratory data provided",
            "confidence": 0.0,
            "explanation": "No laboratory results provided for interpretation",
            "findings": [],
            "hypotheses": [],
            "flags": ["INCOMPLETE_DATA"]
        }
    
    findings = extract_lab_findings(lab_text)
    hypotheses = build_lab_hypotheses(findings)
    
    if hypotheses:
        top = hypotheses[0]
        primary_impression = f"{top.diagnosis} (probability: {top.probability:.0%})"
        explanation = f"Lab findings supporting: {', '.join([f.name for f in findings[:4]])}"
    elif findings:
        primary_impression = f"Abnormal labs: {', '.join([f.name for f in findings[:3]])}"
        explanation = "Laboratory abnormalities identified - requires clinical correlation"
    else:
        primary_impression = "No significant laboratory abnormality identified"
        explanation = "No concerning laboratory patterns identified in the provided text"
    
    # Calculate confidence
    critical_findings = sum(1 for f in findings if f.severity == Severity.CRITICAL)
    high_findings = sum(1 for f in findings if f.severity == Severity.HIGH)
    confidence = calculate_confidence(
        evidence_count=len(findings),
        strong_evidence_count=critical_findings + high_findings,
        weak_evidence_count=len(findings) - critical_findings - high_findings,
        criteria_met_ratio=len(hypotheses) / 4 if hypotheses else 0.0
    ) if findings else 0.3
    
    # Build flags for critical findings
    flags = []
    for finding in findings:
        if finding.severity == Severity.CRITICAL:
            flags.append(f"CRITICAL: {finding.name} - Immediate clinical correlation required")
        elif finding.severity == Severity.HIGH:
            flags.append(f"ALERT: {finding.name}")
    
    return {
        "agent": "pathologist",
        "input_snippet": lab_text[:200],
        "diagnoses": {h.diagnosis: h.probability for h in hypotheses},
        "top_diagnosis": primary_impression,
        "confidence": confidence,
        "explanation": explanation,
        "findings": [f.to_dict() for f in findings],
        "hypotheses": [h.to_dict() for h in hypotheses],
        "flags": flags
    }
