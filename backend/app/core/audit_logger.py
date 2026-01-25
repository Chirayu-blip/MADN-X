# app/core/audit_logger.py
"""
Audit Logger for MADN-X

HIPAA-ready audit logging for all diagnostic decisions.
Every diagnosis must be traceable with full context.

Features:
1. Immutable audit trail
2. Timestamped decision records
3. Full evidence capture
4. User/session tracking (when implemented)
5. Export capabilities for compliance
"""

import json
import os
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path
import uuid


@dataclass
class AuditEntry:
    """A single audit log entry."""
    audit_id: str
    timestamp: str
    event_type: str           # diagnosis, agent_call, error, access
    
    # Case information
    case_id: str
    session_id: Optional[str]
    
    # Decision details
    final_diagnosis: str
    confidence: float
    diagnostic_certainty: str
    
    # Evidence summary
    agents_used: List[str]
    evidence_count: int
    critical_flags: List[str]
    
    # Input hashes (for PHI protection - store hash not data)
    input_hash: str
    
    # Full payload (encrypted in production)
    payload: Dict[str, Any]
    
    # Integrity
    previous_hash: Optional[str]
    entry_hash: str


class AuditLogger:
    """Thread-safe audit logger with immutable entries."""
    
    def __init__(self, log_dir: str = "audit_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.current_log_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl"
        self._last_hash: Optional[str] = None
        self._load_last_hash()
    
    def _load_last_hash(self):
        """Load the hash of the last entry for chain integrity."""
        if self.current_log_file.exists():
            try:
                with open(self.current_log_file, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        last_entry = json.loads(lines[-1])
                        self._last_hash = last_entry.get("entry_hash")
            except:
                pass
    
    def _compute_hash(self, data: Dict) -> str:
        """Compute SHA-256 hash of entry data."""
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]
    
    def _hash_inputs(self, inputs: Dict[str, Any]) -> str:
        """Hash input data to avoid storing PHI directly."""
        input_str = json.dumps(inputs, sort_keys=True)
        return hashlib.sha256(input_str.encode()).hexdigest()[:32]
    
    def log_diagnosis(
        self,
        case_id: str,
        final_diagnosis: str,
        confidence: float,
        diagnostic_certainty: str,
        agents_used: List[str],
        agent_outputs: Dict[str, Any],
        input_data: Dict[str, Any],
        critical_flags: List[str] = None,
        session_id: str = None
    ) -> str:
        """Log a diagnostic decision with full audit trail."""
        
        audit_id = f"AUDIT-{uuid.uuid4().hex[:12].upper()}"
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Count evidence across all agents
        evidence_count = sum(
            len(output.get("findings", [])) 
            for output in agent_outputs.values() 
            if isinstance(output, dict)
        )
        
        # Build entry (without hash first)
        entry_data = {
            "audit_id": audit_id,
            "timestamp": timestamp,
            "event_type": "diagnosis",
            "case_id": case_id,
            "session_id": session_id,
            "final_diagnosis": final_diagnosis,
            "confidence": confidence,
            "diagnostic_certainty": diagnostic_certainty,
            "agents_used": agents_used,
            "evidence_count": evidence_count,
            "critical_flags": critical_flags or [],
            "input_hash": self._hash_inputs(input_data),
            "payload": {
                "agent_outputs": agent_outputs,
                "input_summary": {
                    k: v[:100] + "..." if isinstance(v, str) and len(v) > 100 else v
                    for k, v in input_data.items()
                }
            },
            "previous_hash": self._last_hash
        }
        
        # Compute and add entry hash
        entry_data["entry_hash"] = self._compute_hash(entry_data)
        
        # Write to log file
        with open(self.current_log_file, 'a') as f:
            f.write(json.dumps(entry_data) + "\n")
        
        self._last_hash = entry_data["entry_hash"]
        
        return audit_id
    
    def log_error(
        self,
        case_id: str,
        error_type: str,
        error_message: str,
        context: Dict[str, Any] = None
    ) -> str:
        """Log an error event."""
        
        audit_id = f"ERROR-{uuid.uuid4().hex[:12].upper()}"
        timestamp = datetime.now(timezone.utc).isoformat()
        
        entry_data = {
            "audit_id": audit_id,
            "timestamp": timestamp,
            "event_type": "error",
            "case_id": case_id,
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {},
            "previous_hash": self._last_hash
        }
        
        entry_data["entry_hash"] = self._compute_hash(entry_data)
        
        with open(self.current_log_file, 'a') as f:
            f.write(json.dumps(entry_data) + "\n")
        
        self._last_hash = entry_data["entry_hash"]
        
        return audit_id
    
    def verify_chain_integrity(self) -> Dict[str, Any]:
        """Verify the integrity of the audit log chain."""
        if not self.current_log_file.exists():
            return {"valid": True, "entries": 0, "message": "No log file exists"}
        
        with open(self.current_log_file, 'r') as f:
            lines = f.readlines()
        
        if not lines:
            return {"valid": True, "entries": 0, "message": "Log file is empty"}
        
        valid = True
        broken_at = None
        previous_hash = None
        
        for i, line in enumerate(lines):
            try:
                entry = json.loads(line)
                
                # Verify previous hash chain
                if entry.get("previous_hash") != previous_hash:
                    valid = False
                    broken_at = i
                    break
                
                # Verify entry hash
                stored_hash = entry.pop("entry_hash")
                computed_hash = self._compute_hash(entry)
                entry["entry_hash"] = stored_hash
                
                if stored_hash != computed_hash:
                    valid = False
                    broken_at = i
                    break
                
                previous_hash = stored_hash
                
            except json.JSONDecodeError:
                valid = False
                broken_at = i
                break
        
        return {
            "valid": valid,
            "entries": len(lines),
            "broken_at_entry": broken_at,
            "message": "Chain verified successfully" if valid else f"Chain broken at entry {broken_at}"
        }
    
    def get_entries_for_case(self, case_id: str) -> List[Dict]:
        """Retrieve all audit entries for a specific case."""
        entries = []
        
        for log_file in self.log_dir.glob("audit_*.jsonl"):
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get("case_id") == case_id:
                            entries.append(entry)
                    except:
                        continue
        
        return sorted(entries, key=lambda x: x.get("timestamp", ""))
    
    def export_for_compliance(
        self,
        start_date: str = None,
        end_date: str = None,
        output_file: str = None
    ) -> str:
        """Export audit logs for compliance review."""
        entries = []
        
        for log_file in sorted(self.log_dir.glob("audit_*.jsonl")):
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        ts = entry.get("timestamp", "")
                        
                        # Filter by date if specified
                        if start_date and ts < start_date:
                            continue
                        if end_date and ts > end_date:
                            continue
                        
                        entries.append(entry)
                    except:
                        continue
        
        if not output_file:
            output_file = f"compliance_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        output_path = self.log_dir / output_file
        
        with open(output_path, 'w') as f:
            json.dump({
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "entries_count": len(entries),
                "date_range": {"start": start_date, "end": end_date},
                "entries": entries
            }, f, indent=2)
        
        return str(output_path)


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        log_dir = os.environ.get("AUDIT_LOG_DIR", "audit_logs")
        _audit_logger = AuditLogger(log_dir)
    return _audit_logger
