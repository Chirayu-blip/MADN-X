# app/agents/safety_agent.py
"""
Safety Agent for MADN-X Multi-Agent Diagnostic System

This agent performs critical safety checks on diagnostic outputs to ensure:
1. No dangerous diagnoses are missed
2. Critical findings trigger appropriate alerts
3. Contradictions between agents are flagged
4. Confidence levels are appropriately calibrated
5. Human review is recommended when appropriate

CRITICAL: This agent is a safety net, not a replacement for clinical judgment.
All outputs should be reviewed by qualified healthcare professionals.
"""

import json
from typing import Dict, List, Any, Optional
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ============================================================================
# CRITICAL CONDITIONS THAT MUST NOT BE MISSED
# ============================================================================

CRITICAL_CONDITIONS = {
    "STEMI": {
        "keywords": ["st elevation", "stemi", "st-elevation", "acute mi", "transmural"],
        "action": "IMMEDIATE cardiology consult, cath lab activation if confirmed",
        "time_critical": True
    },
    "Pulmonary Embolism": {
        "keywords": ["pulmonary embolism", "pe", "filling defect", "saddle embolus"],
        "action": "Anticoagulation consideration, hemodynamic assessment",
        "time_critical": True
    },
    "Tension Pneumothorax": {
        "keywords": ["tension pneumothorax", "mediastinal shift"],
        "action": "Immediate needle decompression",
        "time_critical": True
    },
    "Cardiac Tamponade": {
        "keywords": ["tamponade", "beck's triad", "pulsus paradoxus"],
        "action": "Emergent pericardiocentesis consideration",
        "time_critical": True
    },
    "Septic Shock": {
        "keywords": ["septic shock", "lactate >4", "vasopressor", "refractory hypotension"],
        "action": "Sepsis bundle, ICU care",
        "time_critical": True
    },
    "Respiratory Failure": {
        "keywords": ["respiratory failure", "intubation", "ards", "spo2 <88"],
        "action": "Ventilatory support consideration",
        "time_critical": True
    },
    "Ventricular Arrhythmia": {
        "keywords": ["ventricular tachycardia", "vt", "ventricular fibrillation", "vf"],
        "action": "ACLS protocol, defibrillation if indicated",
        "time_critical": True
    },
    "Aortic Dissection": {
        "keywords": ["aortic dissection", "intimal flap", "tearing chest pain"],
        "action": "Urgent surgical/vascular consult, BP control",
        "time_critical": True
    }
}

# ============================================================================
# DANGEROUS DRUG-DIAGNOSIS INTERACTIONS
# ============================================================================

CONTRAINDICATIONS = {
    "STEMI": ["thrombolytics contraindicated if aortic dissection suspected"],
    "Pulmonary Embolism": ["anticoagulation contraindicated if active bleeding"],
    "Atrial Fibrillation": ["rate control caution in WPW syndrome"]
}

# ============================================================================
# SAFETY CHECKS
# ============================================================================

def check_for_critical_conditions(outputs: List[Dict]) -> List[Dict]:
    """Check if any critical conditions are present in agent outputs."""
    alerts = []
    
    # Convert all outputs to searchable text
    combined_text = json.dumps(outputs).lower()
    
    for condition, config in CRITICAL_CONDITIONS.items():
        for keyword in config["keywords"]:
            if keyword.lower() in combined_text:
                alerts.append({
                    "condition": condition,
                    "matched_keyword": keyword,
                    "action_required": config["action"],
                    "time_critical": config["time_critical"],
                    "severity": "CRITICAL"
                })
                break  # Only alert once per condition
    
    return alerts


def check_for_contradictions(outputs: List[Dict]) -> List[Dict]:
    """Identify contradictions between agent outputs."""
    contradictions = []
    
    diagnoses_by_agent = {}
    for output in outputs:
        agent = output.get("agent", "unknown")
        diagnoses = output.get("diagnoses", {})
        diagnoses_by_agent[agent] = diagnoses
    
    # Check for conflicting high-probability diagnoses
    all_diagnoses = {}
    for agent, diagnoses in diagnoses_by_agent.items():
        for diagnosis, prob in diagnoses.items():
            try:
                prob_val = float(prob)
            except:
                prob_val = 1.0 if str(prob).lower() in ["true", "yes"] else 0.0
            
            if prob_val > 0.3:  # Only consider significant probabilities
                if diagnosis not in all_diagnoses:
                    all_diagnoses[diagnosis] = []
                all_diagnoses[diagnosis].append((agent, prob_val))
    
    # Find diagnoses where agents significantly disagree
    for diagnosis, agent_probs in all_diagnoses.items():
        if len(agent_probs) < 2:
            continue
        probs = [p for _, p in agent_probs]
        if max(probs) - min(probs) > 0.4:  # Significant disagreement
            contradictions.append({
                "diagnosis": diagnosis,
                "disagreement": {agent: prob for agent, prob in agent_probs},
                "severity": "moderate",
                "recommendation": "Requires additional clinical correlation"
            })
    
    return contradictions


def check_confidence_calibration(outputs: List[Dict]) -> Dict:
    """Assess if confidence levels are appropriately calibrated."""
    confidences = []
    low_confidence_agents = []
    
    for output in outputs:
        agent = output.get("agent", "unknown")
        conf = output.get("confidence", 0)
        try:
            conf_val = float(conf)
        except:
            conf_val = 0.5
        
        confidences.append(conf_val)
        if conf_val < 0.4:
            low_confidence_agents.append(agent)
    
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
    
    return {
        "average_confidence": round(avg_confidence, 3),
        "low_confidence_agents": low_confidence_agents,
        "reliability": "high" if avg_confidence > 0.6 else "moderate" if avg_confidence > 0.4 else "low"
    }


