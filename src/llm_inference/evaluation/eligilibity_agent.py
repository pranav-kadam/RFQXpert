import logging
import json
import re
import os
import sys

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.append(project_root)

from src.utils.gemini import gemini_client

logger = logging.getLogger(__name__)

# Load company data
company_data_path = os.path.join(project_root, 'data', 'companydata.json')
with open(company_data_path, 'r', encoding='utf-8') as f:
    service_company_data = json.load(f)

# If you want to embed it as raw JSON string
service_company_data_str = json.dumps(service_company_data, indent=2)

# Load RFP data
rfp_data_path = os.path.join(project_root, 'data', 'processed', 'rfq.json')
with open(rfp_data_path, 'r', encoding='utf-8') as f:
    client_rfp_text = json.load(f)

# If you want to embed it as raw JSON string
client_rfp_text_str = json.dumps(client_rfp_text, indent=2)

ELIGIBILITY_PROMPT = """
RFQXpert provides services to U.S. government agencies. To secure contracts, we must respond to Requests for Proposals (RFPs)—detailed documents outlining project requirements, legal terms, and submission guidelines. Crafting a winning proposal is complex and time-sensitive, requiring extensive legal and compliance checks. These are the details of RFQXpert data:
{company_data}

Analyze this RFP and company profile to determine eligibility:
RFP: {rfp_data}

Tasks:
1. List all MANDATORY requirements from RFP
2. Check which requirements are met by the company
3. If there is any ambiguity, apply critical thinking to judge whether company can meet the requirement.
4. Provide clear yes/no eligibility conclusion

Return JSON format:
{{
  "meets_criteria": boolean,
  "met_requirements": [strings],
  "unmet_requirements": [strings],
  "reasons": [strings],
  "recommendations": [strings]
}}"""

async def evaluate_eligibility(rfp_text: str) -> dict:
    try:
        # Format the prompt properly
        prompt = ELIGIBILITY_PROMPT.format(
            company_data=service_company_data_str,
            rfp_data=rfp_text  # Use the passed rfp_text
        )
        
        try:
            response = await gemini_client.generate_content(prompt)
        except Exception as api_error:
            logger.error(f"Gemini API error: {str(api_error)}")
            return create_fallback_response(f"API error: {str(api_error)}")
        
        eligibility_data = parse_gemini_response(response)

        # Save the output to a JSON file
        output_path = os.path.join(project_root, 'data', 'eligibility_output.json')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(eligibility_data, f, indent=2)

        return eligibility_data

    except Exception as e:
        logger.error(f"Gemini eligibility error: {str(e)}")
        return create_fallback_response(f"Evaluation error: {str(e)}")


def parse_gemini_response(response) -> dict:
    """
    Parse the JSON response from Gemini API.
    
    Args:
        response: Response object from Gemini API
        
    Returns:
        dict: Parsed eligibility assessment data
    """
    try:
        # Extract text content from the response
        text_content = response.text
        
        # Try to find JSON in the response using a more precise regex
        # Look for JSON object that matches the expected structure
        json_pattern = r'(\{\s*"meets_criteria":.+?\}\s*})'
        json_matches = re.search(json_pattern, text_content, re.DOTALL)
        
        if json_matches:
            json_str = json_matches.group(1)
            # Parse the JSON string
            eligibility_data = json.loads(json_str)
            
            # Validate the structure
            validate_eligibility_data(eligibility_data)
            
            return eligibility_data
        else:
            # Try a more general approach as fallback
            json_pattern = r'(\{[\s\S]*?\})'
            potential_jsons = re.findall(json_pattern, text_content)
            
            for potential_json in potential_jsons:
                try:
                    data = json.loads(potential_json)
                    if "meets_criteria" in data:
                        validate_eligibility_data(data)
                        return data
                except (json.JSONDecodeError, ValueError):
                    continue
            
            logger.warning("No valid JSON found in Gemini response")
            return create_fallback_response("No valid JSON found in model response")
            
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from Gemini response: {str(e)}")
        return create_fallback_response(f"JSON parsing error: {str(e)}")
        
    except ValueError as e:
        logger.error(f"Invalid eligibility data structure: {str(e)}")
        return create_fallback_response(f"Data validation error: {str(e)}")
        
    except Exception as e:
        logger.error(f"Unexpected error parsing Gemini response: {str(e)}")
        return create_fallback_response(f"Unexpected error: {str(e)}")


def validate_eligibility_data(data: dict) -> None:
    """
    Validate that the eligibility data contains all required fields.
    
    Args:
        data: Parsed JSON data
        
    Raises:
        ValueError: If data is missing required fields
    """
    required_keys = ["meets_criteria", "met_requirements", "unmet_requirements", 
                     "reasons", "recommendations"]
    
    for key in required_keys:
        if key not in data:
            raise ValueError(f"Missing required field: {key}")
    
    # Validate data types
    if not isinstance(data["meets_criteria"], bool):
        raise ValueError("'meets_criteria' must be a boolean")
        
    for list_field in ["met_requirements", "unmet_requirements", "reasons", "recommendations"]:
        if not isinstance(data[list_field], list):
            raise ValueError(f"'{list_field}' must be a list")
            
        # Validate that all items in lists are strings
        if not all(isinstance(item, str) for item in data[list_field]):
            raise ValueError(f"All items in '{list_field}' must be strings")


def create_fallback_response(error_message: str) -> dict:
    """
    Create a fallback response when parsing fails.
    
    Args:
        error_message: Description of the error
        
    Returns:
        dict: Structured fallback response
    """
    return {
        "meets_criteria": False,
        "met_requirements": [],
        "unmet_requirements": ["Unable to determine requirements"],
        "reasons": [f"Response analysis failed: {error_message}"],
        "recommendations": [
            "Try again with more structured RFP information",
            "Review RFP manually to verify requirements",
            "Contact support if the issue persists"
        ]
    }