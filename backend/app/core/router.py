# app/core/router.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List
from fastapi.responses import FileResponse
import uuid, os, time

from .intake import process_case
from .explainability import generate_explanation
from .audit_logger import get_audit_logger
from .metrics import get_metrics_tracker
from .auth import (
    create_user, authenticate_user, create_tokens, refresh_access_token,
    get_current_user, require_auth, User, AuthTokens
)
from app.agents.radiologist import radiologist_agent
from app.agents.cardiologist import cardiologist_agent
from app.agents.pulmonologist import pulmonologist_agent
from app.agents.pathologist import pathologist_agent
from app.agents.discussion_agent import run_discussion  # your Day 5 util
from app.agents.consensus_agent import build_final_diagnosis  # your Day 6 util
from app.agents.safety_agent import safety_agent           # your Day 7 util
from app.utils.pdf_report import generate_pdf_report       # NEW util

router = APIRouter()


# ============================================================================
# AUTH MODELS
# ============================================================================

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: Optional[str] = "user"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


# ============================================================================
# AUTH ENDPOINTS
# ============================================================================

@router.post("/auth/register", tags=["Authentication"])
def register_user(payload: RegisterRequest):
    """
    Register a new user account.
    
    - **email**: Valid email address
    - **password**: Password (min 6 characters recommended)
    - **name**: Display name
    - **role**: User role (user, clinician, admin)
    """
    try:
        user = create_user(
            email=payload.email,
            password=payload.password,
            name=payload.name,
            role=payload.role or "user"
        )
        tokens = create_tokens(user)
        return {
            "status": "success",
            "message": "User registered successfully",
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_type": "bearer",
            "expires_in": tokens.expires_in,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration error: {e}")


@router.post("/auth/login", tags=["Authentication"])
def login_user(payload: LoginRequest):
    """
    Login with email and password to get access tokens.
    
    Returns JWT access token (24h) and refresh token (7 days).
    """
    try:
        user = authenticate_user(payload.email, payload.password)
        tokens = create_tokens(user)
        return {
            "status": "success",
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_type": "bearer",
            "expires_in": tokens.expires_in,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login error: {e}")


@router.post("/auth/refresh", tags=["Authentication"])
def refresh_token(payload: RefreshRequest):
    """
    Get new access token using refresh token.
    """
    try:
        tokens = refresh_access_token(payload.refresh_token)
        return {
            "status": "success",
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_type": "bearer",
            "expires_in": tokens.expires_in
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token refresh error: {e}")


@router.get("/auth/me", tags=["Authentication"])
def get_current_user_info(user: User = Depends(require_auth)):
    """
    Get current authenticated user's information.
    
    Requires: Bearer token in Authorization header.
    """
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "created_at": user.created_at,
        "last_login": user.last_login
    }


# --------- Original Models ----------
class IntakeRequest(BaseModel):
    case: dict

class RadiologyRequest(BaseModel):
    radiology: str

class CardiologyRequest(BaseModel):
    ecg: str

class PulmoRequest(BaseModel):
    symptoms_text: str

class LabRequest(BaseModel):
    lab_text: str

class CaseRequest(BaseModel):
    radiology: Optional[str] = None
    ecg: Optional[str] = None
    symptoms_text: Optional[str] = None
    lab_text: Optional[str] = None
    # New fields for enhanced features
    explain: Optional[bool] = True           # Include explainability
    ground_truth: Optional[str] = None       # For validation/benchmarking
    case_id: Optional[str] = None            # Custom case ID

class DiscussionRequest(BaseModel):
    symptoms: Optional[str] = None
    radiology: Optional[str] = None
    ecg: Optional[str] = None
    labs: Optional[str] = None
    prior_reports: Optional[Dict[str, Any]] = None
    max_rounds: int = 2

class PdfRequest(BaseModel):
    case_id: str
    case: CaseRequest
# ---------------------------

@router.post("/intake")
def intake_endpoint(payload: IntakeRequest):
    return {"processed_case": process_case(payload.case)}

@router.post("/radiologist")
def radiologist_endpoint(payload: RadiologyRequest):
    return {"radiologist_report": radiologist_agent(payload.radiology)}

@router.post("/cardiologist")
def cardiologist_endpoint(payload: CardiologyRequest):
    return {"cardiology_report": cardiologist_agent(payload.ecg)}

@router.post("/pulmonologist")
def pulmonologist_endpoint(payload: PulmoRequest):
    return {"pulmonology_report": pulmonologist_agent(payload.symptoms_text)}

@router.post("/pathologist")
def pathologist_endpoint(payload: LabRequest):
    return {"pathology_report": pathologist_agent(payload.lab_text)}

# ---- Single diagnose endpoint (remove duplicates) ----
# -----------------------------
# Multi-agent consensus logic
# -----------------------------
def _check_for_definitive(agent_outputs):
    """
    Check if any agent has a DEFINITIVE (confirmed) diagnosis.
    When a gold-standard test confirms diagnosis, that takes precedence.
    """
    for out in agent_outputs:
        if out.get("is_definitive") or out.get("diagnostic_certainty") == "confirmed":
            diagnoses = out.get("diagnoses", {})
            if diagnoses:
                top_diagnosis = max(diagnoses.keys(), key=lambda k: diagnoses[k])
                return {
                    "diagnosis": top_diagnosis,
                    "confidence": out.get("confidence", 0.95),
                    "agent": out.get("agent"),
                    "explanation": out.get("explanation", "Confirmed by diagnostic test")
                }
    return None


def _normalize_diagnosis(diag: str) -> str:
    """Normalize diagnosis names for consistent matching."""
    diag_lower = diag.lower().strip()
    # Map common variations to standard names
    if "pneumonia" in diag_lower:
        return "Community-Acquired Pneumonia"
    if "stemi" in diag_lower or ("st" in diag_lower and "elevation" in diag_lower and "mi" in diag_lower):
        return "ST-Elevation Myocardial Infarction"
    if "nstemi" in diag_lower or ("non" in diag_lower and "st" in diag_lower and "mi" in diag_lower):
        return "Non-ST-Elevation Myocardial Infarction"
    if "myocardial infarction" in diag_lower and "st" not in diag_lower:
        return "Myocardial Infarction"
    if "atrial fibrillation" in diag_lower or "afib" in diag_lower or "a fib" in diag_lower:
        return "Atrial Fibrillation"
    if "pulmonary embolism" in diag_lower or diag_lower == "pe":
        return "Pulmonary Embolism"
    if "copd" in diag_lower:
        return "COPD Exacerbation"
    if "heart failure" in diag_lower or "chf" in diag_lower:
        return "Acute Decompensated Heart Failure"
    return diag


def _weighted_merge(agent_outputs):
    """
    Merge agent outputs with support for definitive findings.
    """
    # FIRST: Check for definitive findings
    definitive = _check_for_definitive(agent_outputs)
    if definitive:
        # Definitive finding takes precedence
        return (
            {definitive["diagnosis"]: definitive["confidence"]},
            f"{definitive['diagnosis']} - CONFIRMED",
            [f"{definitive['agent']} -> {definitive['diagnosis']} - CONFIRMED ({definitive['confidence']})"]
        )
    
    # STANDARD: Weighted merge from all agents
    totals = {}
    counts = {}
    rationales = {}
    agent_weights = {
        "radiologist": 1.2,
        "cardiologist": 1.2,
        "pulmonologist": 1.0,
        "pathologist": 0.9
    }

    for out in agent_outputs:
        agent_name = out.get("agent", "unknown")
        weight = agent_weights.get(agent_name, 1.0)
        
        # Get diagnoses from the dict
        diagnoses = out.get("diagnoses", {})
        
        # ALSO consider top_diagnosis if diagnoses is empty but agent has confidence
        if not diagnoses and out.get("confidence", 0) > 0.25:
            top_diag = out.get("top_diagnosis", "")
            if top_diag and "No" not in top_diag and "Normal" not in top_diag:
                # Extract diagnosis name (remove probability/confidence text)
                clean_diag = top_diag.split("(")[0].strip().replace(" - CONFIRMED", "")
                diagnoses = {clean_diag: out.get("confidence", 0.3)}
        
        for diagnosis, prob in diagnoses.items():
            try:
                p = float(prob)
            except Exception:
                p = 1.0 if str(prob).lower() in {"true", "yes", "positive"} else 0.0
            
            # Normalize diagnosis name
            norm_diag = _normalize_diagnosis(diagnosis)
            
            # Apply weight
            weighted_p = p * weight

            totals[norm_diag] = totals.get(norm_diag, 0.0) + weighted_p
            counts[norm_diag] = counts.get(norm_diag, 0) + weight
            rationales.setdefault(norm_diag, []).append(
                f"{agent_name} -> {out['top_diagnosis']} ({out['confidence']})"
            )

    if not totals:
        return {}, None, []

    # Weighted average probabilities
    merged = {k: round(totals[k] / counts[k], 4) for k in totals}

    # Labels we DON'T want as the *main* diagnosis
    benign_labels = {
        "Normal Sinus Rhythm",
        "No Finding",
        "No significant lab abnormality",
        "No specific pulmonary abnormality identified",
    }

    # Primary diagnosis: ignore benign/background labels
    primary_candidates = {
        k: v for k, v in merged.items() if k not in benign_labels
    }

    if primary_candidates:
        top = max(primary_candidates, key=primary_candidates.get)
    else:
        # Fallback: if literally everything is benign, just pick the global max
        top = max(merged, key=merged.get) if merged else None

    return merged, top, rationales.get(top, [])


@router.post("/diagnose")
def multi_agent_reasoning(payload: CaseRequest):
    """Main diagnostic endpoint with explainability, audit logging, and metrics."""
    
    # Start timing
    start_time = time.time()
    case_id = payload.case_id or f"CASE-{uuid.uuid4().hex[:8].upper()}"
    
    agent_outputs = []
    agent_outputs_dict = {}

    if payload.radiology:
        result = radiologist_agent(payload.radiology)
        agent_outputs.append(result)
        agent_outputs_dict["radiologist"] = result

    if payload.ecg:
        result = cardiologist_agent(payload.ecg)
        agent_outputs.append(result)
        agent_outputs_dict["cardiologist"] = result

    if payload.symptoms_text:
        result = pulmonologist_agent(payload.symptoms_text)
        agent_outputs.append(result)
        agent_outputs_dict["pulmonologist"] = result

    if payload.lab_text:
        result = pathologist_agent(payload.lab_text)
        agent_outputs.append(result)
        agent_outputs_dict["pathologist"] = result

    if not agent_outputs:
        return {"error": "No medical inputs provided.", "case_id": case_id}

    merged, top_label, rationale = _weighted_merge(agent_outputs)
    
    # Calculate timing
    latency_ms = (time.time() - start_time) * 1000
    
    # Determine if definitive
    is_definitive = any(
        output.get("is_definitive", False) 
        for output in agent_outputs
    )
    
    # Get confidence from top diagnosis
    confidence = merged.get(top_label, 0.5) if isinstance(merged, dict) else 0.5
    if is_definitive:
        confidence = max(confidence, 0.95)
    
    # Determine diagnostic certainty
    if is_definitive:
        diagnostic_certainty = "confirmed"
    elif confidence >= 0.8:
        diagnostic_certainty = "probable"
    elif confidence >= 0.5:
        diagnostic_certainty = "possible"
    else:
        diagnostic_certainty = "uncertain"
    
    # Build response
    response = {
        "case_id": case_id,
        "agents_considered": [a["agent"] for a in agent_outputs],
        "agent_outputs": agent_outputs,
        "consensus": {
            "diagnoses": merged,
            "top_diagnosis": top_label,
            "confidence": confidence,
            "diagnostic_certainty": diagnostic_certainty,
            "rationale": rationale,
        },
        "latency_ms": round(latency_ms, 2)
    }
    
    # Add explainability if requested
    if payload.explain:
        try:
            differential_diagnoses = list(merged.keys())[:5] if isinstance(merged, dict) else []
            explanation = generate_explanation(
                agent_outputs=agent_outputs_dict,
                final_diagnosis=top_label.split("-")[0].strip() if top_label else "Unknown",
                final_confidence=confidence,
                is_definitive=is_definitive,
                differential_diagnoses=differential_diagnoses
            )
            response["explanation"] = explanation.to_dict()
        except Exception as e:
            response["explanation"] = {"error": str(e)}
    
    # Record metrics
    try:
        tracker = get_metrics_tracker()
        tracker.record_diagnosis(
            case_id=case_id,
            predicted_diagnosis=top_label,
            predicted_confidence=confidence,
            agents_used=[a["agent"] for a in agent_outputs],
            agent_outputs=agent_outputs_dict,
            latency_ms=latency_ms,
            is_definitive=is_definitive,
            actual_diagnosis=payload.ground_truth
        )
    except Exception:
        pass  # Don't fail diagnosis if metrics fail
    
    # Audit log
    try:
        logger = get_audit_logger()
        audit_id = logger.log_diagnosis(
            case_id=case_id,
            final_diagnosis=top_label,
            confidence=confidence,
            diagnostic_certainty=diagnostic_certainty,
            agents_used=[a["agent"] for a in agent_outputs],
            agent_outputs=agent_outputs_dict,
            input_data={
                "radiology": payload.radiology,
                "ecg": payload.ecg,
                "symptoms": payload.symptoms_text,
                "labs": payload.lab_text
            },
            critical_flags=[f for a in agent_outputs for f in a.get("flags", [])]
        )
        response["audit_id"] = audit_id
    except Exception:
        pass  # Don't fail diagnosis if audit fails

    return response

# Day 5: discussion
@router.post("/discussion")
def discussion_endpoint(payload: DiscussionRequest):
    try:
        prior = payload.prior_reports.copy() if payload.prior_reports else {}
        if payload.radiology and "radiologist_report" not in prior:
            prior["radiologist_report"] = radiologist_agent(payload.radiology)
        if payload.ecg and "cardiology_report" not in prior:
            prior["cardiology_report"] = cardiologist_agent(payload.ecg)
        if payload.symptoms and "pulmonology_report" not in prior:
            prior["pulmonology_report"] = pulmonologist_agent(payload.symptoms)
        if payload.labs and "pathology_report" not in prior:
            prior["pathology_report"] = pathologist_agent(payload.labs)

        return run_discussion(
            symptoms=payload.symptoms,
            labs=payload.labs,
            prior_reports=prior,
            max_rounds=payload.max_rounds
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Discussion agent error: {e}")

# Day 6: consensus object builder (if you want the fancier struct)
@router.post("/consensus")
def consensus_endpoint(payload: CaseRequest):
    agent_reports = {}
    if payload.radiology:
        agent_reports["radiologist"] = radiologist_agent(payload.radiology)
    if payload.ecg:
        agent_reports["cardiologist"] = cardiologist_agent(payload.ecg)
    if payload.symptoms_text:
        agent_reports["pulmonologist"] = pulmonologist_agent(payload.symptoms_text)
    if payload.lab_text:
        agent_reports["pathologist"] = pathologist_agent(payload.lab_text)

    if not agent_reports:
        raise HTTPException(status_code=400, detail="No agent inputs provided.")
    return build_final_diagnosis(agent_reports)

# Day 7: safety
@router.post("/safety")
def safety_check(payload: CaseRequest):
    agent_outputs = []
    if payload.radiology:
        agent_outputs.append(radiologist_agent(payload.radiology))
    if payload.ecg:
        agent_outputs.append(cardiologist_agent(payload.ecg))
    if payload.symptoms_text:
        agent_outputs.append(pulmonologist_agent(payload.symptoms_text))
    if payload.lab_text:
        agent_outputs.append(pathologist_agent(payload.lab_text))
    if not agent_outputs:
        raise HTTPException(status_code=400, detail="No agent outputs to evaluate.")

    # your safety_agent should tolerate both dicts and JSON strings
    safety_result = safety_agent(agent_outputs)
    return {
        "safety_agent": safety_result,
        "agents_checked": [getattr(a, "get", lambda _:_ )("agent") if isinstance(a, dict) else "unknown" for a in agent_outputs],
        "raw_agent_outputs": agent_outputs
    }


# ============================================================================
# PDF REPORT ENDPOINTS
# ============================================================================

@router.post("/report/pdf", tags=["Reports"])
def report_pdf(payload: PdfRequest):
    """Generate PDF report from case data."""
    # 1) run agents
    case = payload.case
    agent_outputs = {}
    if case.radiology:
        agent_outputs["radiologist"] = radiologist_agent(case.radiology)
    if case.ecg:
        agent_outputs["cardiologist"] = cardiologist_agent(case.ecg)
    if case.symptoms_text:
        agent_outputs["pulmonologist"] = pulmonologist_agent(case.symptoms_text)
    if case.lab_text:
        agent_outputs["pathologist"] = pathologist_agent(case.lab_text)

    # 2) get consensus
    merged, top, rationale = _weighted_merge(agent_outputs.values())
    consensus = {"diagnoses": merged, "top": top, "rationale": rationale}

    # 3) write PDF
    os.makedirs("reports", exist_ok=True)
    filename = f"report_{payload.case_id}_{uuid.uuid4().hex[:8]}.pdf"
    path = os.path.join("reports", filename)

    generate_pdf_report(
        path,
        case_id=payload.case_id,
        patient_case=case.model_dump(),
        consensus=consensus,
        agents=agent_outputs
    )
    return FileResponse(path=path, filename=filename, media_type="application/pdf")


class ExportPdfRequest(BaseModel):
    """Request to export diagnosis result as PDF."""
    case_id: str
    diagnosis_result: Dict[str, Any]  # The full result from /diagnose


@router.post("/report/export-pdf", tags=["Reports"])
def export_diagnosis_pdf(payload: ExportPdfRequest):
    """
    Export a completed diagnosis as a PDF report.
    
    Pass the full response from /diagnose to generate a PDF.
    """
    try:
        result = payload.diagnosis_result
        case_id = payload.case_id or result.get("case_id", "UNKNOWN")
        
        # Extract data from diagnosis result
        agent_outputs = {}
        for agent_output in result.get("agent_outputs", []):
            agent_name = agent_output.get("agent", "unknown")
            agent_outputs[agent_name] = agent_output
        
        consensus = result.get("consensus", {})
        
        # Build patient case from input (if available)
        patient_case = {
            "radiology": "",
            "ecg": "",
            "symptoms_text": "",
            "lab_text": ""
        }
        
        # Try to extract from agent inputs
        for agent_output in result.get("agent_outputs", []):
            snippet = agent_output.get("input_snippet", "")
            agent = agent_output.get("agent", "")
            if agent == "radiologist":
                patient_case["radiology"] = snippet
            elif agent == "cardiologist":
                patient_case["ecg"] = snippet
            elif agent == "pulmonologist":
                patient_case["symptoms_text"] = snippet
            elif agent == "pathologist":
                patient_case["lab_text"] = snippet
        
        # Generate PDF
        os.makedirs("reports", exist_ok=True)
        filename = f"MADN-X_Report_{case_id}.pdf"
        path = os.path.join("reports", filename)
        
        generate_pdf_report(
            path,
            case_id=case_id,
            patient_case=patient_case,
            consensus=consensus,
            agents=agent_outputs
        )
        
        return FileResponse(
            path=path, 
            filename=filename, 
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation error: {e}")


# ============================================================================
# METRICS & MONITORING ENDPOINTS
# ============================================================================

@router.get("/metrics")
def get_system_metrics():
    """Get comprehensive system performance metrics."""
    try:
        tracker = get_metrics_tracker()
        return {
            "status": "ok",
            "metrics": tracker.get_metrics_summary()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metrics error: {e}")


@router.get("/metrics/export")
def export_metrics():
    """Export metrics to file and return path."""
    try:
        tracker = get_metrics_tracker()
        export_path = tracker.export_metrics()
        return {"status": "ok", "export_path": export_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {e}")


@router.get("/audit/verify")
def verify_audit_chain():
    """Verify the integrity of the audit log chain."""
    try:
        logger = get_audit_logger()
        result = logger.verify_chain_integrity()
        return {"status": "ok", "integrity": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit verification error: {e}")


@router.get("/audit/case/{case_id}")
def get_audit_for_case(case_id: str):
    """Get all audit entries for a specific case."""
    try:
        logger = get_audit_logger()
        entries = logger.get_entries_for_case(case_id)
        return {"status": "ok", "case_id": case_id, "entries": entries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit retrieval error: {e}")


class GroundTruthRequest(BaseModel):
    case_id: str
    actual_diagnosis: str


@router.post("/metrics/ground-truth")
def add_ground_truth(payload: GroundTruthRequest):
    """Add ground truth for a case (for benchmarking)."""
    try:
        tracker = get_metrics_tracker()
        tracker.add_ground_truth(payload.case_id, payload.actual_diagnosis)
        return {"status": "ok", "message": f"Ground truth added for case {payload.case_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding ground truth: {e}")


@router.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for monitoring."""
    try:
        logger = get_audit_logger()
        audit_valid = logger.verify_chain_integrity().get("is_valid", False)
    except:
        audit_valid = "unknown"
    
    return {
        "status": "healthy",
        "version": "2.0.0",
        "agents": ["radiologist", "cardiologist", "pulmonologist", "pathologist"],
        "audit_chain_valid": audit_valid,
        "features": [
            "multi-agent-diagnosis",
            "explainability",
            "audit-logging",
            "metrics-tracking",
            "definitive-finding-detection",
            "jwt-authentication",
            "pdf-export"
        ]
    }
