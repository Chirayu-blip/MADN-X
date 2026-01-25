# app/core/explainability.py
"""
Explainability Module for MADN-X

This module provides transparent reasoning explanations for all diagnostic decisions.
Critical for healthcare AI - every diagnosis must be traceable and explainable.

Features:
1. Evidence Attribution - Which evidence contributed to each diagnosis
2. Reasoning Chain - Step-by-step logic flow
3. Confidence Decomposition - Why confidence is high/low
4. Counterfactual Explanations - What would change the diagnosis
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


class EvidenceContribution(Enum):
    """How much each piece of evidence contributes to diagnosis."""
    DECISIVE = "decisive"      # This alone confirms/rules out diagnosis
    STRONG = "strong"          # Major contributor to diagnosis
    MODERATE = "moderate"      # Supports but not sufficient alone
    WEAK = "weak"              # Minor supporting evidence
    NEUTRAL = "neutral"        # Neither supports nor opposes
    OPPOSING = "opposing"      # Evidence against the diagnosis


@dataclass
class EvidenceAttribution:
    """Attribution of a single piece of evidence to the diagnosis."""
    evidence_type: str          # imaging, ecg, lab, symptom
    finding: str                # What was found
    contribution: EvidenceContribution
    weight: float               # 0.0 to 1.0 contribution weight
    reasoning: str              # Why this evidence matters
    source_agent: str           # Which agent identified this
    
    def to_dict(self) -> Dict:
        return {
            "evidence_type": self.evidence_type,
            "finding": self.finding,
            "contribution": self.contribution.value,
            "weight": self.weight,
            "reasoning": self.reasoning,
            "source_agent": self.source_agent
        }


@dataclass
class ReasoningStep:
    """A single step in the reasoning chain."""
    step_number: int
    agent: str
    action: str                 # "identified", "evaluated", "concluded"
    description: str
    evidence_used: List[str]
    conclusion: str
    confidence_delta: float     # How much this step changed confidence
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ConfidenceDecomposition:
    """Breakdown of how confidence was calculated."""
    base_confidence: float
    evidence_boost: float
    agreement_boost: float
    penalty_factors: List[str]
    final_confidence: float
    calibration_note: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CounterfactualExplanation:
    """What would need to change for a different diagnosis."""
    current_diagnosis: str
    alternative_diagnosis: str
    missing_evidence: List[str]
    contradicting_evidence: List[str]
    probability_if_changed: float
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class DiagnosticExplanation:
    """Complete explanation for a diagnostic decision."""
    diagnosis: str
    confidence: float
    diagnostic_certainty: str   # confirmed, probable, possible, unlikely
    
    # Evidence Attribution
    evidence_attributions: List[EvidenceAttribution] = field(default_factory=list)
    
    # Reasoning Chain
    reasoning_chain: List[ReasoningStep] = field(default_factory=list)
    
    # Confidence Breakdown
    confidence_decomposition: Optional[ConfidenceDecomposition] = None
    
    # Counterfactuals
    counterfactuals: List[CounterfactualExplanation] = field(default_factory=list)
    
    # Summary
    one_line_explanation: str = ""
    detailed_explanation: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "diagnosis": self.diagnosis,
            "confidence": self.confidence,
            "diagnostic_certainty": self.diagnostic_certainty,
            "evidence_attributions": [e.to_dict() for e in self.evidence_attributions],
            "reasoning_chain": [r.to_dict() for r in self.reasoning_chain],
            "confidence_decomposition": self.confidence_decomposition.to_dict() if self.confidence_decomposition else None,
            "counterfactuals": [c.to_dict() for c in self.counterfactuals],
            "one_line_explanation": self.one_line_explanation,
            "detailed_explanation": self.detailed_explanation
        }


def build_evidence_attribution(
    agent_outputs: Dict[str, Any],
    final_diagnosis: str
) -> List[EvidenceAttribution]:
    """Build evidence attribution for the final diagnosis."""
    attributions = []
    
    for agent_name, output in agent_outputs.items():
        if not isinstance(output, dict):
            continue
            
        findings = output.get("findings", [])
        diagnoses = output.get("diagnoses", {})
        is_definitive = output.get("is_definitive", False)
        
        # Check if this agent supports the diagnosis
        agent_supports = final_diagnosis in diagnoses or any(
            final_diagnosis.lower() in str(d).lower() for d in diagnoses.keys()
        )
        
        for finding in findings:
            if isinstance(finding, dict):
                finding_name = finding.get("name", "Unknown")
                severity = finding.get("severity", "moderate")
                significance = finding.get("clinical_significance", "")
                
                # Determine contribution level
                if is_definitive and agent_supports:
                    contribution = EvidenceContribution.DECISIVE
                    weight = 1.0
                elif severity == "critical":
                    contribution = EvidenceContribution.STRONG
                    weight = 0.8
                elif severity == "high":
                    contribution = EvidenceContribution.STRONG
                    weight = 0.6
                elif severity == "moderate":
                    contribution = EvidenceContribution.MODERATE
                    weight = 0.4
                else:
                    contribution = EvidenceContribution.WEAK
                    weight = 0.2
                
                attributions.append(EvidenceAttribution(
                    evidence_type=agent_name.replace("ologist", ""),
                    finding=finding_name,
                    contribution=contribution,
                    weight=weight,
                    reasoning=significance,
                    source_agent=agent_name
                ))
    
    # Sort by weight (most important first)
    attributions.sort(key=lambda x: x.weight, reverse=True)
    return attributions


def build_reasoning_chain(
    agent_outputs: Dict[str, Any],
    final_diagnosis: str,
    final_confidence: float
) -> List[ReasoningStep]:
    """Build the step-by-step reasoning chain."""
    steps = []
    step_num = 1
    cumulative_confidence = 0.0
    
    # Order agents by typical clinical workflow
    agent_order = ["pulmonologist", "radiologist", "cardiologist", "pathologist"]
    
    for agent_name in agent_order:
        if agent_name not in agent_outputs:
            continue
            
        output = agent_outputs[agent_name]
        if not isinstance(output, dict):
            continue
        
        findings = output.get("findings", [])
        top_diag = output.get("top_diagnosis", "")
        confidence = output.get("confidence", 0.0)
        is_definitive = output.get("is_definitive", False)
        
        if not findings:
            continue
        
        finding_names = [f.get("name", "") if isinstance(f, dict) else str(f) for f in findings[:3]]
        
        # Determine action and conclusion
        if is_definitive:
            action = "confirmed"
            conclusion = f"DEFINITIVE: {final_diagnosis} confirmed by gold-standard test"
            confidence_delta = 0.98 - cumulative_confidence
        elif final_diagnosis.lower() in top_diag.lower():
            action = "supported"
            conclusion = f"Evidence supports {final_diagnosis}"
            confidence_delta = min(0.15, confidence * 0.3)
        else:
            action = "evaluated"
            conclusion = f"Findings noted: {', '.join(finding_names)}"
            confidence_delta = 0.05
        
        cumulative_confidence = min(0.98, cumulative_confidence + confidence_delta)
        
        steps.append(ReasoningStep(
            step_number=step_num,
            agent=agent_name,
            action=action,
            description=f"{agent_name.title()} analyzed {len(findings)} finding(s)",
            evidence_used=finding_names,
            conclusion=conclusion,
            confidence_delta=round(confidence_delta, 3)
        ))
        step_num += 1
    
    return steps


def build_confidence_decomposition(
    agent_outputs: Dict[str, Any],
    final_confidence: float
) -> ConfidenceDecomposition:
    """Break down how confidence was calculated."""
    
    # Check for definitive finding
    has_definitive = any(
        output.get("is_definitive", False) 
        for output in agent_outputs.values() 
        if isinstance(output, dict)
    )
    
    if has_definitive:
        return ConfidenceDecomposition(
            base_confidence=0.95,
            evidence_boost=0.03,
            agreement_boost=0.0,
            penalty_factors=[],
            final_confidence=final_confidence,
            calibration_note="Confidence based on definitive diagnostic finding (gold-standard test)"
        )
    
    # Calculate components for non-definitive cases
    confidences = [
        output.get("confidence", 0.5) 
        for output in agent_outputs.values() 
        if isinstance(output, dict)
    ]
    
    base = sum(confidences) / len(confidences) if confidences else 0.5
    
    # Count supporting agents
    supporting = sum(
        1 for output in agent_outputs.values() 
        if isinstance(output, dict) and output.get("confidence", 0) > 0.3
    )
    agreement_boost = 0.05 * max(0, supporting - 1)
    
    penalties = []
    if len(confidences) < 3:
        penalties.append("Incomplete data (not all agents provided input)")
    if max(confidences) - min(confidences) > 0.4:
        penalties.append("Agent disagreement detected")
    
    return ConfidenceDecomposition(
        base_confidence=round(base, 3),
        evidence_boost=round(final_confidence - base - agreement_boost, 3),
        agreement_boost=round(agreement_boost, 3),
        penalty_factors=penalties,
        final_confidence=final_confidence,
        calibration_note="Confidence based on weighted agent consensus"
    )


def build_counterfactuals(
    agent_outputs: Dict[str, Any],
    final_diagnosis: str,
    differential_diagnoses: List[str]
) -> List[CounterfactualExplanation]:
    """Generate counterfactual explanations for alternative diagnoses."""
    counterfactuals = []
    
    # Define what evidence would support alternative diagnoses
    diagnosis_evidence_map = {
        "Community-Acquired Pneumonia": {
            "required": ["Consolidation on imaging", "Fever", "Productive cough", "Elevated WBC"],
            "contradicts": ["Filling defect on CTPA", "D-dimer normal"]
        },
        "ST-Elevation Myocardial Infarction": {
            "required": ["ST elevation on ECG", "Elevated troponin", "Chest pain"],
            "contradicts": ["Normal ECG", "Normal troponin"]
        },
        "Pulmonary Embolism": {
            "required": ["Filling defect on CTPA", "Elevated D-dimer", "DVT risk factors"],
            "contradicts": ["Normal CTPA", "Normal D-dimer with low clinical suspicion"]
        },
        "Acute Decompensated Heart Failure": {
            "required": ["Pulmonary edema on CXR", "Elevated BNP", "Cardiomegaly"],
            "contradicts": ["Normal BNP", "Clear lungs"]
        }
    }
    
    for alt_diag in differential_diagnoses[:3]:
        if alt_diag == final_diagnosis:
            continue
            
        evidence_needed = diagnosis_evidence_map.get(alt_diag, {})
        
        counterfactuals.append(CounterfactualExplanation(
            current_diagnosis=final_diagnosis,
            alternative_diagnosis=alt_diag,
            missing_evidence=evidence_needed.get("required", ["Specific diagnostic criteria"]),
            contradicting_evidence=evidence_needed.get("contradicts", []),
            probability_if_changed=0.15  # Placeholder
        ))
    
    return counterfactuals


def generate_explanation(
    agent_outputs: Dict[str, Any],
    final_diagnosis: str,
    final_confidence: float,
    is_definitive: bool = False,
    differential_diagnoses: List[str] = None
) -> DiagnosticExplanation:
    """Generate complete diagnostic explanation."""
    
    # Determine diagnostic certainty
    if is_definitive:
        certainty = "confirmed"
    elif final_confidence >= 0.8:
        certainty = "probable"
    elif final_confidence >= 0.5:
        certainty = "possible"
    else:
        certainty = "unlikely"
    
    # Build all components
    attributions = build_evidence_attribution(agent_outputs, final_diagnosis)
    reasoning = build_reasoning_chain(agent_outputs, final_diagnosis, final_confidence)
    confidence_breakdown = build_confidence_decomposition(agent_outputs, final_confidence)
    counterfactuals = build_counterfactuals(
        agent_outputs, final_diagnosis, differential_diagnoses or []
    )
    
    # Generate summaries
    decisive_evidence = [a for a in attributions if a.contribution == EvidenceContribution.DECISIVE]
    strong_evidence = [a for a in attributions if a.contribution == EvidenceContribution.STRONG]
    
    if decisive_evidence:
        one_line = f"{final_diagnosis} CONFIRMED by {decisive_evidence[0].finding}"
    elif strong_evidence:
        one_line = f"{final_diagnosis} supported by {len(strong_evidence)} strong finding(s)"
    else:
        one_line = f"{final_diagnosis} suggested based on clinical presentation"
    
    # Detailed explanation
    detailed_parts = [f"Diagnosis: {final_diagnosis} ({certainty.upper()})"]
    detailed_parts.append(f"\nConfidence: {final_confidence:.0%}")
    detailed_parts.append(f"\nKey Evidence:")
    for attr in attributions[:5]:
        detailed_parts.append(f"  • [{attr.contribution.value.upper()}] {attr.finding} ({attr.source_agent})")
    
    if counterfactuals:
        detailed_parts.append(f"\nDifferential Considerations:")
        for cf in counterfactuals[:2]:
            detailed_parts.append(f"  • {cf.alternative_diagnosis}: Would require {cf.missing_evidence[0] if cf.missing_evidence else 'additional evidence'}")
    
    return DiagnosticExplanation(
        diagnosis=final_diagnosis,
        confidence=final_confidence,
        diagnostic_certainty=certainty,
        evidence_attributions=attributions,
        reasoning_chain=reasoning,
        confidence_decomposition=confidence_breakdown,
        counterfactuals=counterfactuals,
        one_line_explanation=one_line,
        detailed_explanation="\n".join(detailed_parts)
    )
