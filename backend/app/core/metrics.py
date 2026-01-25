# app/core/metrics.py
"""
Metrics & Benchmarking Module for MADN-X

This module tracks diagnostic performance and provides real metrics.
Essential for validating the "30-40% improvement" claim.

Metrics Tracked:
1. Diagnostic Accuracy - Agreement with confirmed diagnoses
2. Confidence Calibration - Do high-confidence predictions match accuracy?
3. Agent Agreement Rate - How often do agents agree?
4. Latency Metrics - Response time tracking
5. Coverage - Which conditions are well-supported?
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import defaultdict
import statistics


@dataclass
class DiagnosticResult:
    """A single diagnostic result for tracking."""
    case_id: str
    timestamp: str
    predicted_diagnosis: str
    predicted_confidence: float
    actual_diagnosis: Optional[str]  # Ground truth if known
    is_correct: Optional[bool]
    agents_used: List[str]
    agent_agreement_rate: float
    latency_ms: float
    is_definitive: bool


@dataclass 
class ConfidenceBucket:
    """Metrics for a confidence range."""
    range_start: float
    range_end: float
    total_predictions: int
    correct_predictions: int
    accuracy: float
    
    @property
    def calibration_error(self) -> float:
        """Expected calibration error for this bucket."""
        expected = (self.range_start + self.range_end) / 2
        return abs(self.accuracy - expected)


@dataclass
class AgentMetrics:
    """Metrics for a single agent."""
    agent_name: str
    total_calls: int
    avg_confidence: float
    avg_latency_ms: float
    findings_per_call: float
    critical_findings_rate: float


@dataclass
class SystemMetrics:
    """Overall system performance metrics."""
    total_cases: int
    accuracy: Optional[float]          # If ground truth available
    avg_confidence: float
    confidence_calibration_error: float
    agent_agreement_rate: float
    avg_latency_ms: float
    definitive_diagnosis_rate: float
    
    # Per-agent breakdown
    agent_metrics: Dict[str, AgentMetrics]
    
    # Per-condition breakdown
    condition_counts: Dict[str, int]
    condition_accuracy: Dict[str, float]
    
    # Confidence calibration
    calibration_buckets: List[ConfidenceBucket]


class MetricsTracker:
    """Tracks and computes diagnostic performance metrics."""
    
    def __init__(self, metrics_dir: str = "metrics"):
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(exist_ok=True)
        self.results_file = self.metrics_dir / "diagnostic_results.jsonl"
        self._results_cache: List[DiagnosticResult] = []
        self._load_results()
    
    def _load_results(self):
        """Load existing results from file."""
        if self.results_file.exists():
            with open(self.results_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        self._results_cache.append(DiagnosticResult(**data))
                    except:
                        continue
    
    def record_diagnosis(
        self,
        case_id: str,
        predicted_diagnosis: str,
        predicted_confidence: float,
        agents_used: List[str],
        agent_outputs: Dict[str, Any],
        latency_ms: float,
        is_definitive: bool = False,
        actual_diagnosis: str = None
    ):
        """Record a diagnostic result for metrics."""
        
        # Calculate agent agreement rate
        diagnoses = []
        for output in agent_outputs.values():
            if isinstance(output, dict):
                top = output.get("top_diagnosis", "")
                if top:
                    # Normalize diagnosis name
                    diagnoses.append(top.split("(")[0].strip().lower())
        
        if diagnoses:
            most_common = max(set(diagnoses), key=diagnoses.count)
            agreement_rate = diagnoses.count(most_common) / len(diagnoses)
        else:
            agreement_rate = 0.0
        
        # Determine correctness if ground truth available
        is_correct = None
        if actual_diagnosis:
            is_correct = predicted_diagnosis.lower().strip() in actual_diagnosis.lower().strip() or \
                         actual_diagnosis.lower().strip() in predicted_diagnosis.lower().strip()
        
        result = DiagnosticResult(
            case_id=case_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            predicted_diagnosis=predicted_diagnosis,
            predicted_confidence=predicted_confidence,
            actual_diagnosis=actual_diagnosis,
            is_correct=is_correct,
            agents_used=agents_used,
            agent_agreement_rate=round(agreement_rate, 3),
            latency_ms=round(latency_ms, 2),
            is_definitive=is_definitive
        )
        
        # Save to file
        with open(self.results_file, 'a') as f:
            f.write(json.dumps(asdict(result)) + "\n")
        
        self._results_cache.append(result)
    
    def add_ground_truth(self, case_id: str, actual_diagnosis: str):
        """Add ground truth for a previously recorded case."""
        updated = False
        new_results = []
        
        for result in self._results_cache:
            if result.case_id == case_id:
                result.actual_diagnosis = actual_diagnosis
                result.is_correct = result.predicted_diagnosis.lower().strip() in actual_diagnosis.lower().strip()
                updated = True
            new_results.append(result)
        
        if updated:
            self._results_cache = new_results
            # Rewrite file
            with open(self.results_file, 'w') as f:
                for result in self._results_cache:
                    f.write(json.dumps(asdict(result)) + "\n")
    
    def compute_metrics(self) -> SystemMetrics:
        """Compute comprehensive system metrics."""
        if not self._results_cache:
            return self._empty_metrics()
        
        results = self._results_cache
        
        # Basic counts
        total_cases = len(results)
        
        # Accuracy (only for cases with ground truth)
        labeled_results = [r for r in results if r.is_correct is not None]
        accuracy = None
        if labeled_results:
            accuracy = sum(1 for r in labeled_results if r.is_correct) / len(labeled_results)
        
        # Confidence stats
        confidences = [r.predicted_confidence for r in results]
        avg_confidence = statistics.mean(confidences)
        
        # Agreement rate
        agreement_rates = [r.agent_agreement_rate for r in results]
        avg_agreement = statistics.mean(agreement_rates)
        
        # Latency
        latencies = [r.latency_ms for r in results]
        avg_latency = statistics.mean(latencies)
        
        # Definitive rate
        definitive_count = sum(1 for r in results if r.is_definitive)
        definitive_rate = definitive_count / total_cases
        
        # Condition distribution
        condition_counts = defaultdict(int)
        condition_correct = defaultdict(int)
        condition_total = defaultdict(int)
        
        for result in results:
            diag = result.predicted_diagnosis.split("-")[0].strip()
            condition_counts[diag] += 1
            if result.is_correct is not None:
                condition_total[diag] += 1
                if result.is_correct:
                    condition_correct[diag] += 1
        
        condition_accuracy = {
            diag: condition_correct[diag] / condition_total[diag]
            for diag in condition_total if condition_total[diag] > 0
        }
        
        # Confidence calibration
        calibration_buckets = self._compute_calibration(labeled_results)
        calibration_error = statistics.mean([b.calibration_error for b in calibration_buckets]) if calibration_buckets else 0.0
        
        # Agent metrics (simplified)
        agent_metrics = self._compute_agent_metrics(results)
        
        return SystemMetrics(
            total_cases=total_cases,
            accuracy=round(accuracy, 4) if accuracy else None,
            avg_confidence=round(avg_confidence, 4),
            confidence_calibration_error=round(calibration_error, 4),
            agent_agreement_rate=round(avg_agreement, 4),
            avg_latency_ms=round(avg_latency, 2),
            definitive_diagnosis_rate=round(definitive_rate, 4),
            agent_metrics=agent_metrics,
            condition_counts=dict(condition_counts),
            condition_accuracy={k: round(v, 4) for k, v in condition_accuracy.items()},
            calibration_buckets=calibration_buckets
        )
    
    def _compute_calibration(self, labeled_results: List[DiagnosticResult]) -> List[ConfidenceBucket]:
        """Compute confidence calibration buckets."""
        if not labeled_results:
            return []
        
        buckets = []
        ranges = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]
        
        for start, end in ranges:
            in_bucket = [r for r in labeled_results if start <= r.predicted_confidence < end]
            if not in_bucket:
                continue
            
            correct = sum(1 for r in in_bucket if r.is_correct)
            accuracy = correct / len(in_bucket) if in_bucket else 0.0
            
            buckets.append(ConfidenceBucket(
                range_start=start,
                range_end=end,
                total_predictions=len(in_bucket),
                correct_predictions=correct,
                accuracy=round(accuracy, 4)
            ))
        
        return buckets
    
    def _compute_agent_metrics(self, results: List[DiagnosticResult]) -> Dict[str, AgentMetrics]:
        """Compute per-agent metrics."""
        agent_data = defaultdict(lambda: {"calls": 0, "confidences": [], "latencies": []})
        
        for result in results:
            for agent in result.agents_used:
                agent_data[agent]["calls"] += 1
                # Approximate agent latency as fraction of total
                agent_data[agent]["latencies"].append(result.latency_ms / len(result.agents_used))
        
        metrics = {}
        for agent, data in agent_data.items():
            metrics[agent] = AgentMetrics(
                agent_name=agent,
                total_calls=data["calls"],
                avg_confidence=0.0,  # Would need per-agent tracking
                avg_latency_ms=round(statistics.mean(data["latencies"]), 2) if data["latencies"] else 0.0,
                findings_per_call=0.0,  # Would need per-agent tracking
                critical_findings_rate=0.0
            )
        
        return metrics
    
    def _empty_metrics(self) -> SystemMetrics:
        """Return empty metrics when no data available."""
        return SystemMetrics(
            total_cases=0,
            accuracy=None,
            avg_confidence=0.0,
            confidence_calibration_error=0.0,
            agent_agreement_rate=0.0,
            avg_latency_ms=0.0,
            definitive_diagnosis_rate=0.0,
            agent_metrics={},
            condition_counts={},
            condition_accuracy={},
            calibration_buckets=[]
        )
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a JSON-serializable metrics summary."""
        metrics = self.compute_metrics()
        
        return {
            "summary": {
                "total_cases": metrics.total_cases,
                "accuracy": f"{metrics.accuracy:.1%}" if metrics.accuracy else "N/A (no ground truth)",
                "avg_confidence": f"{metrics.avg_confidence:.1%}",
                "calibration_error": f"{metrics.confidence_calibration_error:.3f}",
                "agent_agreement": f"{metrics.agent_agreement_rate:.1%}",
                "avg_latency": f"{metrics.avg_latency_ms:.0f}ms",
                "definitive_rate": f"{metrics.definitive_diagnosis_rate:.1%}"
            },
            "condition_distribution": metrics.condition_counts,
            "condition_accuracy": metrics.condition_accuracy,
            "calibration": [
                {
                    "confidence_range": f"{b.range_start:.0%}-{b.range_end:.0%}",
                    "predictions": b.total_predictions,
                    "accuracy": f"{b.accuracy:.1%}",
                    "calibration_error": f"{b.calibration_error:.3f}"
                }
                for b in metrics.calibration_buckets
            ],
            "agents": {
                name: {
                    "calls": m.total_calls,
                    "avg_latency": f"{m.avg_latency_ms:.0f}ms"
                }
                for name, m in metrics.agent_metrics.items()
            }
        }
    
    def export_metrics(self, output_file: str = None) -> str:
        """Export metrics to JSON file."""
        if not output_file:
            output_file = f"metrics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        output_path = self.metrics_dir / output_file
        
        with open(output_path, 'w') as f:
            json.dump(self.get_metrics_summary(), f, indent=2)
        
        return str(output_path)


# Global metrics tracker instance
_metrics_tracker: Optional[MetricsTracker] = None


def get_metrics_tracker() -> MetricsTracker:
    """Get the global metrics tracker instance."""
    global _metrics_tracker
    if _metrics_tracker is None:
        metrics_dir = os.environ.get("METRICS_DIR", "metrics")
        _metrics_tracker = MetricsTracker(metrics_dir)
    return _metrics_tracker
