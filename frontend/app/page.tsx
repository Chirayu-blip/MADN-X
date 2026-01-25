"use client";

import { useState } from "react";

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

interface Finding {
  name: string;
  severity?: string;
  clinical_significance?: string;
  present?: boolean;
}

interface AgentOutput {
  agent: string;
  top_diagnosis: string;
  confidence: number;
  explanation: string;
  diagnoses: Record<string, number>;
  findings?: Finding[];
  flags?: string[];
  is_definitive?: boolean;
  diagnostic_certainty?: string;
}

interface EvidenceAttribution {
  evidence_type: string;
  finding: string;
  contribution: string;
  weight: number;
  reasoning: string;
  source_agent: string;
}

interface ReasoningStep {
  step_number: number;
  agent: string;
  action: string;
  description: string;
  evidence_used: string[];
  conclusion: string;
  confidence_delta: number;
}

interface Explanation {
  diagnosis: string;
  confidence: number;
  diagnostic_certainty: string;
  evidence_attributions: EvidenceAttribution[];
  reasoning_chain: ReasoningStep[];
  one_line_explanation: string;
  detailed_explanation: string;
}

interface DiagnosisResult {
  case_id: string;
  agents_considered: string[];
  agent_outputs: AgentOutput[];
  consensus: {
    diagnoses: Record<string, number>;
    top_diagnosis: string;
    confidence: number;
    diagnostic_certainty?: string;
  };
  latency_ms: number;
  explanation?: Explanation;
  audit_id?: string;
  error?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

function ConfidenceBar({ confidence, isDefinitive }: { confidence: number; isDefinitive?: boolean }) {
  const percentage = Math.round(confidence * 100);
  const bgColor = isDefinitive 
    ? "bg-green-500" 
    : percentage >= 80 
      ? "bg-green-500" 
      : percentage >= 50 
        ? "bg-yellow-500" 
        : "bg-red-400";
  
  return (
    <div className="w-full bg-gray-200 rounded-full h-3 mt-1">
      <div 
        className={`h-3 rounded-full ${bgColor} transition-all duration-500`} 
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: "bg-red-100 text-red-800 border-red-300",
    high: "bg-orange-100 text-orange-800 border-orange-300",
    moderate: "bg-yellow-100 text-yellow-800 border-yellow-300",
    low: "bg-green-100 text-green-800 border-green-300",
  };
  
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border ${colors[severity] || colors.low}`}>
      {severity.toUpperCase()}
    </span>
  );
}

function ContributionBadge({ contribution }: { contribution: string }) {
  const colors: Record<string, string> = {
    decisive: "bg-purple-100 text-purple-800",
    strong: "bg-blue-100 text-blue-800",
    moderate: "bg-cyan-100 text-cyan-800",
    weak: "bg-gray-100 text-gray-800",
    opposing: "bg-red-100 text-red-800",
  };
  
  return (
    <span className={`text-xs px-2 py-0.5 rounded ${colors[contribution] || colors.weak}`}>
      {contribution.toUpperCase()}
    </span>
  );
}

function AgentIcon({ agent }: { agent: string }) {
  const icons: Record<string, string> = {
    radiologist: "🔬",
    cardiologist: "❤️",
    pulmonologist: "🫁",
    pathologist: "🧪",
  };
  return <span className="text-2xl">{icons[agent] || "🩺"}</span>;
}

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export default function Home() {
  const [radiology, setRadiology] = useState("");
  const [ecg, setEcg] = useState("");
  const [symptoms, setSymptoms] = useState("");
  const [labText, setLabText] = useState("");
  const [explain, setExplain] = useState(true);

  const [loading, setLoading] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [result, setResult] = useState<DiagnosisResult | null>(null);
  const [activeTab, setActiveTab] = useState<"agents" | "reasoning" | "evidence">("agents");
  
  // Auth state
  const [user, setUser] = useState<{ name: string; email: string; role: string } | null>(null);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authName, setAuthName] = useState("");
  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);

  // Load user from localStorage on mount
  useState(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("madn_user");
      if (stored) setUser(JSON.parse(stored));
    }
  });

  async function handleAuth() {
    setAuthLoading(true);
    setAuthError("");
    
    try {
      const endpoint = authMode === "login" ? "/auth/login" : "/auth/register";
      const body = authMode === "login" 
        ? { email: authEmail, password: authPassword }
        : { email: authEmail, password: authPassword, name: authName };
      
      const response = await fetch(`http://127.0.0.1:8000${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      
      const data = await response.json();
      
      if (response.ok && data.access_token) {
        localStorage.setItem("madn_token", data.access_token);
        localStorage.setItem("madn_refresh", data.refresh_token);
        localStorage.setItem("madn_user", JSON.stringify(data.user));
        setUser(data.user);
        setShowAuthModal(false);
        setAuthEmail("");
        setAuthPassword("");
        setAuthName("");
      } else {
        setAuthError(data.detail || "Authentication failed");
      }
    } catch (error) {
      setAuthError("Could not connect to server");
    }
    
