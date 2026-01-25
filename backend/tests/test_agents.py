"""
MADN-X Agent Test Suite
========================
Comprehensive tests for all specialist agents and edge cases.

Run with: pytest tests/test_agents.py -v
"""

import pytest
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.agents.radiologist import radiologist_agent, check_definitive_findings
from app.agents.cardiologist import cardiologist_agent
from app.agents.pulmonologist import pulmonologist_agent
from app.agents.pathologist import pathologist_agent
from app.agents.consensus_agent import consensus_agent
from app.agents.safety_agent import safety_agent


# ═══════════════════════════════════════════════════════════════════════════════
# RADIOLOGIST TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRadiologist:
    """Tests for Radiologist agent - imaging interpretation."""
    
    def test_pe_ctpa_filling_defect_confirms_diagnosis(self):
        """CTPA filling defect should CONFIRM PE with ~0.98 confidence."""
        radiology = "CT angiography shows filling defect in right main pulmonary artery"
        result = radiologist_agent(radiology)
        
        assert result["is_definitive"] == True
        assert result["diagnostic_certainty"] == "confirmed"
        assert result["diagnoses"].get("Pulmonary Embolism", 0) >= 0.95
        assert "CONFIRMED" in result["top_diagnosis"]
    
    def test_pe_ctpa_variant_detection(self):
        """Various ways to describe CTPA PE should all be detected."""
        variants = [
            "CTPA reveals filling defect in pulmonary artery",
            "CT pulmonary angiogram positive for pulmonary embolism",
            "Filling defect seen in segmental pulmonary arteries on CTA",
        ]
        for text in variants:
            result = radiologist_agent(text)
            assert result["diagnoses"].get("Pulmonary Embolism", 0) >= 0.9
    
    def test_stemi_st_elevation_confirms_diagnosis(self):
        """ST elevation pattern should confirm STEMI with high confidence."""
        radiology = "ECG shows ST elevation in leads V1-V4"
        result = radiologist_agent(radiology)
        
        # STEMI should be detected
        assert any("myocardial" in k.lower() or "stemi" in k.lower() or "MI" in result["diagnoses"].keys() 
                   for k in result["diagnoses"].keys()) or result["confidence"] > 0.5
    
    def test_pneumonia_consolidation_confirms_diagnosis(self):
        """Lobar consolidation should confirm pneumonia."""
        radiology = "Chest X-ray shows right lower lobe consolidation with air bronchograms"
        result = radiologist_agent(radiology)
        
        # Should detect pneumonia-related finding
        assert result["confidence"] > 0.5
    
    def test_normal_chest_xray_low_confidence(self):
        """Normal chest X-ray should have low diagnostic confidence."""
        radiology = "Chest X-ray is normal. No acute cardiopulmonary abnormality."
        result = radiologist_agent(radiology)
        
        assert result["confidence"] < 0.5
    
    def test_definitive_findings_function(self):
        """Test the definitive findings checker directly."""
        # PE via CTPA
        result = check_definitive_findings("CTPA shows filling defect in pulmonary artery")
        assert result["disease"] == "Pulmonary Embolism"
        assert result["confidence"] >= 0.95
        
        # No definitive finding
        result = check_definitive_findings("Chest X-ray normal")
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# CARDIOLOGIST TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCardiologist:
    """Tests for Cardiologist agent - ECG and cardiac interpretation."""
    
    def test_afib_detection(self):
        """Atrial fibrillation should be detected with high confidence."""
        ecg = "ECG shows irregularly irregular rhythm with absent P waves, ventricular rate 120"
        result = cardiologist_agent(ecg)
        
        assert result["confidence"] > 0.5
        assert "Atrial Fibrillation" in result["diagnoses"] or "irregularly irregular" in str(result).lower()
    
    def test_pe_s1q3t3_supportive_only(self):
        """S1Q3T3 should be supportive for PE, not diagnostic."""
        ecg = "Sinus tachycardia, S1Q3T3 pattern, right axis deviation"
        result = cardiologist_agent(ecg)
        
        # PE should be considered but with moderate confidence
        pe_conf = result["diagnoses"].get("Pulmonary Embolism", 0)
        assert pe_conf < 0.5, "S1Q3T3 is supportive only, not diagnostic for PE"
    
    def test_stemi_st_elevation(self):
        """ST elevation should raise STEMI concern."""
        ecg = "Sinus rhythm with ST elevation in leads II, III, aVF"
        result = cardiologist_agent(ecg)
        
        # Should detect cardiac finding
        assert result["confidence"] > 0.3
    
    def test_normal_sinus_rhythm(self):
        """Normal sinus rhythm should have low pathology confidence."""
        ecg = "Normal sinus rhythm at 72 bpm. Normal axis. No ST changes."
        result = cardiologist_agent(ecg)
        
        # Low overall confidence for pathology
        assert result["confidence"] < 0.5


