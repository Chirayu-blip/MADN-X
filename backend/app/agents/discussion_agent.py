import json
from typing import Any, Dict, List, Tuple, Optional
from openai import OpenAI
import os

# ---------------------------------------------------------
# OpenAI Client
# ---------------------------------------------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =========================================================
# SAFE PARSING
# =========================================================
def _safe_parse_report(report: Any) -> Dict[str, Any]:
    """Normalize different agent report formats into a consistent dict."""
    out = {"labels": {}, "explanation": "", "confidence": None, "raw": report}

    try:
        if isinstance(report, str):
            s, e = report.find("{"), report.rfind("}")
            block = report[s:e+1] if s != -1 and e > s else report
            data = json.loads(block)
        elif isinstance(report, dict):
            data = report
        else:
            return out

        # labels
        labels = data.get("labels") or data.get("Labels")
        if isinstance(labels, dict):
            out["labels"] = labels

        # explanation
        out["explanation"] = (
            data.get("explanation")
            or data.get("reasoning")
            or data.get("summary")
            or ""
        )

        # confidence
        c = data.get("confidence")
        if isinstance(c, (int, float)):
            out["confidence"] = float(c)
        elif isinstance(c, str):
            try:
                out["confidence"] = float(c)
            except:
                pass

    except Exception:
        pass

    return out


# =========================================================
# UTIL
# =========================================================
def _bin(v: Any) -> int:
    """Normalize any truth-like value to 0/1."""
    try:
        iv = int(v)
        return 1 if iv >= 1 else 0
    except:
        return 1 if str(v).lower() in {"true", "positive", "yes"} else 0


# =========================================================
# CONFLICT DETECTION
# =========================================================
def _detect_conflicts(reports: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    tallies: Dict[str, Dict[str, int]] = {}

    for agent, rep in reports.items():
        for label, val in rep.get("labels", {}).items():
            tallies.setdefault(label, {})[agent] = _bin(val)

    return [
        {"label": lbl, "votes": votes}
        for lbl, votes in tallies.items()
        if set(votes.values()) == {0, 1}
    ]


# =========================================================
# MAJORITY CONSENSUS
# =========================================================
def _majority_consensus(reports: Dict[str, Dict[str, Any]]):
    votes: Dict[str, List[int]] = {}
    confs, explanations = [], []

    for rep in reports.values():
        if rep.get("explanation"):
            explanations.append(rep["explanation"])
        if isinstance(rep.get("confidence"), (int, float)):
            confs.append(float(rep["confidence"]))

        for label, val in rep.get("labels", {}).items():
            votes.setdefault(label, []).append(_bin(val))

    result = {lbl: 1 if sum(v) >= len(v)/2 else 0 for lbl, v in votes.items()}
    avg_conf = round(sum(confs)/len(confs), 3) if confs else 0.5

    return result, avg_conf, explanations


# =========================================================
# CLARIFICATION PROMPTS
# =========================================================
def _clarification_prompts(conflicts, symptoms, labs):
    if not conflicts:
        return []

    out = []
    if symptoms:
        out.append("Clarify present/absent symptoms with durations (fever, cough, dyspnea, chest pain, sputum).")
    if labs:
        out.append("Provide lab thresholds (CRP, WBC diff, procalcitonin, troponin, NT-proBNP).")

    for c in conflicts:
        out.append(f"For {c['label']}: specify imaging signs, ECG features, or lab thresholds to resolve disagreement.")

    return out


# =========================================================
# MULTI-TURN DEBATE ENGINE
# =========================================================
def _extract_json(text: str) -> Dict[str, Any]:
    try:
        s, e = text.find("{"), text.rfind("}")
        return json.loads(text[s:e+1])
    except:
        return {"error": "parse_failed", "raw": text}


def _debate_turn(agent: str, report: Dict, others: Dict[str, Dict]):
    """One agent re-evaluates after reading others."""
    prompt = f"""
You are the **{agent}** in a medical diagnostic committee.

Your report:
{json.dumps(report, indent=2)}

Other agents:
{json.dumps(others, indent=2)}

Identify disagreements, reconsider your opinion, and revise your labels only if justified.

Respond ONLY in JSON:
{{
  "revised_labels": {{ "Diagnosis": 0/1 }},
  "revised_confidence": 0-1,
  "explanation": "short reason"
}}
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return _extract_json(res.choices[0].message.content)


def run_debate(prior_reports: Dict[str, Any], turns: int = 2):
    """True multi-turn collaborative agent debate."""
    current = {k: _safe_parse_report(v) for k, v in prior_reports.items()}
    history = []

    for t in range(1, turns + 1):
        step = {"round": t, "agents": {}}

        for agent, rep in current.items():
            others = {k: v for k, v in current.items() if k != agent}
            updated = _debate_turn(agent, rep, others)
            step["agents"][agent] = updated

        # apply updates
        for agent, upd in step["agents"].items():
            if "revised_labels" in upd:
                current[agent]["labels"] = upd["revised_labels"]
            if "revised_confidence" in upd:
                current[agent]["confidence"] = upd["revised_confidence"]

        history.append(step)

    return {"history": history, "final": current}


# =========================================================
# MAIN WRAPPER (DISCUSSION + DEBATE + CONSENSUS)
# =========================================================
def run_discussion(
    symptoms: Optional[str],
    labs: Optional[str],
    prior_reports: Dict[str, Any],
    debate_rounds: int = 2,
):
    """Unified entry: conflict detection + debate + consensus."""
    normalized = {k: _safe_parse_report(v) for k, v in prior_reports.items()}

    conflicts = _detect_conflicts(normalized)
    prompts = _clarification_prompts(conflicts, symptoms, labs)

    debate = run_debate(prior_reports, turns=debate_rounds)

    final_consensus, conf, rationales = _majority_consensus(debate["final"])

    return {
        "conflicts_initial": conflicts,
        "clarification_prompts": prompts,
        "debate_history": debate["history"],
        "final_consensus": {
            "labels": final_consensus,
            "confidence": conf,
            "rationales": rationales[:3],
        },
        "agents_considered": list(prior_reports.keys()),
    }
