from dotenv import load_dotenv
import os

# FIX: Load .env using absolute path
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.core.router import router

# ═══════════════════════════════════════════════════════════════════════════════
# MADN-X: Multi-Agent Diagnostic Network
# A production-grade AI diagnostic system with explainability & audit logging
# ═══════════════════════════════════════════════════════════════════════════════

def custom_openapi():
    """Generate custom OpenAPI schema with comprehensive documentation."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="MADN-X Multi-Agent Diagnostic API",
        version="2.0.0",
        description="""
# 🏥 MADN-X: Multi-Agent Diagnostic Network

A sophisticated AI-powered medical diagnostic system that simulates a **virtual tumor board** 
of specialist physicians to provide comprehensive diagnostic assessments.

## 🏗️ Architecture

```
Patient Data → Intake → Specialist Agents → Consensus Engine → Explainable Diagnosis
                           ↓
             ┌─────────────┼─────────────┐
             │             │             │
        Radiologist  Cardiologist  Pulmonologist
             │             │             │
             └─────────────┼─────────────┘
                           ↓
                    Pathologist
                           ↓
                   Safety Agent
                           ↓
                 Consensus Agent
```

## 🌟 Key Features

### 1. **Multi-Agent Reasoning**
- 4 specialist agents (Radiologist, Cardiologist, Pulmonologist, Pathologist)
- Independent analysis with domain-specific expertise
- Weighted consensus based on diagnostic certainty

### 2. **Definitive Finding Detection**
- Distinguishes between **diagnostic** vs **supportive** evidence
- CTPA filling defect → PE confirmed (0.98)
- ST elevation → STEMI confirmed
- Consolidation on X-ray → Pneumonia confirmed

### 3. **Explainable AI (XAI)**
- Evidence attribution for each finding
- Step-by-step reasoning chain
- Counterfactual analysis ("What if X was negative?")
- Confidence decomposition

### 4. **HIPAA-Ready Audit Logging**
- Immutable hash-chained audit trail
- Every diagnosis is logged with full context
- Chain integrity verification
- Compliance-ready export

### 5. **Metrics & Benchmarking**
- Track accuracy, precision, recall, F1
- Confidence calibration (Brier score)
- Latency monitoring per agent
- Ground truth feedback loop

## 📊 Example Response

When you call `/diagnose` with PE patient data:
- Radiologist detects CTPA filling defect → **CONFIRMED** at 0.98
- Cardiologist notes S1Q3T3 pattern → **supportive** evidence
- Pulmonologist flags sudden dyspnea → **supportive** evidence
- Consensus: **Pulmonary Embolism - CONFIRMED**

## 🔒 Safety Features

- Critical finding alerts (troponin elevation, unstable rhythms)
- Drug interaction warnings
- Differential diagnosis suggestions
- Urgency flagging for emergency cases
        """,
        routes=app.routes,
    )
    
    # Add custom tags with descriptions
    openapi_schema["tags"] = [
        {
            "name": "Diagnosis",
            "description": "Core diagnostic endpoints - analyze patient data and get AI-powered diagnoses"
        },
        {
            "name": "Metrics",
            "description": "Performance tracking and benchmarking endpoints"
        },
        {
            "name": "Audit",
            "description": "HIPAA-ready audit logging and compliance endpoints"
        },
        {
            "name": "Health",
            "description": "System health and status checks"
        }
    ]
    
    # Add contact and license info
    openapi_schema["info"]["contact"] = {
        "name": "MADN-X Team",
        "url": "https://github.com/yourusername/madn-x",
        "email": "contact@madn-x.ai"
    }
    openapi_schema["info"]["license"] = {
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app = FastAPI(
    title="MADN-X Multi-Agent Diagnostic API",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.openapi = custom_openapi

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include router
app.include_router(router)

@app.get("/", tags=["Health"])
def root():
    """Root endpoint - API status check."""
    return {
        "service": "MADN-X Multi-Agent Diagnostic Network",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs",
        "redoc": "/redoc"
    }