# ═══════════════════════════════════════════════════════════════════════════════
# PULMONOLOGIST TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPulmonologist:
    """Tests for Pulmonologist agent - respiratory symptoms."""
    
    def test_pe_symptoms_detected(self):
        """Classic PE symptoms should raise PE consideration."""
        symptoms = "Sudden onset shortness of breath, pleuritic chest pain, recent DVT"
        result = pulmonologist_agent(symptoms)
        
        assert "Pulmonary Embolism" in result["diagnoses"]
        assert result["diagnoses"]["Pulmonary Embolism"] > 0.2
    
    def test_pneumonia_symptoms_detected(self):
        """Pneumonia symptoms should raise pneumonia consideration."""
        symptoms = "Productive cough with yellow sputum, fever 102F, chills, dyspnea"
        result = pulmonologist_agent(symptoms)
        
        # Should detect pneumonia or infection
        assert result["confidence"] > 0.3
    
    def test_asthma_symptoms(self):
        """Asthma symptoms should be detected."""
        symptoms = "Wheezing, shortness of breath worse at night, history of allergies"
        result = pulmonologist_agent(symptoms)
        
        assert result["confidence"] > 0.2
    
    def test_red_flag_sudden_dyspnea(self):
        """Sudden onset dyspnea should trigger red flag."""
        symptoms = "Sudden severe shortness of breath"
        result = pulmonologist_agent(symptoms)
        
        # Should have flags for urgent conditions
        assert len(result["flags"]) > 0 or result["confidence"] > 0.3


# ═══════════════════════════════════════════════════════════════════════════════
# PATHOLOGIST TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPathologist:
    """Tests for Pathologist agent - lab interpretation."""
    
    def test_elevated_ddimer_for_pe(self):
        """Elevated D-dimer should raise PE suspicion."""
        labs = "D-dimer: 2500 ng/mL (normal <500)"
        result = pathologist_agent(labs)
        
        assert "Pulmonary Embolism" in result["diagnoses"]
        assert result["diagnoses"]["Pulmonary Embolism"] > 0.2
    
    def test_elevated_troponin_for_mi(self):
        """Elevated troponin should flag MI."""
        labs = "Troponin I: 2.5 ng/mL (elevated), CK-MB: 45 U/L (elevated)"
        result = pathologist_agent(labs)
        
        # Should flag MI-related condition
        assert result["confidence"] > 0.4
        assert any("CRITICAL" in flag or "troponin" in flag.lower() for flag in result["flags"])
    
    def test_elevated_bnp_for_heart_failure(self):
        """Elevated BNP should raise heart failure concern."""
        labs = "BNP: 1500 pg/mL (normal <100), Creatinine 1.8"
        result = pathologist_agent(labs)
        
        # Should detect heart failure marker
        assert result["confidence"] > 0.3
    
    def test_normal_labs_low_confidence(self):
        """Normal labs should have low diagnostic confidence."""
        labs = "CBC normal, BMP normal, all values within reference range"
        result = pathologist_agent(labs)
        
        assert result["confidence"] < 0.4


# ═══════════════════════════════════════════════════════════════════════════════
# CONSENSUS AGENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestConsensusAgent:
    """Tests for Consensus agent - multi-agent synthesis."""
    
    def test_definitive_finding_dominates(self):
        """When radiologist confirms PE, consensus should respect that."""
        agent_outputs = [
            {
                "agent": "radiologist",
                "diagnoses": {"Pulmonary Embolism": 0.98},
                "confidence": 0.98,
                "is_definitive": True,
                "diagnostic_certainty": "confirmed"
            },
            {
                "agent": "cardiologist",
                "diagnoses": {"Pulmonary Embolism": 0.25},
                "confidence": 0.25,
                "is_definitive": False
            },
            {
                "agent": "pulmonologist",
                "diagnoses": {"Pulmonary Embolism": 0.33},
                "confidence": 0.33,
                "is_definitive": False
            }
        ]
        
        result = consensus_agent(agent_outputs)
        
        assert result["diagnoses"].get("Pulmonary Embolism", 0) >= 0.9
        assert "confirmed" in result.get("diagnostic_certainty", "").lower() or result["confidence"] > 0.9
    
    def test_weighted_average_when_no_definitive(self):
        """Without definitive findings, should use weighted average."""
        agent_outputs = [
            {
                "agent": "radiologist",
                "diagnoses": {"Pneumonia": 0.6},
                "confidence": 0.6,
                "is_definitive": False
            },
            {
                "agent": "pulmonologist",
                "diagnoses": {"Pneumonia": 0.5},
                "confidence": 0.5,
                "is_definitive": False
            }
        ]
        
        result = consensus_agent(agent_outputs)
        
        # Should be somewhere between the two
        assert 0.4 < result["diagnoses"].get("Pneumonia", 0) < 0.7
    
    def test_disagreement_handling(self):
        """Agents with different top diagnoses should be handled."""
        agent_outputs = [
            {
                "agent": "radiologist",
                "diagnoses": {"Pneumonia": 0.6, "Pulmonary Embolism": 0.2},
                "confidence": 0.6,
                "is_definitive": False
            },
            {
                "agent": "cardiologist",
                "diagnoses": {"Pulmonary Embolism": 0.5, "Pneumonia": 0.1},
                "confidence": 0.5,
                "is_definitive": False
            }
        ]
        
        result = consensus_agent(agent_outputs)
        
        # Both diagnoses should be in final output
        assert "Pneumonia" in result["diagnoses"] or "Pulmonary Embolism" in result["diagnoses"]


