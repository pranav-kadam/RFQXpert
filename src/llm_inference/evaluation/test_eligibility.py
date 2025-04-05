import pytest
import json
from unittest.mock import Mock # Or use pytest-mock fixture 'mocker'

# Import functions from your script (adjust path as needed)
# Assuming your script is at ../src/processing/eligibility.py
import sys
import os
# Add project root to allow importing 'src'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, project_root)

from src.llm_inference.evaluation.eligilibity_agent import (
    parse_gemini_response,
    validate_eligibility_data,
    create_fallback_response
)

# --- Test parse_gemini_response ---

def create_mock_response(text_content):
    """Helper to create a mock Gemini response object."""
    mock_part = Mock()
    mock_part.text = text_content
    mock_response = Mock()
    # Simulate the structure expected by the parser
    mock_response.parts = [mock_part]
    # Add .text attribute as a potential fallback access pattern
    mock_response.text = text_content
    return mock_response

def test_parse_gemini_response_success_plain():
    json_payload = {
        "meets_criteria": True,
        "met_requirements": ["req1"],
        "unmet_requirements": [],
        "reasons": ["All good"],
        "recommendations": ["Proceed"]
    }
    raw_text = f"Here is the analysis:\n{json.dumps(json_payload, indent=2)}\nEnd of analysis."
    mock_response = create_mock_response(raw_text)
    result = parse_gemini_response(mock_response)
    assert result == json_payload

def test_parse_gemini_response_success_markdown():
    json_payload = {
        "meets_criteria": False,
        "met_requirements": [],
        "unmet_requirements": ["req2"],
        "reasons": ["Missing req2"],
        "recommendations": ["Do not proceed"]
    }
    raw_text = f"```json\n{json.dumps(json_payload)}\n```"
    mock_response = create_mock_response(raw_text)
    result = parse_gemini_response(mock_response)
    assert result == json_payload

def test_parse_gemini_response_invalid_json():
    raw_text = "Here is the data: { \"meets_criteria\": true, oops forgot quote }"
    mock_response = create_mock_response(raw_text)
    result = parse_gemini_response(mock_response)
    assert result["meets_criteria"] is False
    assert "JSON parsing error" in result["reasons"][0]

def test_parse_gemini_response_no_json():
    raw_text = "The company looks eligible based on my analysis."
    mock_response = create_mock_response(raw_text)
    result = parse_gemini_response(mock_response)
    assert result["meets_criteria"] is False
    assert "No valid JSON found" in result["reasons"][0]

# --- Test validate_eligibility_data ---

def test_validate_data_success():
    valid_data = {
        "meets_criteria": True,
        "met_requirements": ["req1"],
        "unmet_requirements": [],
        "reasons": ["All good"],
        "recommendations": ["Proceed"]
    }
    try:
        validate_eligibility_data(valid_data)
    except ValueError:
        pytest.fail("Validation failed unexpectedly for valid data")

def test_validate_data_missing_key():
    invalid_data = {
        "meets_criteria": True,
        # "met_requirements": ["req1"], # Missing key
        "unmet_requirements": [],
        "reasons": ["All good"],
        "recommendations": ["Proceed"]
    }
    with pytest.raises(ValueError, match="Missing required field"):
        validate_eligibility_data(invalid_data)

def test_validate_data_wrong_type():
    invalid_data = {
        "meets_criteria": "yes", # Should be boolean
        "met_requirements": ["req1"],
        "unmet_requirements": [],
        "reasons": "All good", # Should be list
        "recommendations": ["Proceed"]
    }
    with pytest.raises(ValueError, match="'meets_criteria' must be a boolean"):
         validate_eligibility_data(invalid_data)
    # Fix meets_criteria to test the next error
    invalid_data["meets_criteria"] = True
    with pytest.raises(ValueError, match="'reasons' must be a list"):
         validate_eligibility_data(invalid_data)

# --- Test create_fallback_response ---

def test_create_fallback():
    error_msg = "API Key Invalid"
    result = create_fallback_response(error_msg)
    assert result["meets_criteria"] is False
    assert "Unable to determine requirements" in result["unmet_requirements"][0]
    assert f"Processing failed: {error_msg}" in result["reasons"][0]
    assert isinstance(result["recommendations"], list)