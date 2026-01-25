# app/core/evidence_layer.py
"""
Shared Evidence Layer for Multi-Agent Medical Diagnostic System

This module defines the standardized evidence schema that all agents use,
ensuring consistent data flow and enabling proper consensus building.

Key Components:
1. Evidence - Individual piece of clinical evidence with source and confidence
2. Finding - Clinical finding with supporting evidence
3. DiagnosticHypothesis - A potential diagnosis with supporting/opposing evidence
4. AgentReport - Standardized output format for all specialist agents
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime
import json


class EvidenceType(str, Enum):
    """Types of clinical evidence"""
    IMAGING = "imaging"
    ECG = "ecg"
    LAB = "laboratory"
    SYMPTOM = "symptom"
    VITAL_SIGN = "vital_sign"
    PHYSICAL_EXAM = "physical_exam"
    HISTORY = "history"


class Severity(str, Enum):
    """Clinical severity levels"""
    CRITICAL = "critical"      # Life-threatening, immediate intervention needed
    HIGH = "high"              # Serious, urgent attention required
    MODERATE = "moderate"      # Significant, requires timely evaluation
    LOW = "low"                # Minor, routine follow-up
    NORMAL = "normal"          # Within normal limits


class EvidenceStrength(str, Enum):
    """How strongly evidence supports a finding"""
    DEFINITIVE = "definitive"  # Pathognomonic, highly specific (e.g., ST elevation + troponin for STEMI)
    STRONG = "strong"          # Highly suggestive but not pathognomonic
    MODERATE = "moderate"      # Supportive evidence
    WEAK = "weak"              # Marginally supportive
    ABSENT = "absent"          # Expected finding not present


@dataclass
class Evidence:
    """Individual piece of clinical evidence"""
    type: EvidenceType
    description: str
    value: Optional[str] = None
    normal_range: Optional[str] = None
    is_abnormal: bool = False
    strength: EvidenceStrength = EvidenceStrength.MODERATE
    source: str = ""  # e.g., "radiology_report", "ecg_interpretation"
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "description": self.description,
            "value": self.value,
            "normal_range": self.normal_range,
            "is_abnormal": self.is_abnormal,
            "strength": self.strength.value,
            "source": self.source
        }


@dataclass
class Finding:
    """Clinical finding with supporting evidence"""
    name: str
    present: bool
    evidence: List[Evidence] = field(default_factory=list)
    clinical_significance: str = ""
    severity: Severity = Severity.NORMAL
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "present": self.present,
            "evidence": [e.to_dict() for e in self.evidence],
            "clinical_significance": self.clinical_significance,
            "severity": self.severity.value
        }


@dataclass
class DiagnosticHypothesis:
    """A potential diagnosis with supporting and opposing evidence"""
    diagnosis: str
    icd10_code: Optional[str] = None  # For standardization
    probability: float = 0.0  # 0-1 scale
    supporting_evidence: List[Evidence] = field(default_factory=list)
    opposing_evidence: List[Evidence] = field(default_factory=list)
    required_for_diagnosis: List[str] = field(default_factory=list)  # Criteria that must be met
    criteria_met: List[str] = field(default_factory=list)
    criteria_not_met: List[str] = field(default_factory=list)
    differential_diagnoses: List[str] = field(default_factory=list)
    recommended_workup: List[str] = field(default_factory=list)
    urgency: Severity = Severity.MODERATE
    
    def to_dict(self) -> Dict:
        return {
            "diagnosis": self.diagnosis,
            "icd10_code": self.icd10_code,
            "probability": self.probability,
            "supporting_evidence": [e.to_dict() for e in self.supporting_evidence],
            "opposing_evidence": [e.to_dict() for e in self.opposing_evidence],
            "required_for_diagnosis": self.required_for_diagnosis,
            "criteria_met": self.criteria_met,
            "criteria_not_met": self.criteria_not_met,
            "differential_diagnoses": self.differential_diagnoses,
            "recommended_workup": self.recommended_workup,
            "urgency": self.urgency.value
        }


@dataclass
class AgentReport:
    """Standardized output format for all specialist agents"""
    agent_type: str
    agent_name: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    input_summary: str = ""
    findings: List[Finding] = field(default_factory=list)
    hypotheses: List[DiagnosticHypothesis] = field(default_factory=list)
    primary_impression: str = ""
    confidence: float = 0.0  # 0-1 scale
    confidence_factors: Dict[str, float] = field(default_factory=dict)
    limitations: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)  # Critical alerts
    raw_input: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "agent_type": self.agent_type,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp,
            "input_summary": self.input_summary,
            "findings": [f.to_dict() for f in self.findings],
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "primary_impression": self.primary_impression,
            "confidence": self.confidence,
            "confidence_factors": self.confidence_factors,
            "limitations": self.limitations,
            "recommendations": self.recommendations,
            "flags": self.flags,
            "raw_input": self.raw_input[:500]  # Truncate for storage
        }
    
    def get_top_diagnosis(self) -> Optional[DiagnosticHypothesis]:
        """Return the highest probability hypothesis"""
        if not self.hypotheses:
            return None
        return max(self.hypotheses, key=lambda h: h.probability)
    
    def get_critical_findings(self) -> List[Finding]:
        """Return findings marked as critical"""
        return [f for f in self.findings if f.severity == Severity.CRITICAL]
    
    def has_critical_flags(self) -> bool:
        """Check if there are any critical alerts"""
        return len(self.flags) > 0 or len(self.get_critical_findings()) > 0


def calculate_confidence(
    evidence_count: int,
    strong_evidence_count: int,
    weak_evidence_count: int,
    criteria_met_ratio: float,
    has_contradictions: bool = False
) -> float:
    """
    Calculate calibrated confidence score based on evidence strength.
    
    This provides more consistent confidence scoring across agents.
    """
    # Base confidence from criteria match
    base = criteria_met_ratio * 0.5
    
    # Evidence contribution
    evidence_score = min(0.3, (evidence_count * 0.05))
    strong_bonus = min(0.15, (strong_evidence_count * 0.05))
    weak_penalty = min(0.1, (weak_evidence_count * 0.02))
    
    confidence = base + evidence_score + strong_bonus - weak_penalty
    
    # Contradiction penalty
    if has_contradictions:
        confidence *= 0.7
    
    # Clamp to valid range
    return round(max(0.1, min(0.95, confidence)), 3)


def merge_evidence_from_reports(reports: List[AgentReport]) -> Dict[str, List[Evidence]]:
    """
    Merge evidence from multiple agent reports into a unified evidence pool.
    Groups by evidence type for easier analysis.
    """
    merged: Dict[str, List[Evidence]] = {}
    
    for report in reports:
        for finding in report.findings:
            for evidence in finding.evidence:
                key = evidence.type.value
                if key not in merged:
                    merged[key] = []
                merged[key].append(evidence)
        
        for hypothesis in report.hypotheses:
            for evidence in hypothesis.supporting_evidence:
                key = evidence.type.value
                if key not in merged:
                    merged[key] = []
                merged[key].append(evidence)
    
    return merged


def identify_conflicts(reports: List[AgentReport]) -> List[Dict[str, Any]]:
    """
    Identify conflicting diagnoses or findings between agents.
    Returns list of conflicts with details about which agents disagree.
    """
    conflicts = []
    
    # Collect all hypotheses by diagnosis name
    diagnosis_map: Dict[str, List[tuple]] = {}  # diagnosis -> [(agent, probability)]
    
    for report in reports:
        for hypothesis in report.hypotheses:
            key = hypothesis.diagnosis.lower()
            if key not in diagnosis_map:
                diagnosis_map[key] = []
            diagnosis_map[key].append((report.agent_name, hypothesis.probability))
    
    # Check for significant disagreements (>0.3 difference in probability)
    for diagnosis, agent_probs in diagnosis_map.items():
        if len(agent_probs) < 2:
            continue
        
        probs = [p for _, p in agent_probs]
        if max(probs) - min(probs) > 0.3:
            conflicts.append({
                "diagnosis": diagnosis,
                "disagreement": agent_probs,
                "spread": max(probs) - min(probs)
            })
    
    return conflicts
