import logging
import json
import os
from llm_inference.utils.gemini import gemini_client

logger = logging.getLogger(__name__)

# Correct the path to companydata.json based on your project structure
# According to the folder structure, it should be in src/llm_inference/data
with open('src/llm_inference/data/companydata.json', 'r') as f:
    service_company_data = json.load(f)

# If you want to embed it as raw JSON string
service_company_data_str = json.dumps(service_company_data, indent=2)

with open('RFQXpert/data/processed/rfq.json', 'r') as f:
    client_rfp_text = json.load(f)

# If you want to embed it as raw JSON string
client_rfp_text_str = json.dumps(client_rfp_text, indent=2)

COMPLIANCE_PROMPT = """
RFQXpert provides services to U.S. government agencies. To secure contracts, we must respond to Requests for Proposals (RFPs)—detailed documents outlining project requirements, legal terms, and submission guidelines. Crafting a winning proposal is complex and time-sensitive, requiring extensive legal and compliance checks. These are the details of RFQXpert data:{service_company_data_str}

Analyze this RFP for compliance risks: {client_rfp_text_str}

Identify risks in these categories:
- Legal/Contractual
- Financial
- Operational
- Technical

For each risk:
- Categorize
- Severity (1-5)
- Likelihood (1-5)
- Explanation
- Mitigation strategy

Return JSON format:
{{
  "risk_assessment": {{
    "overall_risk_score": float,
    "high_risk_items": [
      {{
        "category": string,
        "severity": int,
        "likelihood": int,
        "description": string,
        "mitigation": string
      }}
    ],
    "medium_risk_items": [...],
    "low_risk_items": [...]
  }}
}}
"""

def parse_compliance_response(response):
    """
    Parse the response from Gemini API and extract the risk assessment JSON.
    
    Args:
        response: The response object from Gemini API
        
    Returns:
        dict: Parsed risk assessment data
    """
    try:
        # Extract text from the response
        text_content = response.text
        
        # Find and extract JSON content
        json_content = extract_json_from_text(text_content)
        
        # Parse the JSON
        risk_data = json.loads(json_content)
        
        # Validate the structure of the risk assessment
        validate_risk_assessment(risk_data)
        
        return risk_data
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from Gemini response: {str(e)}")
        raise ValueError("Invalid JSON format in response")
    
    except KeyError as e:
        logger.error(f"Missing required key in risk assessment: {str(e)}")
        raise ValueError(f"Incomplete risk assessment data: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error parsing compliance response: {str(e)}")
        raise

def extract_json_from_text(text):
    """
    Extract JSON content from text that might contain markdown or other formatting
    
    Args:
        text: String containing JSON somewhere in the content
        
    Returns:
        str: Extracted JSON string
    """
    # Look for JSON content between curly braces
    start_index = text.find('{')
    if start_index == -1:
        raise ValueError("No JSON found in response")
    
    # Track nested braces to find the end of the JSON object
    brace_count = 0
    for i in range(start_index, len(text)):
        if text[i] == '{':
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                # Found the matching closing brace
                return text[start_index:i+1]
    
    raise ValueError("Incomplete JSON in response")

def validate_risk_assessment(data):
    """
    Validate that the risk assessment data has the required structure
    
    Args:
        data: Parsed JSON data
        
    Raises:
        ValueError: If data is missing required fields
    """
    if "risk_assessment" not in data:
        raise ValueError("Missing 'risk_assessment' key in response")
    
    assessment = data["risk_assessment"]
    
    required_keys = ["overall_risk_score", "high_risk_items", "medium_risk_items", "low_risk_items"]
    for key in required_keys:
        if key not in assessment:
            raise ValueError(f"Missing '{key}' in risk assessment")
    
    # Validate risk item format in each risk category
    for category in ["high_risk_items", "medium_risk_items", "low_risk_items"]:
        if not isinstance(assessment[category], list):
            raise ValueError(f"'{category}' must be a list")
        
        # Validate each risk item
        for item in assessment[category]:
            validate_risk_item(item)

def validate_risk_item(item):
    """
    Validate individual risk item structure
    
    Args:
        item: Risk item dictionary
        
    Raises:
        ValueError: If item is missing required fields
    """
    required_fields = ["category", "severity", "likelihood", "description", "mitigation"]
    for field in required_fields:
        if field not in item:
            raise ValueError(f"Risk item missing required field: {field}")
    
    # Validate severity and likelihood are integers between 1-5
    if not isinstance(item["severity"], int) or not 1 <= item["severity"] <= 5:
        raise ValueError("Severity must be an integer between 1-5")
    
    if not isinstance(item["likelihood"], int) or not 1 <= item["likelihood"] <= 5:
        raise ValueError("Likelihood must be an integer between 1-5")

async def analyze_risks(rfp_text: str) -> dict:
    try:
        prompt = COMPLIANCE_PROMPT.format(
            rfp_text=rfp_text,
        )
        
        response = await gemini_client.generate_content(prompt)
        return parse_compliance_response(response)
        
    except Exception as e:
        logger.error(f"Gemini compliance error: {str(e)}")
        raise