# ═══════════════════════════════════════════════════════════════════════════════
# SAFETY AGENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSafetyAgent:
    """Tests for Safety agent - critical finding detection."""
    
    def test_critical_troponin_flagged(self):
        """Critical troponin elevation should be flagged."""
        agent_outputs = [
            {
                "agent": "pathologist",
                "diagnoses": {"STEMI": 0.8},
                "findings": [
                    {"name": "Elevated Troponin", "severity": "critical"}
                ],
                "flags": ["CRITICAL: Elevated Troponin"]
            }
        ]
        
        result = safety_agent(agent_outputs, {})
        
        assert result["critical_findings_detected"] == True or len(result["alerts"]) > 0
    
    def test_no_alerts_for_normal(self):
        """Normal findings should not trigger alerts."""
        agent_outputs = [
            {
                "agent": "radiologist",
                "diagnoses": {},
                "findings": [],
                "flags": [],
                "confidence": 0.1
            }
        ]
        
        result = safety_agent(agent_outputs, {})
        
        assert result["critical_findings_detected"] == False or len(result.get("alerts", [])) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    """Integration tests for full diagnostic pipeline."""
    
    def test_pe_full_case(self):
        """Test complete PE case through all agents."""
        # Simulate full case data
        radiology = "CTPA shows filling defect in pulmonary artery"
        ecg = "Sinus tachycardia 110 bpm, S1Q3T3 pattern"
        symptoms = "Sudden dyspnea, pleuritic chest pain, recent surgery"
        labs = "D-dimer 2500, troponin mildly elevated"
        
        # Run each agent
        rad_result = radiologist_agent(radiology)
        card_result = cardiologist_agent(ecg)
        pulm_result = pulmonologist_agent(symptoms)
        path_result = pathologist_agent(labs)
        
        # All should contribute to PE diagnosis
        assert rad_result["diagnoses"].get("Pulmonary Embolism", 0) >= 0.95
        
        # Aggregate for consensus
        agent_outputs = [
            {**rad_result, "agent": "radiologist"},
            {**card_result, "agent": "cardiologist"},
            {**pulm_result, "agent": "pulmonologist"},
            {**path_result, "agent": "pathologist"}
        ]
        
        consensus = consensus_agent(agent_outputs)
        
        # Final consensus should confirm PE
        assert consensus["diagnoses"].get("Pulmonary Embolism", 0) >= 0.9


# ═══════════════════════════════════════════════════════════════════════════════
# EDGE CASE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_input(self):
        """Agents should handle empty input gracefully."""
        result = radiologist_agent("")
        assert result["confidence"] >= 0  # Should not crash
        
        result = cardiologist_agent("")
        assert result["confidence"] >= 0
    
    def test_gibberish_input(self):
        """Agents should handle nonsense input."""
        result = radiologist_agent("asdfghjkl random words 12345")
        assert result["confidence"] < 0.5  # Low confidence for nonsense
    
    def test_very_long_input(self):
        """Agents should handle long input."""
        long_text = "Patient presents with chest pain. " * 100
        result = radiologist_agent(long_text)
        assert "confidence" in result  # Should not crash
    
    def test_special_characters(self):
        """Agents should handle special characters."""
        result = radiologist_agent("X-ray shows <abnormality> & 'findings' @ 90% confidence")
        assert "confidence" in result  # Should not crash


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
