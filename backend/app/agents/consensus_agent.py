# app/agents/consensus_agent.py
"""
Consensus Agent for MADN-X Multi-Agent Diagnostic System

This agent aggregates outputs from all specialist agents and builds
a unified diagnosis using weighted evidence merging.

Key Features:
1. Weighted evidence aggregation based on agent expertise
2. Cross-validation of findings between agents
3. Confidence calibration based on agreement
4. Identification of supporting and conflicting evidence
"""

import json
from typing import Dict, Any, List, Tuple, Optional

# ============================================================================
# AGENT WEIGHTS - Based on diagnostic relevance for different conditions
# ============================================================================

AGENT_BASE_WEIGHTS = {
    "radiologist": 1.0,
    "cardiologist": 1.0,
    "pulmonologist": 1.0,
    "pathologist": 0.8
}

CONDITION_WEIGHTS = {
    "Community-Acquired Pneumonia": {"radiologist": 1.3, "pulmonologist": 1.2, "pathologist": 1.0, "cardiologist": 0.5},
    "ST-Elevation Myocardial Infarction": {"cardiologist": 1.5, "pathologist": 1.3, "radiologist": 0.6, "pulmonologist": 0.4},
    "Non-ST-Elevation Myocardial Infarction": {"cardiologist": 1.4, "pathologist": 1.3, "radiologist": 0.6, "pulmonologist": 0.5},
    "Pulmonary Embolism": {"radiologist": 1.4, "cardiologist": 1.0, "pathologist": 1.0, "pulmonologist": 0.8},
    "Acute Decompensated Heart Failure": {"radiologist": 1.2, "cardiologist": 1.2, "pathologist": 1.1, "pulmonologist": 0.9},
    "COPD Exacerbation": {"pulmonologist": 1.4, "radiologist": 1.0, "pathologist": 0.8, "cardiologist": 0.6},
}


def _safe_parse_report(report: Any) -> Dict[str, Any]:
    """Normalize agent report into consistent format."""
    if isinstance(report, dict):
        return report
    try:
        if isinstance(report, str):
            start = report.find("{")
            end = report.rfind("}")
            if start != -1 and end > start:
                return json.loads(report[start:end+1])
    except:
        pass
    return {"diagnoses": {}, "confidence": 0.0}


def get_condition_weight(condition: str, agent: str) -> float:
    """Get weight for an agent for a specific condition."""
    if condition in CONDITION_WEIGHTS:
        return CONDITION_WEIGHTS[condition].get(agent, AGENT_BASE_WEIGHTS.get(agent, 1.0))
    return AGENT_BASE_WEIGHTS.get(agent, 1.0)


def collect_all_hypotheses(agent_outputs: Dict[str, Dict]) -> Dict[str, List[Tuple[str, float, float]]]:
    """Collect all diagnostic hypotheses from all agents."""
    hypotheses: Dict[str, List[Tuple[str, float, float]]] = {}
    for agent, output in agent_outputs.items():
        parsed = _safe_parse_report(output)
        diagnoses = parsed.get("diagnoses", {})
        for diagnosis, prob in diagnoses.items():
            try:
                prob_val = float(prob)
            except:
                prob_val = 1.0 if str(prob).lower() in ["true", "yes", "positive"] else 0.0
            weight = get_condition_weight(diagnosis, agent)
            if diagnosis not in hypotheses:
                hypotheses[diagnosis] = []
            hypotheses[diagnosis].append((agent, prob_val, weight))
    return hypotheses


def calculate_weighted_probability(agent_probs: List[Tuple[str, float, float]]) -> Tuple[float, float]:
    """Calculate weighted average probability and agreement score."""
    if not agent_probs:
        return 0.0, 0.0
    total_weight = sum(w for _, _, w in agent_probs)
    weighted_sum = sum(prob * weight for _, prob, weight in agent_probs)
    weighted_prob = weighted_sum / total_weight if total_weight > 0 else 0.0
    if len(agent_probs) > 1:
        probs = [p for _, p, _ in agent_probs]
        mean_prob = sum(probs) / len(probs)
        variance = sum((p - mean_prob) ** 2 for p in probs) / len(probs)
        agreement = max(0, 1 - (variance ** 0.5) * 2)
    else:
        agreement = 0.5
    return round(weighted_prob, 4), round(agreement, 3)


def identify_supporting_agents(agent_probs: List[Tuple[str, float, float]], threshold: float = 0.3) -> List[str]:
    """Identify which agents support a diagnosis."""
    return [agent for agent, prob, _ in agent_probs if prob >= threshold]


def collect_all_findings(agent_outputs: Dict[str, Dict]) -> List[Dict]:
    """Collect all findings from all agents."""
    all_findings = []
    for agent, output in agent_outputs.items():
        parsed = _safe_parse_report(output)
        findings = parsed.get("findings", [])
        for finding in findings:
            if isinstance(finding, dict):
                finding["source_agent"] = agent
                all_findings.append(finding)
    return all_findings


def collect_all_flags(agent_outputs: Dict[str, Dict]) -> List[str]:
    """Collect all critical flags from agents."""
    all_flags = []
    for agent, output in agent_outputs.items():
        parsed = _safe_parse_report(output)
        flags = parsed.get("flags", [])
        for flag in flags:
            all_flags.append(f"[{agent}] {flag}")
    return all_flags


def determine_urgency(top_diagnosis: str, flags: List[str]) -> str:
    """Determine overall case urgency."""
    critical_keywords = ["stemi", "embolism", "tamponade", "shock", "arrest", "critical"]
    combined = (top_diagnosis + " ".join(flags)).lower()
    if any(kw in combined for kw in critical_keywords):
        return "critical"
    high_keywords = ["nstemi", "failure", "effusion", "tuberculosis"]
    if any(kw in combined for kw in high_keywords):
        return "high"
    return "moderate"


