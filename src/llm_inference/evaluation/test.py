import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from eligilibity_agent import evaluate_eligibility
import sys
import os

# Add the project root to PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from evaluation.eligilibity_agent import evaluate_eligibility

# Sample RFP input to simulate evaluation
mock_rfp_text = """
The vendor must have GSA Schedule certification, provide services within the continental US,
maintain cybersecurity compliance with NIST 800-53, and have at least 3 years of experience working with federal agencies.
"""

# Expected mock response from the Gemini API (as it would return)
mock_gemini_response = type('MockResponse', (), {
    "text": """
    {
      "meets_criteria": true,
      "met_requirements": [
        "GSA Schedule certification",
        "Provides services within the continental US",
        "Cybersecurity compliance with NIST 800-53",
        "3+ years experience with federal agencies"
      ],
      "unmet_requirements": [],
      "reasons": [
        "All mandatory criteria have been met based on the provided company profile"
      ],
      "recommendations": [
        "Proceed with proposal submission"
      ]
    }
    """
})()

@pytest.mark.asyncio
async def test_evaluate_eligibility_success():
    with patch("eligibility_evaluator.gemini_client.generate_content", new=AsyncMock(return_value=mock_gemini_response)):
        result = await evaluate_eligibility(mock_rfp_text)
        
        assert isinstance(result, dict)
        assert result["meets_criteria"] is True
        assert "Cybersecurity compliance with NIST 800-53" in result["met_requirements"]
        assert len(result["unmet_requirements"]) == 0
        assert "Proceed with proposal submission" in result["recommendations"]

if __name__ == "__main__":
    asyncio.run(test_evaluate_eligibility_success())
