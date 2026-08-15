"""
Tests für das JSON-Parsing.
"""
import pytest
import json

from src.llm.ollama_client import OllamaClient, OllamaResponseError
from src.castes.plan_models import PlanModel, ExperimentStrategy


class TestJsonParsing:
    """Tests für das JSON-Parsing."""

    def test_parse_valid_json(self):
        """Gültiges JSON wird geparst."""
        client = OllamaClient()
        
        json_text = json.dumps({
            "strategy": "exploration",
            "parameter_to_change": "fecl3_concentration_mm",
            "new_value": 0.1,
            "reasoning": "Test reasoning",
            "expected_outcome": "Test outcome",
            "confidence": "medium",
            "summary": "Test summary",
        })
        
        result = client._parse_json_response(json_text, PlanModel)
        
        assert isinstance(result, PlanModel)
        assert result.strategy.value == "exploration"
        assert result.parameter_to_change == "fecl3_concentration_mm"
        assert result.new_value == 0.1

    def test_parse_json_in_markdown_code_block(self):
        """JSON in Markdown-Codeblock wird geparst."""
        client = OllamaClient()
        
        markdown_text = "```json\n" + json.dumps({
            "strategy": "ofat",
            "parameter_to_change": "target_temperature_c",
            "new_value": 40.0,
            "reasoning": "Test",
            "expected_outcome": "Test",
            "confidence": "high",
            "summary": "Test",
        }) + "\n```"
        
        result = client._parse_json_response(markdown_text, PlanModel)
        
        assert isinstance(result, PlanModel)
        assert result.strategy.value == "ofat"

    def test_parse_markdown_format_fallback(self):
        """Markdown-Format wird in JSON umgewandelt (Fallback)."""
        client = OllamaClient()
        
        markdown_text = """**Strategy:** exploration
**Parameter to change:** fecl3_concentration_mm
**New value:** 0.1
**Reasoning:** Test reasoning
**Expected outcome:** Test outcome
**Confidence:** medium
**Summary:** Test summary
"""
        
        result = client._parse_json_response(markdown_text, PlanModel)
        
        assert isinstance(result, PlanModel)
        assert result.strategy.value == "exploration"
        assert result.parameter_to_change == "fecl3_concentration_mm"

    def test_parse_invalid_json_raises_error(self):
        """Ungültiges JSON wirft OllamaResponseError oder ValidationError."""
        client = OllamaClient()
        
        invalid_text = "This is not JSON at all"
        
        # Der Fallback-Parser gibt {} zurück, was zu einer ValidationError führt
        # Da PlanModel required fields hat, wird das Validieren fehlschlagen
        from pydantic import ValidationError
        with pytest.raises((OllamaResponseError, ValidationError)):
            client._parse_json_response(invalid_text, PlanModel)

    def test_extract_json_from_markdown_bold_keys(self):
        """Extrahiert JSON aus Markdown mit **Key:** Value Format."""
        client = OllamaClient()
        
        markdown_text = """**Strategy:** doe
**Parameter to change:** h2o2_concentration_mm
**New value:** 50.0
**Reasoning:** Based on the observed discrepancy
**Expected outcome:** Increased reaction rate
**Confidence:** high
**Summary:** Adjusting H2O2 concentration
"""
        
        json_text = client._extract_json_from_markdown(markdown_text)
        data = json.loads(json_text)
        
        assert data["strategy"] == "doe"
        assert data["parameter_to_change"] == "h2o2_concentration_mm"
        # new_value wird als Float geparst (50.0), nicht als String ("50.0")
        assert data["new_value"] == 50.0

    def test_extract_json_from_markdown_plain_keys(self):
        """Extrahiert JSON aus Markdown mit Key: Value Format."""
        client = OllamaClient()
        
        markdown_text = """Strategy: exploration
Parameter to change: target_temperature_c
New value: 45.0
Reasoning: Temperature optimization
Expected outcome: Faster kinetics
Confidence: medium
Summary: Temperature increase
"""
        
        json_text = client._extract_json_from_markdown(markdown_text)
        data = json.loads(json_text)
        
        assert data["strategy"] == "exploration"
        assert data["parameter_to_change"] == "target_temperature_c"