def check_for_definitive_diagnosis(agent_outputs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Check if any agent has a DEFINITIVE (confirmed) diagnosis.
    Definitive findings from gold-standard tests override probability calculations.
    
    Example: CTPA filling defect = PE confirmed (not suspected)
    """
    for agent, output in agent_outputs.items():
        parsed = _safe_parse_report(output)
        
        # Check for definitive finding flag
        if parsed.get("is_definitive") or parsed.get("diagnostic_certainty") == "confirmed":
            diagnoses = parsed.get("diagnoses", {})
            if diagnoses:
                top_diagnosis = max(diagnoses.keys(), key=lambda k: diagnoses[k])
                return {
                    "diagnosis": top_diagnosis,
                    "confidence": parsed.get("confidence", 0.95),
                    "confirmed_by": agent,
                    "explanation": parsed.get("explanation", "Confirmed by gold-standard diagnostic test"),
                    "is_definitive": True
                }
    return None


def build_final_diagnosis(agent_outputs: Dict[str, Any]) -> Dict[str, Any]:
    """Build final consensus diagnosis from all agent outputs."""
    if not agent_outputs:
        return {
            "diagnosis": {"top_label": "No diagnosis - insufficient data", "confidence": 0.0, "urgency": "unknown"},
            "agents_used": [],
            "error": "No agent outputs provided"
        }
    
    # =========================================================================
    # STEP 1: Check for DEFINITIVE diagnosis from any agent
    # When a gold-standard test confirms diagnosis, we don't need probability
    # =========================================================================
    definitive = check_for_definitive_diagnosis(agent_outputs)
    
    if definitive:
        all_findings = collect_all_findings(agent_outputs)
        all_flags = collect_all_flags(agent_outputs)
        
        return {
            "diagnosis": {
                "top_label": f"{definitive['diagnosis']} - CONFIRMED",
                "probability": definitive["confidence"],
                "confidence": definitive["confidence"],
                "agreement_score": 1.0,  # N/A for confirmed diagnosis
                "supporting_agents": [definitive["confirmed_by"]],
                "urgency": "critical" if "embolism" in definitive["diagnosis"].lower() or "stemi" in definitive["diagnosis"].lower() else "high",
                "diagnostic_certainty": "CONFIRMED",
                "merged_labels": {definitive["diagnosis"]: definitive["confidence"]}
            },
            "differential_diagnoses": [],  # No differentials for confirmed diagnosis
            "all_findings": all_findings[:10],
            "critical_flags": [f"CONFIRMED: {definitive['diagnosis']} by {definitive['confirmed_by']}"] + all_flags,
            "agents_used": list(agent_outputs.keys()),
            "confirmation_source": definitive["confirmed_by"],
            "explanation": definitive["explanation"],
            "is_definitive": True,
            "agent_confidences": {agent: round(_safe_parse_report(out).get("confidence", 0.5), 3) for agent, out in agent_outputs.items()},
        }
    
    # =========================================================================
    # STEP 2: Standard probability-based consensus for non-definitive cases
    # =========================================================================
    all_hypotheses = collect_all_hypotheses(agent_outputs)
    diagnosis_scores = {}
    
    for diagnosis, agent_probs in all_hypotheses.items():
        weighted_prob, agreement = calculate_weighted_probability(agent_probs)
        supporting_agents = identify_supporting_agents(agent_probs)
        agreement_boost = 1.0 + (agreement * 0.2) if len(supporting_agents) > 1 else 1.0
        final_prob = min(0.95, weighted_prob * agreement_boost)
        diagnosis_scores[diagnosis] = {
            "probability": round(final_prob, 4),
            "agreement": agreement,
            "supporting_agents": supporting_agents,
            "agent_details": [(a, round(p, 3)) for a, p, _ in agent_probs]
        }
    
    if diagnosis_scores:
        sorted_diagnoses = sorted(diagnosis_scores.items(), key=lambda x: x[1]["probability"], reverse=True)
        top_diagnosis = sorted_diagnoses[0][0]
        top_info = sorted_diagnoses[0][1]
        differentials = [{"diagnosis": d, "probability": info["probability"]} for d, info in sorted_diagnoses[1:4] if info["probability"] > 0.15]
    else:
        top_diagnosis = "No significant diagnosis identified"
        top_info = {"probability": 0.0, "agreement": 0.0, "supporting_agents": []}
        differentials = []
    
    all_findings = collect_all_findings(agent_outputs)
    all_flags = collect_all_flags(agent_outputs)
    
    confidences = []
    for output in agent_outputs.values():
        parsed = _safe_parse_report(output)
        try:
            confidences.append(float(parsed.get("confidence", 0.5)))
        except:
            confidences.append(0.5)
    
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
    agreement_factor = top_info.get("agreement", 0.5)
    final_confidence = round(avg_confidence * 0.7 + agreement_factor * 0.3, 3)
    urgency = determine_urgency(top_diagnosis, all_flags)
    
    return {
        "diagnosis": {
            "top_label": top_diagnosis,
            "probability": top_info["probability"],
            "confidence": final_confidence,
            "agreement_score": top_info.get("agreement", 0.0),
            "supporting_agents": top_info.get("supporting_agents", []),
            "urgency": urgency,
            "merged_labels": {d: info["probability"] for d, info in diagnosis_scores.items()}
        },
        "differential_diagnoses": differentials,
        "all_findings": all_findings[:10],
        "critical_flags": all_flags,
        "agents_used": list(agent_outputs.keys()),
        "agent_confidences": {agent: round(_safe_parse_report(out).get("confidence", 0.5), 3) for agent, out in agent_outputs.items()},
    }