    setAuthLoading(false);
  }

  function handleLogout() {
    localStorage.removeItem("madn_token");
    localStorage.removeItem("madn_refresh");
    localStorage.removeItem("madn_user");
    setUser(null);
  }

  async function handleSubmit() {
    setLoading(true);
    setResult(null);

    const payload = {
      radiology: radiology || null,
      ecg: ecg || null,
      symptoms_text: symptoms || null,
      lab_text: labText || null,
      explain: explain,
    };

    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      const token = localStorage.getItem("madn_token");
      if (token) headers["Authorization"] = `Bearer ${token}`;
      
      const response = await fetch("http://127.0.0.1:8000/diagnose", {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error(error);
      setResult({ error: "Could not reach backend server." } as DiagnosisResult);
    }

    setLoading(false);
  }

  async function handleDownloadPdf() {
    if (!result) return;
    setPdfLoading(true);
    
    try {
      const response = await fetch("http://127.0.0.1:8000/report/export-pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          case_id: result.case_id,
          diagnosis_result: result
        }),
      });
      
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `MADN-X_Report_${result.case_id}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        console.error("PDF generation failed");
      }
    } catch (error) {
      console.error("Error downloading PDF:", error);
    }
    
    setPdfLoading(false);
  }

  function loadSampleCase() {
    setRadiology("CT angiography shows filling defect in right main pulmonary artery consistent with pulmonary embolism");
    setEcg("Sinus tachycardia 110 bpm, S1Q3T3 pattern, right axis deviation");
    setSymptoms("Sudden onset dyspnea, pleuritic chest pain, recent leg surgery");
    setLabText("D-dimer 2500, troponin elevated");
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6">
      {/* ═══════════ AUTH MODAL ═══════════ */}
      {showAuthModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 border border-slate-700 rounded-2xl p-8 w-full max-w-md">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-semibold text-white">
                {authMode === "login" ? "Sign In" : "Create Account"}
              </h2>
              <button onClick={() => setShowAuthModal(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>
            
            <div className="space-y-4">
              {authMode === "register" && (
                <input
                  type="text"
                  placeholder="Full Name"
                  value={authName}
                  onChange={(e) => setAuthName(e.target.value)}
                  className="w-full bg-slate-900/50 border border-slate-600 rounded-lg p-3 text-white placeholder-slate-500"
                />
              )}
              <input
                type="email"
                placeholder="Email"
                value={authEmail}
                onChange={(e) => setAuthEmail(e.target.value)}
                className="w-full bg-slate-900/50 border border-slate-600 rounded-lg p-3 text-white placeholder-slate-500"
              />
              <input
                type="password"
                placeholder="Password"
                value={authPassword}
                onChange={(e) => setAuthPassword(e.target.value)}
                className="w-full bg-slate-900/50 border border-slate-600 rounded-lg p-3 text-white placeholder-slate-500"
              />
              
              {authError && <p className="text-red-400 text-sm">{authError}</p>}
              
              <button
                onClick={handleAuth}
                disabled={authLoading}
                className="w-full py-3 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-semibold rounded-lg hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50"
              >
                {authLoading ? "Loading..." : authMode === "login" ? "Sign In" : "Create Account"}
              </button>
              
              <p className="text-center text-slate-400 text-sm">
                {authMode === "login" ? "Don't have an account?" : "Already have an account?"}{" "}
                <button
                  onClick={() => setAuthMode(authMode === "login" ? "register" : "login")}
                  className="text-cyan-400 hover:underline"
                >
                  {authMode === "login" ? "Sign up" : "Sign in"}
                </button>
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ═══════════ HEADER ═══════════ */}
      <header className="text-center mb-10">
        {/* Auth buttons */}
        <div className="absolute top-4 right-4">
          {user ? (
            <div className="flex items-center gap-3">
              <span className="text-slate-400 text-sm">👤 {user.name}</span>
              <button
                onClick={handleLogout}
                className="px-3 py-1 bg-slate-700 text-slate-300 rounded-lg text-sm hover:bg-slate-600"
              >
                Logout
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowAuthModal(true)}
              className="px-4 py-2 bg-cyan-600 text-white rounded-lg text-sm hover:bg-cyan-500"
            >
              Sign In
            </button>
          )}
        </div>
        
        <h1 className="text-5xl font-bold text-white mb-2">
          <span className="bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
            MADN-X
          </span>
        </h1>
        <p className="text-slate-400 text-lg">
          Multi-Agent Diagnostic Network with Explainable AI
        </p>
        <div className="flex justify-center gap-2 mt-3 flex-wrap">
          <span className="px-3 py-1 bg-green-900/50 text-green-400 rounded-full text-xs">
            ✓ Explainable AI
          </span>
          <span className="px-3 py-1 bg-blue-900/50 text-blue-400 rounded-full text-xs">
            ✓ HIPAA-Ready Audit
          </span>
          <span className="px-3 py-1 bg-purple-900/50 text-purple-400 rounded-full text-xs">
            ✓ Multi-Agent Consensus
          </span>
          <span className="px-3 py-1 bg-orange-900/50 text-orange-400 rounded-full text-xs">
            ✓ JWT Auth
          </span>
          <span className="px-3 py-1 bg-pink-900/50 text-pink-400 rounded-full text-xs">
            ✓ PDF Export
          </span>
        </div>
      </header>

      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* ═══════════ INPUT PANEL ═══════════ */}
        <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-2xl p-6 shadow-xl">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              📋 Clinical Data Input
            </h2>
            <button
              onClick={loadSampleCase}
              className="text-sm text-cyan-400 hover:text-cyan-300 underline"
            >
              Load Sample PE Case
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm text-slate-400 mb-1">🔬 Radiology Report</label>
              <textarea
                placeholder="CT, X-ray, MRI findings..."
                className="w-full bg-slate-900/50 border border-slate-600 rounded-lg p-3 text-white placeholder-slate-500 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                rows={3}
                value={radiology}
                onChange={(e) => setRadiology(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm text-slate-400 mb-1">❤️ ECG Interpretation</label>
              <textarea
                placeholder="Rhythm, axis, ST changes..."
                className="w-full bg-slate-900/50 border border-slate-600 rounded-lg p-3 text-white placeholder-slate-500 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                rows={2}
                value={ecg}
                onChange={(e) => setEcg(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm text-slate-400 mb-1">🫁 Symptoms</label>
              <textarea
                placeholder="Chief complaint, history..."
                className="w-full bg-slate-900/50 border border-slate-600 rounded-lg p-3 text-white placeholder-slate-500 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                rows={2}
                value={symptoms}
                onChange={(e) => setSymptoms(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm text-slate-400 mb-1">🧪 Lab Results</label>
              <textarea
                placeholder="CBC, BMP, cardiac enzymes..."
                className="w-full bg-slate-900/50 border border-slate-600 rounded-lg p-3 text-white placeholder-slate-500 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                rows={2}
                value={labText}
                onChange={(e) => setLabText(e.target.value)}
              />
            </div>

            <div className="flex items-center gap-2 pt-2">
              <input
                type="checkbox"
                id="explain"
                checked={explain}
                onChange={(e) => setExplain(e.target.checked)}
                className="w-4 h-4 text-cyan-500 bg-slate-700 border-slate-600 rounded focus:ring-cyan-500"
              />
              <label htmlFor="explain" className="text-sm text-slate-400">
                Include Explainability (reasoning chain, evidence attribution)
              </label>
            </div>

            <button
              onClick={handleSubmit}
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-semibold rounded-lg hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-cyan-500/25"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  Analyzing with AI Agents...
                </span>
              ) : (
                "🩺 Run Multi-Agent Diagnosis"
              )}
            </button>
          </div>
        </div>

        {/* ═══════════ RESULTS PANEL ═══════════ */}
        <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-2xl p-6 shadow-xl">
          {!result && !loading && (
            <div className="h-full flex items-center justify-center text-slate-500">
              <div className="text-center">
                <div className="text-6xl mb-4">🏥</div>
                <p>Enter clinical data and run diagnosis</p>
                <p className="text-sm mt-2">4 specialist AI agents will analyze the case</p>
              </div>
            </div>
          )}

          {loading && (
            <div className="h-full flex items-center justify-center text-slate-400">
              <div className="text-center">
                <div className="text-6xl mb-4 animate-pulse">🧠</div>
                <p className="text-lg">Multi-Agent Analysis in Progress...</p>
                <div className="flex justify-center gap-4 mt-6">
                  {["🔬", "❤️", "🫁", "🧪"].map((icon, i) => (
                    <div key={i} className="animate-bounce" style={{ animationDelay: `${i * 0.1}s` }}>
                      <span className="text-3xl">{icon}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {result && !result.error && (
            <div className="space-y-6">
              {/* ─────────── CONSENSUS HEADER ─────────── */}
              <div className={`p-4 rounded-xl border ${
                result.consensus.diagnostic_certainty === "confirmed" 
                  ? "bg-green-900/30 border-green-600" 
                  : "bg-slate-700/50 border-slate-600"
              }`}>
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-xs text-slate-400 uppercase tracking-wide">Final Diagnosis</p>
                    <h3 className="text-2xl font-bold text-white mt-1">
                      {result.consensus.top_diagnosis}
                    </h3>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-slate-400">Confidence</p>
                    <p className="text-3xl font-bold text-cyan-400">
                      {Math.round(result.consensus.confidence * 100)}%
                    </p>
                  </div>
                </div>
                <ConfidenceBar 
                  confidence={result.consensus.confidence} 
                  isDefinitive={result.consensus.diagnostic_certainty === "confirmed"}
                />
                {result.explanation && (
                  <p className="text-sm text-slate-300 mt-3 italic">
                    "{result.explanation.one_line_explanation}"
                  </p>
                )}
              </div>

              {/* ─────────── METADATA ─────────── */}
              <div className="flex justify-between items-center">
                <div className="flex gap-4 text-xs text-slate-400">
                  <span>Case: {result.case_id}</span>
                  <span>•</span>
                  <span>Latency: {result.latency_ms.toFixed(0)}ms</span>
                  {result.audit_id && (
                    <>
                      <span>•</span>
                      <span>Audit: {result.audit_id}</span>
                    </>
                  )}
                </div>
                
                {/* PDF Download Button */}
                <button
                  onClick={handleDownloadPdf}
                  disabled={pdfLoading}
                  className="flex items-center gap-2 px-3 py-1.5 bg-red-600 hover:bg-red-500 disabled:bg-slate-600 text-white text-sm rounded-lg transition-colors"
                >
                  {pdfLoading ? (
                    <>
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                      </svg>
                      Generating...
                    </>
                  ) : (
                    <>📄 Download PDF</>
                  )}
                </button>
              </div>

              {/* ─────────── TAB NAVIGATION ─────────── */}
              <div className="flex gap-2 border-b border-slate-700">
                {[
                  { id: "agents", label: "Agent Outputs", icon: "🧠" },
                  { id: "reasoning", label: "Reasoning Chain", icon: "🔗" },
                  { id: "evidence", label: "Evidence", icon: "📊" },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    className={`px-4 py-2 text-sm font-medium transition-all ${
                      activeTab === tab.id
                        ? "text-cyan-400 border-b-2 border-cyan-400"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    {tab.icon} {tab.label}
                  </button>
                ))}
              </div>

              {/* ─────────── AGENTS TAB ─────────── */}
              {activeTab === "agents" && (
                <div className="space-y-4 max-h-96 overflow-y-auto pr-2">
                  {result.agent_outputs.map((agent, i) => (
                    <div
                      key={i}
                      className={`p-4 rounded-lg border ${
                        agent.is_definitive
                          ? "bg-green-900/20 border-green-600"
                          : "bg-slate-700/30 border-slate-600"
                      }`}
                    >
                      <div className="flex items-center gap-3 mb-2">
                        <AgentIcon agent={agent.agent} />
                        <div className="flex-1">
                          <h4 className="font-semibold text-white capitalize">
                            {agent.agent}
                            {agent.is_definitive && (
                              <span className="ml-2 text-xs bg-green-600 text-white px-2 py-0.5 rounded">
                                DEFINITIVE
                              </span>
                            )}
                          </h4>
                          <p className="text-sm text-slate-400">{agent.top_diagnosis}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-2xl font-bold text-cyan-400">
                            {Math.round(agent.confidence * 100)}%
                          </p>
                        </div>
                      </div>
                      <p className="text-sm text-slate-300">{agent.explanation}</p>
                      
                      {/* Findings */}
                      {agent.findings && agent.findings.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {agent.findings.slice(0, 5).map((finding, j) => (
                            <span
                              key={j}
                              className="text-xs px-2 py-1 bg-slate-600/50 text-slate-300 rounded"
                            >
                              {finding.name}
                              {finding.severity && (
                                <span className="ml-1">
                                  <SeverityBadge severity={finding.severity} />
                                </span>
                              )}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Flags */}
                      {agent.flags && agent.flags.length > 0 && (
                        <div className="mt-2">
                          {agent.flags.map((flag, j) => (
                            <p key={j} className="text-xs text-orange-400">⚠️ {flag}</p>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* ─────────── REASONING TAB ─────────── */}
              {activeTab === "reasoning" && result.explanation && (
                <div className="space-y-4 max-h-96 overflow-y-auto pr-2">
                  {result.explanation.reasoning_chain.map((step, i) => (
                    <div key={i} className="flex gap-4">
                      <div className="flex flex-col items-center">
                        <div className="w-8 h-8 bg-cyan-600 rounded-full flex items-center justify-center text-white font-bold text-sm">
                          {step.step_number}
                        </div>
                        {i < result.explanation!.reasoning_chain.length - 1 && (
                          <div className="w-0.5 h-full bg-slate-600 mt-2"/>
                        )}
                      </div>
                      <div className="flex-1 pb-4">
                        <div className="flex items-center gap-2 mb-1">
                          <AgentIcon agent={step.agent} />
                          <span className="font-semibold text-white capitalize">{step.agent}</span>
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            step.action === "confirmed" 
                              ? "bg-green-600 text-white" 
                              : "bg-blue-600 text-white"
                          }`}>
                            {step.action.toUpperCase()}
                          </span>
                        </div>
                        <p className="text-sm text-slate-300">{step.conclusion}</p>
                        <div className="flex gap-2 mt-2 flex-wrap">
                          {step.evidence_used.slice(0, 3).map((ev, j) => (
                            <span key={j} className="text-xs px-2 py-1 bg-slate-700 text-slate-300 rounded">
                              {ev}
                            </span>
                          ))}
                        </div>
                        <p className="text-xs text-cyan-400 mt-1">
                          Confidence Δ: +{(step.confidence_delta * 100).toFixed(1)}%
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* ─────────── EVIDENCE TAB ─────────── */}
              {activeTab === "evidence" && result.explanation && (
                <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
                  {result.explanation.evidence_attributions.map((attr, i) => (
                    <div key={i} className="p-3 bg-slate-700/30 rounded-lg border border-slate-600">
                      <div className="flex justify-between items-start mb-1">
                        <div className="flex items-center gap-2">
                          <ContributionBadge contribution={attr.contribution} />
                          <span className="font-medium text-white">{attr.finding}</span>
                        </div>
                        <span className="text-sm text-cyan-400 font-mono">
                          {(attr.weight * 100).toFixed(0)}%
                        </span>
                      </div>
                      <p className="text-sm text-slate-400">{attr.reasoning}</p>
                      <p className="text-xs text-slate-500 mt-1">Source: {attr.source_agent}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {result?.error && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="text-6xl mb-4">❌</div>
                <p className="text-red-400">{result.error}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ═══════════ FOOTER ═══════════ */}
      <footer className="text-center mt-12 text-slate-500 text-sm">
        <p>MADN-X v2.0 • Multi-Agent Diagnostic Network</p>
        <p className="mt-1">Built with FastAPI, Next.js, and GPT-4</p>
      </footer>
    </div>
  );
}
