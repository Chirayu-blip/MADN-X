"use client";

import { useState } from "react";

export default function CaseForm() {
  const [radiology, setRadiology] = useState("");
  const [ecg, setEcg] = useState("");
  const [symptoms, setSymptoms] = useState("");
  const [labs, setLabs] = useState("");

  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  async function runDiagnosis() {
    setLoading(true);
    setResult(null);

    const payload = {
      radiology,
      ecg,
      symptoms_text: symptoms,
      lab_text: labs
    };

    try {
      const res = await fetch("http://127.0.0.1:8000/diagnose", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      setResult(data);

    } catch (err) {
      console.error(err);
      alert("Backend not running or error occurred.");
    }

    setLoading(false);
  }

  return (
    <div className="flex flex-col gap-4 w-full max-w-2xl">

      <textarea
        className="w-full p-3 border rounded"
        placeholder="Radiology report..."
        value={radiology}
        onChange={(e) => setRadiology(e.target.value)}
      />

      <textarea
        className="w-full p-3 border rounded"
        placeholder="ECG text..."
        value={ecg}
        onChange={(e) => setEcg(e.target.value)}
      />

      <textarea
        className="w-full p-3 border rounded"
        placeholder="Symptoms..."
        value={symptoms}
        onChange={(e) => setSymptoms(e.target.value)}
      />

      <textarea
        className="w-full p-3 border rounded"
        placeholder="Lab results..."
        value={labs}
        onChange={(e) => setLabs(e.target.value)}
      />

      <button
        onClick={runDiagnosis}
        className="bg-black text-white px-6 py-3 rounded-lg"
      >
        {loading ? "Diagnosing..." : "Run Diagnosis"}
      </button>

      {/* ----- OUTPUT SECTION ----- */}
      {result && (
        <div className="mt-6 p-4 border rounded bg-zinc-100">
          <h2 className="text-xl font-semibold mb-3">Results</h2>

          <p><b>Agents Considered:</b> {result.agents_considered?.join(", ")}</p>

          <h3 className="mt-3 font-bold">Top Diagnosis:</h3>
          <p className="text-lg">{result.consensus?.top_diagnosis}</p>

          <h3 className="mt-3 font-bold">All Diagnoses:</h3>
          <pre className="bg-white p-2 rounded text-sm">
            {JSON.stringify(result.consensus?.diagnoses, null, 2)}
          </pre>

          <h3 className="mt-3 font-bold">Rationale:</h3>
          <pre className="bg-white p-2 rounded text-sm">
            {JSON.stringify(result.consensus?.rationale, null, 2)}
          </pre>
        </div>
      )}

    </div>
  );
}
