"use client";

import Link from "next/link";

export default function ArchitecturePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6">
      {/* Header */}
      <header className="text-center mb-10">
        <Link href="/" className="text-cyan-400 hover:text-cyan-300 text-sm">
          ← Back to Diagnostic Interface
        </Link>
        <h1 className="text-4xl font-bold text-white mt-4 mb-2">
          <span className="bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
            MADN-X Architecture
          </span>
        </h1>
        <p className="text-slate-400">Multi-Agent Diagnostic Network - System Design</p>
      </header>

      <div className="max-w-6xl mx-auto space-y-8">
        {/* Main Architecture Diagram */}
        <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-2xl p-8">
          <h2 className="text-xl font-semibold text-white mb-6">🏗️ System Architecture</h2>
          
          <pre className="text-xs md:text-sm text-cyan-300 overflow-x-auto font-mono leading-relaxed">
{`
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              MADN-X ARCHITECTURE                                 │
│                     Multi-Agent Diagnostic Network v2.0                          │
└─────────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────────┐
                              │   🌐 FRONTEND       │
                              │   Next.js + React   │
                              │   Tailwind CSS      │
                              └──────────┬──────────┘
                                         │
                                         ▼
                    ┌────────────────────────────────────────┐
                    │              🔌 API GATEWAY            │
                    │         FastAPI REST Endpoints         │
                    │    /diagnose  /metrics  /audit         │
                    └────────────────────┬───────────────────┘
                                         │
                    ┌────────────────────┴───────────────────┐
                    │                                        │
                    ▼                                        ▼
        ┌───────────────────────┐             ┌──────────────────────┐
        │     📥 INTAKE         │             │   📊 OBSERVABILITY   │
        │   Case Normalization  │             │                      │
        │   Data Validation     │             │  ┌────────────────┐  │
        └───────────┬───────────┘             │  │ Audit Logger   │  │
                    │                         │  │ (Hash Chain)   │  │
                    ▼                         │  └────────────────┘  │
        ┌───────────────────────┐             │  ┌────────────────┐  │
        │     🔀 ROUTER         │             │  │ Metrics Tracker│  │
        │   Agent Orchestration │             │  │ (Calibration)  │  │
        │   Parallel Dispatch   │             │  └────────────────┘  │
        └───────────┬───────────┘             │  ┌────────────────┐  │
                    │                         │  │ Explainability │  │
        ┌───────────┴───────────┐             │  │ Engine (XAI)   │  │
        │                       │             │  └────────────────┘  │
        ▼                       ▼             └──────────────────────┘
┌───────────────────────────────────────────────────────────────────┐
│                    🧠 SPECIALIST AGENTS LAYER                      │
│                                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐
│  │   🔬         │  │   ❤️         │  │   🫁         │  │   🧪            │
│  │ RADIOLOGIST  │  │ CARDIOLOGIST │  │ PULMONOLOGIST│  │ PATHOLOGIST    │
│  │              │  │              │  │              │  │                │
│  │ • CT/MRI     │  │ • ECG        │  │ • Symptoms   │  │ • Labs         │
│  │ • X-Ray      │  │ • Echo       │  │ • PFTs       │  │ • Biomarkers   │
│  │ • Ultrasound │  │ • Rhythm     │  │ • History    │  │ • Blood Work   │
│  │              │  │              │  │              │  │                │
│  │ DEFINITIVE:  │  │ DEFINITIVE:  │  │ SUPPORTIVE:  │  │ SUPPORTIVE:    │
│  │ CTPA→PE 98%  │  │ STE→STEMI    │  │ Sx+Signs     │  │ D-dimer, Trop  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────────┘
│                                                                    │
└────────────────────────────────┬───────────────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │    🛡️ SAFETY AGENT     │
                    │   Critical Findings    │
                    │   Drug Interactions    │
                    │   Urgency Flagging     │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │   🎯 CONSENSUS AGENT   │
                    │                        │
                    │  • Definitive Check    │
                    │    (No averaging if    │
                    │    gold-standard found)│
                    │                        │
                    │  • Weighted Merge      │
                    │    (Agent confidence   │
                    │    + specialty weight) │
                    │                        │
                    │  • Agreement Analysis  │
                    │    (Multi-agent vote)  │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │  📝 FINAL DIAGNOSIS    │
                    │                        │
                    │  {                     │
                    │    diagnosis: "PE",    │
                    │    confidence: 0.98,   │
                    │    certainty: "CONFIRM"│
                    │    explanation: {...}  │
                    │    audit_id: "..."     │
                    │  }                     │
                    └────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           🤖 AI BACKBONE                                         │
│                                                                                  │
│    OpenAI GPT-4o-mini  │  Structured Outputs  │  Medical Prompt Engineering      │
└─────────────────────────────────────────────────────────────────────────────────┘
`}
          </pre>
        </div>

        {/* Data Flow */}
        <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-2xl p-8">
          <h2 className="text-xl font-semibold text-white mb-6">🔄 Diagnostic Pipeline Flow</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {[
              { step: 1, icon: "📥", title: "Intake", desc: "Patient data received and normalized" },
              { step: 2, icon: "🔀", title: "Dispatch", desc: "Parallel agent execution" },
              { step: 3, icon: "🧠", title: "Analysis", desc: "4 specialists analyze independently" },
              { step: 4, icon: "🎯", title: "Consensus", desc: "Definitive findings prioritized" },
              { step: 5, icon: "📝", title: "Output", desc: "Explainable diagnosis + audit" },
            ].map((item) => (
              <div key={item.step} className="relative">
                <div className="bg-slate-700/50 rounded-lg p-4 text-center border border-slate-600">
                  <div className="text-3xl mb-2">{item.icon}</div>
                  <div className="text-sm font-semibold text-white">{item.title}</div>
                  <div className="text-xs text-slate-400 mt-1">{item.desc}</div>
                </div>
                {item.step < 5 && (
                  <div className="hidden md:block absolute top-1/2 -right-2 transform -translate-y-1/2 text-cyan-400">
                    →
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Key Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-slate-800/50 backdrop-blur border border-green-700 rounded-2xl p-6">
            <h3 className="text-lg font-semibold text-green-400 mb-4">🎯 Definitive Detection</h3>
            <p className="text-slate-300 text-sm mb-4">
              Gold-standard findings are prioritized over statistical averaging.
            </p>
            <div className="bg-slate-900/50 rounded p-3 text-xs font-mono text-green-300">
              CTPA + Filling Defect<br/>
              → PE CONFIRMED (98%)<br/>
              <span className="text-slate-500"># No averaging needed</span>
            </div>
          </div>

          <div className="bg-slate-800/50 backdrop-blur border border-blue-700 rounded-2xl p-6">
            <h3 className="text-lg font-semibold text-blue-400 mb-4">🔗 Reasoning Chain</h3>
            <p className="text-slate-300 text-sm mb-4">
              Step-by-step explanation of how each agent contributed to the diagnosis.
            </p>
            <div className="bg-slate-900/50 rounded p-3 text-xs font-mono text-blue-300">
              Step 1: Pulmonologist<br/>
              → Dyspnea detected (+12%)<br/>
              Step 2: Radiologist<br/>
              → CTPA positive (+86%)
            </div>
          </div>

          <div className="bg-slate-800/50 backdrop-blur border border-purple-700 rounded-2xl p-6">
            <h3 className="text-lg font-semibold text-purple-400 mb-4">🔒 Audit Trail</h3>
            <p className="text-slate-300 text-sm mb-4">
              HIPAA-ready hash-chained audit log for compliance and traceability.
            </p>
            <div className="bg-slate-900/50 rounded p-3 text-xs font-mono text-purple-300">
              audit_id: AUDIT-A1B2C3<br/>
              hash: 7f8a9b...<br/>
              prev_hash: 4d5e6f...
            </div>
          </div>
        </div>

        {/* Tech Stack */}
        <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-2xl p-8">
          <h2 className="text-xl font-semibold text-white mb-6">🛠️ Technology Stack</h2>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { name: "FastAPI", type: "Backend", color: "text-green-400" },
              { name: "Next.js 16", type: "Frontend", color: "text-cyan-400" },
              { name: "GPT-4o-mini", type: "AI Model", color: "text-purple-400" },
              { name: "Python 3.11+", type: "Runtime", color: "text-yellow-400" },
              { name: "TypeScript", type: "Language", color: "text-blue-400" },
              { name: "Tailwind CSS", type: "Styling", color: "text-pink-400" },
              { name: "Docker", type: "Deployment", color: "text-blue-300" },
              { name: "OpenAPI 3.0", type: "Documentation", color: "text-orange-400" },
            ].map((tech) => (
              <div key={tech.name} className="bg-slate-700/30 rounded-lg p-3 text-center">
                <div className={`font-semibold ${tech.color}`}>{tech.name}</div>
                <div className="text-xs text-slate-500">{tech.type}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="text-center mt-12 text-slate-500 text-sm">
        <p>MADN-X v2.0 • Multi-Agent Diagnostic Network</p>
        <div className="flex justify-center gap-4 mt-2">
          <Link href="/" className="text-cyan-400 hover:text-cyan-300">
            Diagnostic Interface
          </Link>
          <span>•</span>
          <a href="http://localhost:8000/docs" target="_blank" className="text-cyan-400 hover:text-cyan-300">
            API Docs
          </a>
          <span>•</span>
          <a href="http://localhost:8000/redoc" target="_blank" className="text-cyan-400 hover:text-cyan-300">
            ReDoc
          </a>
        </div>
      </footer>
    </div>
  );
}
