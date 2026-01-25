"""
MADN-X API Integration Tests
=============================
End-to-end tests for all API endpoints.

Run with: pytest tests/test_api.py -v
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.main import app

client = TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH & STATUS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealthEndpoints:
    """Tests for system health and status endpoints."""
    
    def test_root_endpoint(self):
        """Root endpoint should return service info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert "MADN-X" in data["service"]
    
    def test_health_endpoint(self):
        """Health endpoint should return detailed status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "agents" in data
        assert "audit_chain_valid" in data


# ═══════════════════════════════════════════════════════════════════════════════
# DIAGNOSIS ENDPOINT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDiagnoseEndpoint:
    """Tests for the main /diagnose endpoint."""
    
    def test_pe_case_basic(self):
        """Test basic PE case diagnosis."""
        response = client.post("/diagnose", json={
            "radiology": "CT angiography shows filling defect in pulmonary artery",
            "ecg": "Sinus tachycardia, S1Q3T3 pattern",
            "symptoms_text": "Sudden dyspnea, chest pain",
            "lab_text": "D-dimer elevated 2500"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "case_id" in data
        assert "agents_considered" in data
        assert "agent_outputs" in data
        assert "consensus" in data
        assert "latency_ms" in data
        
        # Check PE is detected
        assert data["consensus"]["diagnoses"].get("Pulmonary Embolism", 0) >= 0.9
        assert "confirmed" in data["consensus"].get("diagnostic_certainty", "").lower()
    
    def test_pe_case_with_explainability(self):
        """Test PE case with explainability enabled."""
        response = client.post("/diagnose", json={
            "radiology": "CTPA positive for pulmonary embolism",
            "ecg": "Sinus tachycardia",
            "symptoms_text": "Dyspnea",
            "lab_text": "D-dimer 3000",
            "explain": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Check explainability
        assert "explanation" in data
        assert "evidence_attributions" in data["explanation"]
        assert "reasoning_chain" in data["explanation"]
        assert "one_line_explanation" in data["explanation"]
    
    def test_case_with_custom_id(self):
        """Test case with custom case_id."""
        response = client.post("/diagnose", json={
            "radiology": "Normal chest X-ray",
            "case_id": "TEST-CASE-001"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["case_id"] == "TEST-CASE-001"
    
    def test_minimal_input(self):
        """Test with minimal input - should still work."""
        response = client.post("/diagnose", json={
            "symptoms_text": "Chest pain"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "consensus" in data
    
    def test_empty_input(self):
        """Test with empty input - should handle gracefully."""
        response = client.post("/diagnose", json={})
        
        # Should either work or return proper error
        assert response.status_code in [200, 422]
    
    def test_cardiac_case(self):
        """Test cardiac-focused case."""
        response = client.post("/diagnose", json={
            "radiology": "Normal chest X-ray",
            "ecg": "ST elevation in leads V1-V4 with reciprocal changes",
            "symptoms_text": "Crushing chest pain radiating to left arm, diaphoresis",
            "lab_text": "Troponin elevated 5.0, CK-MB elevated"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should detect cardiac emergency
        assert data["consensus"]["confidence"] > 0.5
    
    def test_pneumonia_case(self):
        """Test pneumonia case."""
        response = client.post("/diagnose", json={
            "radiology": "Right lower lobe consolidation with air bronchograms",
            "symptoms_text": "Productive cough, fever 102F, chills",
            "lab_text": "WBC 15,000 with left shift"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should detect something
        assert data["consensus"]["confidence"] > 0.3


# ═══════════════════════════════════════════════════════════════════════════════
# METRICS ENDPOINT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMetricsEndpoints:
    """Tests for metrics tracking endpoints."""
    
    def test_get_metrics(self):
        """Test getting current metrics."""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        
        assert "total_cases" in data
        assert "average_latency_ms" in data
        assert "agent_metrics" in data
    
    def test_export_metrics(self):
        """Test exporting metrics."""
        response = client.get("/metrics/export")
        assert response.status_code == 200
        data = response.json()
        
        assert "exported_at" in data
        assert "summary" in data
    
    def test_ground_truth_feedback(self):
        """Test submitting ground truth feedback."""
        # First, create a case
        case_response = client.post("/diagnose", json={
            "radiology": "Normal chest X-ray",
            "symptoms_text": "Mild cough"
        })
        case_id = case_response.json()["case_id"]
        
        # Submit ground truth
        response = client.post("/metrics/ground-truth", json={
            "case_id": case_id,
            "actual_diagnosis": "Viral Upper Respiratory Infection"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "recorded"


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT ENDPOINT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditEndpoints:
    """Tests for audit logging endpoints."""
    
    def test_verify_audit_chain(self):
        """Test audit chain verification."""
        response = client.get("/audit/verify")
        assert response.status_code == 200
        data = response.json()
        
        assert "is_valid" in data
        assert "total_entries" in data
    
    def test_get_case_audit(self):
        """Test getting audit entries for a specific case."""
        # First, create a case
        case_response = client.post("/diagnose", json={
            "radiology": "Normal chest X-ray",
            "symptoms_text": "Mild cough"
        })
        case_id = case_response.json()["case_id"]
        
        # Get audit entries
        response = client.get(f"/audit/case/{case_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert "case_id" in data
        assert "entries" in data


# ═══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPerformance:
    """Performance and stress tests."""
    
    def test_latency_reasonable(self):
        """Test that latency is within reasonable bounds."""
        response = client.post("/diagnose", json={
            "radiology": "Normal chest X-ray",
            "symptoms_text": "Mild cough"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Latency should be under 30 seconds (accounting for GPT API)
        assert data["latency_ms"] < 30000
    
    def test_multiple_sequential_requests(self):
        """Test multiple sequential requests work correctly."""
        for i in range(3):
            response = client.post("/diagnose", json={
                "symptoms_text": f"Test case {i}"
            })
            assert response.status_code == 200
    
    def test_response_structure_consistent(self):
        """Test response structure is consistent across calls."""
        response1 = client.post("/diagnose", json={"symptoms_text": "Chest pain"})
        response2 = client.post("/diagnose", json={"symptoms_text": "Dyspnea"})
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Same keys should be present
        assert set(data1.keys()) == set(data2.keys())


# ═══════════════════════════════════════════════════════════════════════════════
# OPENAPI TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestOpenAPI:
    """Tests for OpenAPI/Swagger documentation."""
    
    def test_docs_available(self):
        """Test Swagger docs are available."""
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_redoc_available(self):
        """Test ReDoc is available."""
        response = client.get("/redoc")
        assert response.status_code == 200
    
    def test_openapi_schema(self):
        """Test OpenAPI schema is valid."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data
        assert data["info"]["title"] == "MADN-X Multi-Agent Diagnostic API"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