def check_missing_data(outputs: List[Dict]) -> List[str]:
    """Check if any agents flagged missing data."""
    missing = []
    
    for output in outputs:
        flags = output.get("flags", [])
        if any("INCOMPLETE" in str(f).upper() for f in flags):
            missing.append(output.get("agent", "unknown"))
    
    return missing


def assess_risk_level(critical_alerts: List, contradictions: List, confidence: Dict) -> str:
    """Determine overall risk level of the case."""
    if any(alert.get("time_critical") for alert in critical_alerts):
        return "critical"
    if len(critical_alerts) > 0:
        return "high"
    if len(contradictions) > 1 or confidence["reliability"] == "low":
        return "moderate"
    return "low"


def determine_human_review_needed(
    risk_level: str,
    critical_alerts: List,
    contradictions: List,
    missing_agents: List
) -> Dict:
    """Determine if human review is needed and why."""
    needs_review = False
    reasons = []
    
    if risk_level in ["critical", "high"]:
        needs_review = True
        reasons.append("Critical or high-risk findings present")
    
    if len(critical_alerts) > 0:
        needs_review = True
        reasons.append(f"Critical conditions detected: {[a['condition'] for a in critical_alerts]}")
    
    if len(contradictions) > 1:
        needs_review = True
        reasons.append("Significant disagreement between specialist agents")
    
    if len(missing_agents) > 1:
        needs_review = True
        reasons.append("Insufficient data for multiple agents")
    
    return {
        "needed": needs_review,
        "reasons": reasons
    }


def get_gpt_safety_assessment(outputs: List[Dict], preliminary_checks: Dict) -> Dict:
    """Get GPT assessment for additional safety validation."""
    formatted_outputs = json.dumps(outputs, indent=2)
    formatted_checks = json.dumps(preliminary_checks, indent=2)
    
    prompt = f"""You are a SAFETY VALIDATION AGENT for a medical diagnostic system.

Your job is to identify potential errors, hallucinations, or dangerous recommendations.

Agent Outputs:
{formatted_outputs}

Preliminary Safety Checks:
{formatted_checks}

Evaluate and respond in JSON format:
{{
    "hallucination_risk": "low" | "moderate" | "high",
    "hallucination_concerns": ["list specific concerns if any"],
    "medically_sound": true | false,
    "concerns": ["list of medical concerns"],
    "missing_considerations": ["important factors not addressed"],
    "final_recommendation": "summary recommendation"
}}

Return ONLY valid JSON."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            timeout=20
        )
        raw = response.choices[0].message.content
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
    except:
        pass
    
    return {
        "hallucination_risk": "unknown",
        "medically_sound": False,
        "concerns": ["Unable to complete GPT safety assessment"],
        "final_recommendation": "Manual review required due to safety check failure"
    }


def safety_agent(agent_outputs: List[Dict]) -> Dict[str, Any]:
    """
    Main safety agent function.
    
    Performs comprehensive safety checks on all agent outputs.
    
    Args:
        agent_outputs: List of outputs from specialist agents
        
    Returns:
        Safety assessment with risk level and recommendations
    """
    if not agent_outputs:
        return {
            "risk_level": "high",
            "needs_human_review": True,
            "explanation": "No agent outputs provided for safety evaluation",
            "critical_alerts": [],
            "contradictions": [],
            "confidence_assessment": {"reliability": "unknown"},
            "flags": ["NO_DATA_PROVIDED"]
        }
    
    # Run all safety checks
    critical_alerts = check_for_critical_conditions(agent_outputs)
    contradictions = check_for_contradictions(agent_outputs)
    confidence_assessment = check_confidence_calibration(agent_outputs)
    missing_agents = check_missing_data(agent_outputs)
    
    # Assess overall risk
    risk_level = assess_risk_level(critical_alerts, contradictions, confidence_assessment)
    
    # Determine if human review needed
    human_review = determine_human_review_needed(
        risk_level, critical_alerts, contradictions, missing_agents
    )
    
    # Prepare preliminary checks for GPT
    preliminary = {
        "critical_alerts": critical_alerts,
        "contradictions": contradictions,
        "confidence": confidence_assessment,
        "missing_data": missing_agents,
        "risk_level": risk_level
    }
    
    # Get GPT safety assessment
    gpt_assessment = get_gpt_safety_assessment(agent_outputs, preliminary)
    
    # Build final flags
    flags = []
    if risk_level == "critical":
        flags.append("CRITICAL: Immediate clinical attention required")
    for alert in critical_alerts:
        flags.append(f"CRITICAL: {alert['condition']} - {alert['action_required']}")
    if gpt_assessment.get("hallucination_risk") == "high":
        flags.append("WARNING: High hallucination risk detected")
    if not gpt_assessment.get("medically_sound", True):
        flags.append("WARNING: Medical soundness concerns identified")
    
    return {
        "risk_level": risk_level,
        "needs_human_review": human_review["needed"],
        "review_reasons": human_review["reasons"],
        "critical_alerts": critical_alerts,
        "contradictions": contradictions,
        "confidence_assessment": confidence_assessment,
        "missing_data_agents": missing_agents,
        "gpt_assessment": gpt_assessment,
        "flags": flags,
        "explanation": gpt_assessment.get("final_recommendation", 
            "Safety evaluation complete. See flags and alerts for details."),
        "disclaimer": "This is an AI-assisted diagnostic tool. All outputs must be reviewed by qualified healthcare professionals. Do not make clinical decisions based solely on this output."
    }
