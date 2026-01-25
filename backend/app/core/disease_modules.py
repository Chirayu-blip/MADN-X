# app/core/disease_modules.py
"""
Disease Modules for MADN-X Medical Diagnostic System

This module contains evidence-based diagnostic criteria for supported diseases.
Each disease module includes:
- Clinical diagnostic criteria (based on established medical guidelines)
- Required and supportive findings
- Red flags and contraindications
- Differential diagnoses to consider

SUPPORTED DISEASE CATEGORIES:
1. Respiratory: Pneumonia, COPD Exacerbation, Pulmonary Embolism, Tuberculosis, Asthma
2. Cardiac: STEMI, NSTEMI, Heart Failure, Atrial Fibrillation, Pericarditis

References:
- AHA/ACC Guidelines for Acute Coronary Syndromes
- IDSA/ATS Guidelines for Community-Acquired Pneumonia
- GOLD Guidelines for COPD
- ESC Guidelines for Pulmonary Embolism
- Framingham Criteria for Heart Failure
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum


class DiseaseCategory(str, Enum):
    RESPIRATORY = "respiratory"
    CARDIAC = "cardiac"
    INFECTIOUS = "infectious"
    INFLAMMATORY = "inflammatory"


@dataclass
class DiagnosticCriteria:
    """Defines the criteria needed to diagnose a condition"""
    name: str
    icd10_code: str
    category: DiseaseCategory
    
    # Major criteria (high diagnostic value)
    major_criteria: List[str] = field(default_factory=list)
    major_required: int = 0  # How many major criteria needed
    
    # Minor criteria (supportive)
    minor_criteria: List[str] = field(default_factory=list)
    minor_required: int = 0
    
    # Imaging findings
    imaging_findings: List[str] = field(default_factory=list)
    
    # ECG findings
    ecg_findings: List[str] = field(default_factory=list)
    
    # Lab findings with thresholds
    lab_findings: Dict[str, str] = field(default_factory=dict)  # lab: threshold
    
    # Symptoms
    typical_symptoms: List[str] = field(default_factory=list)
    
    # Red flags requiring immediate attention
    red_flags: List[str] = field(default_factory=list)
    
    # Findings that argue against this diagnosis
    exclusion_criteria: List[str] = field(default_factory=list)
    
    # Differential diagnoses to consider
    differential_diagnoses: List[str] = field(default_factory=list)
    
    # Urgency level
    default_urgency: str = "moderate"


# ============================================================================
# RESPIRATORY DISEASES
# ============================================================================

PNEUMONIA = DiagnosticCriteria(
    name="Community-Acquired Pneumonia",
    icd10_code="J18.9",
    category=DiseaseCategory.RESPIRATORY,
    
    major_criteria=[
        "New infiltrate on chest imaging",
        "Consolidation on imaging",
        "Air bronchograms on imaging"
    ],
    major_required=1,
    
    minor_criteria=[
        "Fever (>38°C or >100.4°F)",
        "Productive cough",
        "Pleuritic chest pain",
        "Dyspnea",
        "Crackles/rales on auscultation",
        "Altered mental status (elderly)",
        "Tachypnea (RR >20)"
    ],
    minor_required=2,
    
    imaging_findings=[
        "Lobar consolidation",
        "Patchy opacities",
        "Interstitial infiltrates",
        "Air bronchograms",
        "Pleural effusion (parapneumonic)"
    ],
    
    ecg_findings=[
        "Sinus tachycardia (common)",
        "Otherwise typically normal"
    ],
    
    lab_findings={
        "WBC": ">12,000/μL or <4,000/μL",
        "CRP": ">10 mg/L",
        "Procalcitonin": ">0.25 ng/mL (bacterial)",
        "Lactate": ">2 mmol/L (severe)"
    },
    
    typical_symptoms=[
        "Cough (productive or dry)",
        "Fever/chills",
        "Dyspnea",
        "Pleuritic chest pain",
        "Fatigue",
        "Sputum production"
    ],
    
    red_flags=[
        "Respiratory failure (SpO2 <90%)",
        "Septic shock",
        "Altered mental status",
        "Multilobar involvement"
    ],
    
    exclusion_criteria=[
        "Clear chest X-ray with no infiltrates",
        "Heart failure causing pulmonary edema"
    ],
    
    differential_diagnoses=[
        "Heart failure with pulmonary edema",
        "Pulmonary embolism",
        "Lung cancer",
        "COPD exacerbation",
        "Interstitial lung disease"
    ],
    
    default_urgency="moderate"
)


COPD_EXACERBATION = DiagnosticCriteria(
    name="COPD Exacerbation",
    icd10_code="J44.1",
    category=DiseaseCategory.RESPIRATORY,
    
    major_criteria=[
        "Known history of COPD",
        "Increased dyspnea from baseline",
        "Increased sputum volume",
        "Increased sputum purulence"
    ],
    major_required=2,  # Anthonisen criteria: 2+ of increased dyspnea, sputum volume, purulence
    
    minor_criteria=[
        "Wheezing",
        "Upper respiratory infection in past 5 days",
        "Fever without other source",
        "Increased cough",
        "Heart rate or respiratory rate increase >20% from baseline"
    ],
    minor_required=1,
    
    imaging_findings=[
        "Hyperinflation",
        "Flattened diaphragms",
        "Increased AP diameter",
        "Bullae",
        "No new infiltrate (rules out pneumonia)"
    ],
    
    ecg_findings=[
        "Right axis deviation",
        "P pulmonale (tall P waves in II)",
        "Low voltage QRS",
        "Sinus tachycardia"
    ],
    
    lab_findings={
        "ABG pH": "<7.35 (respiratory acidosis in severe)",
        "PaCO2": ">45 mmHg (hypercapnia)",
        "WBC": "Normal or mildly elevated",
        "BNP": "<100 pg/mL (helps exclude CHF)"
    },
    
    typical_symptoms=[
        "Worsening dyspnea",
        "Increased sputum",
        "Change in sputum color",
        "Wheezing",
        "Chest tightness"
    ],
    
    red_flags=[
        "Severe dyspnea at rest",
        "Cyanosis",
        "Use of accessory muscles",
        "Peripheral edema (cor pulmonale)",
        "Altered mental status (CO2 narcosis)"
    ],
    
    exclusion_criteria=[
        "New infiltrate suggesting pneumonia",
        "Pulmonary embolism on imaging"
    ],
    
    differential_diagnoses=[
        "Pneumonia",
        "Pulmonary embolism",
        "Heart failure",
        "Pneumothorax",
        "Asthma exacerbation"
    ],
    
    default_urgency="moderate"
)


PULMONARY_EMBOLISM = DiagnosticCriteria(
    name="Pulmonary Embolism",
    icd10_code="I26.99",
    category=DiseaseCategory.RESPIRATORY,
    
    major_criteria=[
        "CT angiography showing filling defect",
        "V/Q scan high probability",
        "Positive pulmonary angiography"
    ],
    major_required=1,
    
    minor_criteria=[
        "Elevated D-dimer",
        "Wells score ≥4",
        "Tachycardia unexplained",
        "Hypoxemia",
        "Right heart strain on echo"
    ],
    minor_required=2,
    
    imaging_findings=[
        "Filling defect in pulmonary artery (CTA)",
        "Hampton's hump (wedge-shaped opacity)",
        "Westermark sign (oligemia)",
        "Enlarged pulmonary artery",
        "RV dilation"
    ],
    
    ecg_findings=[
        "S1Q3T3 pattern",
        "Right bundle branch block (new)",
        "Right axis deviation",
        "Sinus tachycardia",
        "T wave inversions V1-V4",
        "Atrial fibrillation (new onset)"
    ],
    
    lab_findings={
        "D-dimer": ">500 ng/mL",
        "Troponin": "Elevated (RV strain)",
        "BNP": "Elevated (RV dysfunction)",
        "ABG": "Hypoxemia, respiratory alkalosis"
    },
    
    typical_symptoms=[
        "Sudden onset dyspnea",
        "Pleuritic chest pain",
        "Cough",
        "Hemoptysis",
        "Syncope (massive PE)",
        "Leg swelling/pain (DVT)"
    ],
    
    red_flags=[
        "Hemodynamic instability",
        "Syncope",
        "Severe hypoxemia",
        "RV dysfunction",
        "Elevated troponin"
    ],
    
    exclusion_criteria=[
        "Negative CTA",
        "Low probability V/Q scan with low clinical suspicion",
        "Negative D-dimer with low clinical probability"
    ],
    
    differential_diagnoses=[
        "Pneumonia",
        "Acute coronary syndrome",
        "Aortic dissection",
        "Pneumothorax",
        "Heart failure"
    ],
    
    default_urgency="high"
)


TUBERCULOSIS = DiagnosticCriteria(
    name="Pulmonary Tuberculosis",
    icd10_code="A15.0",
    category=DiseaseCategory.INFECTIOUS,
    
    major_criteria=[
        "Positive sputum AFB smear",
        "Positive TB culture",
        "Positive TB PCR/GeneXpert"
    ],
    major_required=1,
    
    minor_criteria=[
        "Upper lobe cavitary lesion on imaging",
        "Positive tuberculin skin test",
        "Positive IGRA (QuantiFERON)",
        "Endemic exposure or known contact",
        "Immunocompromised state"
    ],
    minor_required=2,
    
    imaging_findings=[
        "Upper lobe infiltrates",
        "Cavitary lesions",
        "Tree-in-bud pattern",
        "Miliary pattern (disseminated)",
        "Hilar/mediastinal lymphadenopathy",
        "Pleural effusion",
        "Apical scarring"
    ],
    
    ecg_findings=[
        "Usually normal",
        "Pericarditis pattern if TB pericarditis"
    ],
    
    lab_findings={
        "AFB smear": "Positive",
        "TB culture": "Positive (gold standard)",
        "IGRA": "Positive",
        "TST": "≥10mm (≥5mm if immunocompromised)"
    },
    
    typical_symptoms=[
        "Chronic cough (>2-3 weeks)",
        "Hemoptysis",
        "Night sweats",
        "Weight loss",
        "Low-grade fever",
        "Fatigue"
    ],
    
    red_flags=[
        "Massive hemoptysis",
        "Respiratory failure",
        "Miliary pattern (disseminated)",
        "TB meningitis symptoms"
    ],
    
    exclusion_criteria=[
        "Negative AFB and culture with resolution on follow-up"
    ],
    
    differential_diagnoses=[
        "Lung cancer",
        "Nontuberculous mycobacteria",
        "Fungal infection",
        "Bacterial pneumonia",
        "Sarcoidosis"
    ],
    
    default_urgency="moderate"
)


ASTHMA_EXACERBATION = DiagnosticCriteria(
    name="Asthma Exacerbation",
    icd10_code="J45.901",
    category=DiseaseCategory.RESPIRATORY,
    
    major_criteria=[
        "Known history of asthma",
        "Wheezing on auscultation",
        "Response to bronchodilators"
    ],
    major_required=2,
    
    minor_criteria=[
        "Dyspnea",
        "Chest tightness",
        "Cough",
        "Trigger exposure (allergen, infection, irritant)",
        "Peak flow reduced from personal best"
    ],
    minor_required=1,
    
    imaging_findings=[
        "Hyperinflation",
        "Usually normal",
        "Rule out pneumothorax",
        "Rule out pneumonia"
    ],
    
    ecg_findings=[
        "Sinus tachycardia",
        "Usually normal"
    ],
    
    lab_findings={
        "ABG": "Respiratory alkalosis early, acidosis in severe",
        "WBC": "May be elevated with stress or steroids",
        "Eosinophils": "May be elevated"
    },
    
    typical_symptoms=[
        "Dyspnea",
        "Wheezing",
        "Cough (often dry)",
        "Chest tightness",
        "Symptoms worse at night"
    ],
    
    red_flags=[
        "Silent chest (severe obstruction)",
        "Unable to speak in sentences",
        "Peak flow <25% predicted",
        "Cyanosis",
        "Altered mental status"
    ],
    
    exclusion_criteria=[
        "New infiltrate on imaging (consider pneumonia)",
        "Heart failure",
        "Vocal cord dysfunction"
    ],
    
    differential_diagnoses=[
        "COPD exacerbation",
        "Heart failure",
        "Pulmonary embolism",
        "Vocal cord dysfunction",
        "Foreign body aspiration"
    ],
    
    default_urgency="moderate"
)


# ============================================================================
# CARDIAC DISEASES
# ============================================================================

STEMI = DiagnosticCriteria(
    name="ST-Elevation Myocardial Infarction",
    icd10_code="I21.3",
    category=DiseaseCategory.CARDIAC,
    
    major_criteria=[
        "ST elevation ≥1mm in 2+ contiguous leads",
        "New LBBB with ischemic symptoms",
        "Elevated troponin with rise/fall pattern"
    ],
    major_required=2,  # ECG changes + troponin
    
    minor_criteria=[
        "Ischemic symptoms (chest pain, dyspnea)",
        "Reciprocal ST depression",
        "Q waves",
        "Wall motion abnormality on echo"
    ],
    minor_required=1,
    
    imaging_findings=[
        "Wall motion abnormality on echo",
        "Pulmonary congestion (if heart failure)",
        "Usually normal chest X-ray early"
    ],
    
    ecg_findings=[
        "ST elevation ≥1mm in limb leads",
        "ST elevation ≥2mm in precordial leads",
        "Reciprocal ST depression",
        "Hyperacute T waves (early)",
        "Q waves (evolving)",
        "New LBBB"
    ],
    
    lab_findings={
        "Troponin I/T": "Elevated with rise/fall",
        "CK-MB": "Elevated",
        "BNP": "May be elevated (heart failure)"
    },
    
    typical_symptoms=[
        "Crushing/squeezing chest pain",
        "Radiation to left arm, jaw, back",
        "Diaphoresis",
        "Nausea/vomiting",
        "Dyspnea",
        "Sense of impending doom"
    ],
    
    red_flags=[
        "Cardiogenic shock",
        "Ventricular arrhythmias",
        "Mechanical complications (VSD, papillary muscle rupture)",
        "Complete heart block"
    ],
    
    exclusion_criteria=[
        "Aortic dissection (contraindication to thrombolytics)",
        "Stress cardiomyopathy (Takotsubo)"
    ],
    
    differential_diagnoses=[
        "NSTEMI",
        "Pericarditis",
        "Aortic dissection",
        "Pulmonary embolism",
        "Esophageal rupture"
    ],
    
    default_urgency="critical"
)


NSTEMI = DiagnosticCriteria(
    name="Non-ST-Elevation Myocardial Infarction",
    icd10_code="I21.4",
    category=DiseaseCategory.CARDIAC,
    
    major_criteria=[
        "Elevated troponin with rise/fall pattern",
        "Ischemic symptoms",
        "ECG changes (ST depression or T wave inversion)"
    ],
    major_required=2,
    
    minor_criteria=[
        "Known CAD history",
        "Diabetes mellitus",
        "Dynamic ECG changes",
        "Wall motion abnormality"
    ],
    minor_required=1,
    
    imaging_findings=[
        "Wall motion abnormality on echo",
        "Coronary stenosis on angiography"
    ],
    
    ecg_findings=[
        "ST depression ≥0.5mm",
        "T wave inversion ≥1mm",
        "No ST elevation (except aVR)",
        "Dynamic changes"
    ],
    
    lab_findings={
        "Troponin I/T": "Elevated with rise/fall",
        "CK-MB": "May be elevated",
        "BNP": "May be elevated"
    },
    
    typical_symptoms=[
        "Chest pain/pressure",
        "May be atypical (especially in diabetics, women, elderly)",
        "Dyspnea",
        "Fatigue"
    ],
    
    red_flags=[
        "Ongoing chest pain despite treatment",
        "Hemodynamic instability",
        "Heart failure",
        "Sustained arrhythmias"
    ],
    
    exclusion_criteria=[
        "ST elevation (STEMI)",
        "Non-cardiac troponin elevation (renal failure, PE)"
    ],
    
    differential_diagnoses=[
        "STEMI",
        "Unstable angina",
        "Type 2 MI (demand ischemia)",
        "Myocarditis",
        "Takotsubo cardiomyopathy"
    ],
    
    default_urgency="high"
)


HEART_FAILURE = DiagnosticCriteria(
    name="Acute Decompensated Heart Failure",
    icd10_code="I50.9",
    category=DiseaseCategory.CARDIAC,
    
    # Modified Framingham Criteria
    major_criteria=[
        "Paroxysmal nocturnal dyspnea or orthopnea",
        "Jugular venous distension",
        "Pulmonary rales/crackles",
        "Cardiomegaly on imaging",
        "Pulmonary edema on imaging",
        "S3 gallop",
        "Hepatojugular reflux"
    ],
    major_required=2,
    
    minor_criteria=[
        "Bilateral ankle edema",
        "Nocturnal cough",
        "Dyspnea on exertion",
        "Hepatomegaly",
        "Pleural effusion",
        "Heart rate >120 bpm",
        "Weight loss >4.5 kg in 5 days with treatment"
    ],
    minor_required=1,  # 2 major OR 1 major + 2 minor
    
    imaging_findings=[
        "Cardiomegaly",
        "Pulmonary vascular congestion",
        "Kerley B lines",
        "Pleural effusions (bilateral)",
        "Pulmonary edema",
        "Cephalization of vessels"
    ],
    
    ecg_findings=[
        "LVH by voltage criteria",
        "Atrial fibrillation (common)",
        "Left axis deviation",
        "Q waves (prior MI)",
        "LBBB"
    ],
    
    lab_findings={
        "BNP": ">400 pg/mL (or NT-proBNP >1000)",
        "Troponin": "May be mildly elevated",
        "Creatinine": "May be elevated (cardiorenal)",
        "Sodium": "May be low (dilutional)"
    },
    
    typical_symptoms=[
        "Dyspnea (exertional and at rest)",
        "Orthopnea",
        "Paroxysmal nocturnal dyspnea",
        "Fatigue",
        "Lower extremity edema",
        "Weight gain"
    ],
    
    red_flags=[
        "Cardiogenic shock",
        "Severe hypoxemia",
        "Acute pulmonary edema",
        "Need for intubation"
    ],
    
    exclusion_criteria=[
        "Non-cardiac cause of edema",
        "Isolated right heart failure from pulmonary cause"
    ],
    
    differential_diagnoses=[
        "COPD exacerbation",
        "Pneumonia",
        "Pulmonary embolism",
        "Nephrotic syndrome",
        "Cirrhosis"
    ],
    
    default_urgency="high"
)


ATRIAL_FIBRILLATION = DiagnosticCriteria(
    name="Atrial Fibrillation",
    icd10_code="I48.91",
    category=DiseaseCategory.CARDIAC,
    
    major_criteria=[
        "Irregularly irregular rhythm on ECG",
        "Absence of P waves",
        "Fibrillatory waves"
    ],
    major_required=2,
    
    minor_criteria=[
        "Palpitations",
        "Variable R-R intervals",
        "Ventricular rate >100 (RVR) or <60"
    ],
    minor_required=1,
    
    imaging_findings=[
        "May show cardiomegaly",
        "Left atrial enlargement on echo",
        "Rule out thrombus (TEE)"
    ],
    
    ecg_findings=[
        "Absent P waves",
        "Irregularly irregular R-R intervals",
        "Fibrillatory (f) waves",
        "Variable ventricular rate",
        "May have RVR (rate >100)"
    ],
    
    lab_findings={
        "TSH": "Check for hyperthyroidism",
        "Electrolytes": "Check K+, Mg2+",
        "BNP": "Often elevated"
    },
    
    typical_symptoms=[
        "Palpitations",
        "Fatigue",
        "Dyspnea",
        "Dizziness",
        "Chest discomfort",
        "May be asymptomatic"
    ],
    
    red_flags=[
        "Hemodynamic instability",
        "Ventricular rate >150",
        "Evidence of stroke/TIA",
        "Active bleeding with need for anticoagulation"
    ],
    
    exclusion_criteria=[
        "Regular rhythm",
        "Clear P waves"
    ],
    
    differential_diagnoses=[
        "Atrial flutter",
        "Multifocal atrial tachycardia",
        "Sinus tachycardia with frequent PACs",
        "Atrial tachycardia"
    ],
    
    default_urgency="moderate"
)


PERICARDITIS = DiagnosticCriteria(
    name="Acute Pericarditis",
    icd10_code="I30.9",
    category=DiseaseCategory.CARDIAC,
    
    # ESC Criteria: 2 of 4 needed
    major_criteria=[
        "Typical pericarditic chest pain",
        "Pericardial friction rub",
        "Widespread ST elevation or PR depression on ECG",
        "New or worsening pericardial effusion"
    ],
    major_required=2,
    
    minor_criteria=[
        "Elevated inflammatory markers (CRP, ESR)",
        "Recent viral illness",
        "Low-grade fever"
    ],
    minor_required=1,
    
    imaging_findings=[
        "Pericardial effusion on echo",
        "Normal or enlarged cardiac silhouette",
        "Pericardial thickening on CT/MRI"
    ],
    
    ecg_findings=[
        "Diffuse ST elevation (concave up)",
        "PR depression (most specific)",
        "No reciprocal changes",
        "May see low voltage if effusion",
        "Electrical alternans (tamponade)"
    ],
    
    lab_findings={
        "CRP": "Elevated",
        "ESR": "Elevated",
        "WBC": "May be elevated",
        "Troponin": "May be mildly elevated (myopericarditis)"
    },
    
    typical_symptoms=[
        "Sharp, pleuritic chest pain",
        "Pain worse lying flat",
        "Pain relieved sitting forward",
        "May radiate to trapezius ridge",
        "Low-grade fever"
    ],
    
    red_flags=[
        "Cardiac tamponade (Beck's triad)",
        "Large effusion",
        "High-risk features (fever >38°C, immunosuppression, trauma)",
        "Elevated troponin (myopericarditis)"
    ],
    
    exclusion_criteria=[
        "Focal ST elevation with reciprocal changes (STEMI)",
        "Aortic dissection"
    ],
    
    differential_diagnoses=[
        "STEMI",
        "Pulmonary embolism",
        "Aortic dissection",
        "Pneumonia",
        "Costochondritis"
    ],
    
    default_urgency="moderate"
)


# ============================================================================
# DISEASE REGISTRY
# ============================================================================

DISEASE_REGISTRY: Dict[str, DiagnosticCriteria] = {
    # Respiratory
    "pneumonia": PNEUMONIA,
    "community_acquired_pneumonia": PNEUMONIA,
    "copd_exacerbation": COPD_EXACERBATION,
    "copd": COPD_EXACERBATION,
    "pulmonary_embolism": PULMONARY_EMBOLISM,
    "pe": PULMONARY_EMBOLISM,
    "tuberculosis": TUBERCULOSIS,
    "tb": TUBERCULOSIS,
    "asthma_exacerbation": ASTHMA_EXACERBATION,
    "asthma": ASTHMA_EXACERBATION,
    
    # Cardiac
    "stemi": STEMI,
    "st_elevation_mi": STEMI,
    "nstemi": NSTEMI,
    "heart_failure": HEART_FAILURE,
    "chf": HEART_FAILURE,
    "atrial_fibrillation": ATRIAL_FIBRILLATION,
    "afib": ATRIAL_FIBRILLATION,
    "pericarditis": PERICARDITIS,
}


def get_all_diseases() -> List[DiagnosticCriteria]:
    """Return all unique disease modules"""
    seen = set()
    diseases = []
    for disease in DISEASE_REGISTRY.values():
        if disease.name not in seen:
            seen.add(disease.name)
            diseases.append(disease)
    return diseases


def get_diseases_by_category(category: DiseaseCategory) -> List[DiagnosticCriteria]:
    """Get all diseases in a specific category"""
    seen = set()
    diseases = []
    for disease in DISEASE_REGISTRY.values():
        if disease.category == category and disease.name not in seen:
            seen.add(disease.name)
            diseases.append(disease)
    return diseases


def match_disease(text: str) -> List[DiagnosticCriteria]:
    """Find potentially matching diseases based on text content"""
    text_lower = text.lower()
    matches = []
    seen = set()
    
    for disease in DISEASE_REGISTRY.values():
        if disease.name in seen:
            continue
            
        score = 0
        # Check symptoms
        for symptom in disease.typical_symptoms:
            if symptom.lower() in text_lower:
                score += 1
        
        # Check imaging findings
        for finding in disease.imaging_findings:
            if finding.lower() in text_lower:
                score += 2
        
        # Check ECG findings
        for finding in disease.ecg_findings:
            if finding.lower() in text_lower:
                score += 2
        
        if score > 0:
            seen.add(disease.name)
            matches.append((score, disease))
    
    # Sort by score descending
    matches.sort(key=lambda x: x[0], reverse=True)
    return [m[1] for m in matches]
