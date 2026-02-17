# 🏥 MADN-X: Multi-Agent Diagnostic Network

> **Production-grade AI clinical decision support using collaborative multi-agent reasoning with Explainable AI**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16+-black.svg)](https://nextjs.org)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-purple.svg)](https://openai.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🚀 Quick Demo

```bash
# PE Case: CTPA + Clinical Signs → Confirmed Diagnosis
curl -X POST http://localhost:8000/diagnose \
  -H "Content-Type: application/json" \
  -d '{"radiology": "CTPA shows filling defect in pulmonary artery", "explain": true}'

# Response: {"diagnosis": "Pulmonary Embolism - CONFIRMED", "confidence": 0.98, ...}
```

**Result**: 98% confidence PE diagnosis with full reasoning chain, evidence attribution, and audit trail.

---

## 🎯 What Makes This Project Stand Out

### Technical Differentiators

| Feature | Implementation | Why It Matters |
|---------|----------------|----------------|
| **Definitive Finding Detection** | Pattern matching for gold-standard tests (CTPA, STEMI criteria) | Prevents averaging away 98% confidence to 50% |
| **Evidence Hierarchy** | Classifies findings as DIAGNOSTIC vs SUPPORTIVE | Mirrors real clinical decision-making |
| **Multi-Agent Consensus** | 4 specialists with weighted voting + definitive override | Reduces single-point-of-failure |
| **Explainable AI (XAI)** | Evidence attribution, reasoning chains, counterfactuals | Builds trust, enables debugging |
| **Hash-Chained Audit Log** | Immutable entries with SHA-256 chain verification | HIPAA-ready, tamper-evident |
| **Confidence Calibration** | Brier score tracking, calibration metrics | Validates reliability of probabilities |
| **Structured OpenAPI Docs** | Comprehensive Swagger UI with examples | Production-ready API |

### Clinical Accuracy Features

```
Traditional AI:     "PE probability: 52% (averaged from conflicting signals)"
MADN-X:             "PE CONFIRMED: 98% - CTPA filling defect is diagnostic"
                    ↳ Reasoning: Gold-standard test overrides statistical averaging
```

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MADN-X ARCHITECTURE v2.0                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             |
│  ┌──────────────┐                                                           │
│  │   Frontend   │  Next.js 16 + React + Tailwind                            |
│  │   (Port 3000)│  • Dark theme professional UI                             │
│  └──────┬───────┘  • Reasoning chain visualization                          │
│         │          • Evidence attribution display                           │
│         ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        FastAPI Backend (Port 8000)                   │   |
│  │  ┌─────────────────────────────────────────────────────────────────┐ │   │
│  │  │                     /diagnose Endpoint                          │ │   │
│  │  │                                                                 │ │   │
│  │  │   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐               │ │   │
│  │  │   │🔬 Radio-│ │❤️ Cardio│ │🫁 Pulmo-│ │🧪 Patho-│             │ │   │
│  │  │   │ logist  │ │ logist  │ │ nologist│ │ logist  │               │ │   │
│  │  │   │         │ │         │ │         │ │         │               │ │   │
│  │  │   │DEFINIT- │ │DEFINIT- │ │SUPPORT- │ │SUPPORT- │               │ │   │
│  │  │   │IVE TEST │ │IVE TEST │ │IVE SIGNS│ │IVE LABS │               │ │   │
│  │  │   └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘               │ │   │
│  │  │        │           │           │           │                    │ │   │
│  │  │        └───────────┴─────┬─────┴───────────┘                    │ │   │
│  │  │                          ▼                                      │ │   │
│  │  │   ┌─────────────────────────────────────────────────┐           │ │   │
│  │  │   │              Shared Evidence Layer              │           │ │   │
│  │  │   │  • Evidence Attribution    • Finding Correlation│           │ │   │
│  │  │   │  • Definitive vs Supportive Evidence Detection  │           │ │   │
│  │  │   └─────────────────────┬───────────────────────────┘           │ │   │
│  │  │                         │                                       │ │   │
│  │  │                         ▼                                       │ │   │
│  │  │   ┌─────────────────────────────────────────────────┐           │ │   │
│  │  │   │              Consensus Agent                    │           │ │   │
│  │  │   │  • Weighted Evidence Merging                    │           │ │   │
│  │  │   │  • Agreement Scoring                            │           │ │   │
│  │  │   │  • Definitive Finding Override                  │           │ │   │
│  │  │   └─────────────────────┬───────────────────────────┘           │ │   │
│  │  │                         │                                       │ │   │
│  │  │                         ▼                                       │ │   │
│  │  │   ┌─────────────────────────────────────────────────┐           │ │   │
│  │  │   │               Safety Agent                      │           │ │   │
│  │  │   │  • Critical Condition Detection                 │           │ │   │
│  │  │   │  • Contradiction Checking                       │           │ │   │
│  │  │   │  • Confidence Calibration                       │           │ │   │
│  │  │   └─────────────────────────────────────────────────┘           │ │   │
│  │  │                                                                 │ │   │
│  │  └─────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                   │   │
│  │  │Explainabil- │  │Audit Logger │  │  Metrics    │                   │   │
│  │  │ity Engine   │  │(HIPAA-Ready)│  │  Tracker    │                   │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/MADN-X.git
cd MADN-X

# Set your OpenAI API key
export OPENAI_API_KEY=your_api_key_here

# Start everything
docker-compose up --build

# Access:
# - Frontend: http://localhost:3000
# - API Docs: http://localhost:8000/docs
# - Metrics:  http://localhost:8000/metrics
```

### Option 2: Manual Setup

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

---

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/diagnose` | POST | Main diagnostic endpoint with all agents |
| `/metrics` | GET | System performance metrics |
| `/metrics/ground-truth` | POST | Add ground truth for benchmarking |
| `/audit/verify` | GET | Verify audit chain integrity |
| `/audit/case/{id}` | GET | Get audit trail for a case |
| `/health` | GET | Health check endpoint |

### Example Request

```bash
curl -X POST "http://localhost:8000/diagnose" \
  -H "Content-Type: application/json" \
  -d '{
    "radiology": "CT angiography shows filling defect in right main pulmonary artery",
    "ecg": "Sinus tachycardia 110 bpm, S1Q3T3 pattern",
    "symptoms_text": "Sudden onset dyspnea, pleuritic chest pain",
    "lab_text": "D-dimer 2500, troponin elevated"
  }'
```

### Example Response (Abbreviated)

```json
{
  "case_id": "CASE-A1B2C3D4",
  "consensus": {
    "top_diagnosis": "Pulmonary Embolism - CONFIRMED",
    "confidence": 0.98,
    "diagnostic_certainty": "confirmed"
  },
  "explanation": {
    "one_line_explanation": "Pulmonary Embolism CONFIRMED by Pulmonary Artery Filling Defect",
    "evidence_attributions": [...],
    "reasoning_chain": [...]
  },
  "audit_id": "AUDIT-ABC123DEF456"
}
```

---

## 🔬 Supported Conditions

| Category | Conditions |
|----------|------------|
| **Pulmonary** | Pneumonia, COPD Exacerbation, Pulmonary Embolism, Tuberculosis, Asthma |
| **Cardiac** | STEMI, NSTEMI, Atrial Fibrillation, Heart Failure, Pericarditis |
| **Critical** | Cardiac Tamponade, Tension Pneumothorax, Septic Shock |

---

## 🧠 Key Design Decisions

### 1. Diagnostic vs Supportive Evidence
```
DIAGNOSTIC (Confirms):          SUPPORTIVE (Suggests):
├── CTPA filling defect → PE    ├── S1Q3T3 on ECG → PE possible
├── ST elevation → STEMI        ├── D-dimer elevated → VTE possible
└── Consolidation + fever       └── Tachycardia → Many causes
    → Pneumonia
```

### 2. Confidence Calibration
The system tracks whether predictions at each confidence level are actually correct:
- 80-100% confidence → Should be correct 80-100% of the time
- This validates the "30-40% improvement" claim with real data

### 3. Immutable Audit Trail
Every diagnosis creates a hash-chained audit entry:
```
Entry 1 [hash: abc123, prev: null]
    ↓
Entry 2 [hash: def456, prev: abc123]
    ↓
Entry 3 [hash: ghi789, prev: def456]
```
Tampering with any entry breaks the chain → detectable.

---

## 📈 Metrics Dashboard

Access `/metrics` to see:
- **Accuracy**: % of correct diagnoses (when ground truth provided)
- **Calibration Error**: How well confidence matches accuracy
- **Agent Agreement**: How often agents reach consensus
- **Latency**: Response time tracking
- **Condition Distribution**: Which conditions are most common

---

## 🛡️ Safety Features

1. **Critical Condition Detection**: Auto-flags STEMI, PE, Tamponade
2. **Contradiction Detection**: Alerts when agents disagree significantly
3. **Confidence Calibration**: Warns when confidence seems miscalibrated
4. **Hallucination Check**: GPT-based verification of reasoning

---

## 🔮 Future Roadmap

- [ ] Vision model for actual X-ray/CT image analysis
- [ ] ECG waveform analysis (not just text)
- [ ] MIMIC-III dataset benchmarking
- [ ] Multi-language support
- [ ] FHIR integration for EHR systems

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 👨‍💻 Author

**Your Name**
- Built as a demonstration of multi-agent AI systems in healthcare
- Focus on explainability, safety, and clinical accuracy

---

*⚠️ Disclaimer: This is a demonstration project and should NOT be used for actual medical diagnosis. Always consult qualified healthcare professionals.*
