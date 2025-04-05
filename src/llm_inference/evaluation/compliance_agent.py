import logging
import json
import re
import os
import sys
import asyncio
from typing import Dict, List, Optional, TypedDict

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import argparse # for command-line arguments


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Data Structures (using TypedDict for better type safety) ---

class RiskItem(TypedDict):
    category: str
    severity: int
    likelihood: int
    description: str
    mitigation: str

class RiskAssessment(TypedDict):
    overall_risk_score: float
    high_risk_items: List[RiskItem]
    medium_risk_items: List[RiskItem]
    low_risk_items: List[RiskItem]

class EligibilityData(TypedDict):
    risk_assessment: RiskAssessment

# --- Configuration ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = 'gemini-2.0-flash'
COMPANY_DATA_PATH = 'data/companydata.json'  # Relative path within project
RFP_DATA_PATH = 'data/processed/rfq.json'

if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY environment variable not set.")
    sys.exit("Error: GEMINI_API_KEY environment variable not set.")

try:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(MODEL_NAME)
    logger.info(f"Successfully initialized Gemini model: {MODEL_NAME}")
except Exception as config_error:
    logger.error(f"Failed to configure Gemini API: {config_error}")
    gemini_model = None  # Ensure model is None if initialization fails


# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.append(project_root)


# --- Data Loading ---
def load_json_data(file_path: str) -> dict:
    """Loads JSON data from a file, handling common errors."""
    try:
        full_path = os.path.join(project_root, file_path)
        with open(full_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from file: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Error loading data from file: {file_path}: {e}")
        raise

try:
    service_company_data = load_json_data(COMPANY_DATA_PATH)
    service_company_data_str = json.dumps(service_company_data, indent=2)
except Exception:
    logger.critical("Failed to load company data. Exiting.")
    sys.exit(1)

# --- RFP Data Loading (Handling Missing or Invalid Data) ---
try:
    client_rfp_text_json = load_json_data(RFP_DATA_PATH)
    client_rfp_text_str = json.dumps(client_rfp_text_json, indent=2)
except Exception:
    logger.warning("Failed to load RFP data. Using placeholder.")
    client_rfp_text_str = "{}"  # Placeholder

# --- PROMPT ---

ELIGIBILITY_PROMPT = """
RFQXpert provides services to U.S. government agencies. To secure contracts, we must respond to Requests for Proposals (RFPs)—detailed documents outlining project requirements, legal terms, and submission guidelines. Crafting a winning proposal is complex and time-sensitive, requiring extensive legal and compliance checks. These are the details of RFQXpert data:{service_company_data_str}

Analyze this RFP for compliance risks: {rfp_data}

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
}}"""

# --- Gemini API Interaction ---

async def evaluate_eligibility(rfp_text: str) -> EligibilityData:
    """
    Evaluates RFP eligibility using Gemini API, parses the response, and returns
    a dictionary containing the risk assessment data.

    Args:
        rfp_text: The RFP text to evaluate.

    Returns:
        A dictionary containing the risk assessment data.

    Raises:
        Exception: If the Gemini model is not initialized or if an error occurs
            during the API call or response parsing.
    """
    if not gemini_model:
        raise ValueError("Gemini model is not initialized.")

    prompt = ELIGIBILITY_PROMPT.format(service_company_data_str=service_company_data_str, rfp_data=rfp_text)

    try:
        response = await gemini_model.generate_content_async(prompt)
        logger.info("Successfully received response from Gemini API.")
    except google_exceptions.GoogleAPIError as api_error:  # More specific exception
        logger.error(f"Gemini API error: {api_error}")
        raise  # Re-raise for handling upstream, perhaps with retry logic

    eligibility_data = parse_gemini_response(response)

    # Save the output to a JSON file
    output_path = os.path.join(project_root, 'data', 'compliance_output.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(eligibility_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Eligibility output saved to {output_path}")
    except IOError as e:
        logger.error(f"Failed to save eligibility output to {output_path}: {e}")
    except TypeError as e:
        logger.error(f"Data serialization error when saving eligibility output: {e}")

    return eligibility_data

def parse_gemini_response(response) -> EligibilityData:
    """
    Parses the response from Gemini API to extract risk assessment data.

    Args:
        response: The response object from Gemini API.

    Returns:
        A dictionary containing the parsed risk assessment data.

    Raises:
        ValueError: If the response does not contain valid JSON or if the data
            structure is invalid.
    """
    try:
        if not response.parts:
            logger.warning("Gemini response has no parts.")
            try:
                text_content = response.text
            except AttributeError:
                raise ValueError("Gemini response has no parts and no direct text attribute.")
        else:
            text_content = response.parts[0].text

        logger.debug(f"Raw response text:\n{text_content}")

        json_pattern_precise = r'```json\s*(\{\s*"risk_assessment":.+?\}\s*})\s*```|(\{\s*"risk_assessment":.+?\}\s*})'
        json_matches = re.search(json_pattern_precise, text_content, re.DOTALL)

        json_str = None
        if json_matches:
            json_str = json_matches.group(1) if json_matches.group(1) else json_matches.group(2)
            logger.info("Found JSON block using precise pattern.")
        else:
            logger.warning("Precise JSON pattern failed. Trying general JSON block search.")
            json_pattern_general = r'```json\s*(\{[\s\S]*?\})\s*```|(\{[\s\S]*?\})'
            potential_jsons = re.findall(json_pattern_general, text_content, re.DOTALL)

            for potential_match in potential_jsons:
                potential_json_str = potential_match[0] if potential_match[0] else potential_match[1]
                try:
                    data = json.loads(potential_json_str)
                    if "risk_assessment" in data and isinstance(data["risk_assessment"], dict):
                        json_str = potential_json_str
                        logger.info("Found JSON block using general pattern fallback.")
                        break
                except (json.JSONDecodeError, TypeError):
                    logger.debug(f"Ignoring invalid JSON block: {potential_json_str[:100]}...")
                    continue

        if json_str:
            try:
                eligibility_data: EligibilityData = json.loads(json_str)  # Type hint
                validate_eligibility_data(eligibility_data)
                return eligibility_data
            except (json.JSONDecodeError, TypeError) as e:
                 logger.error(f"Failed to parse or validate JSON: {e}")
                 raise ValueError("Invalid JSON data in response") from e
        else:
            logger.error("No valid JSON found in Gemini response text.")
            logger.debug(f"Full response text where JSON was not found:\n{text_content}")
            raise ValueError("No valid JSON found in Gemini response")

    except Exception as e:
        logger.exception(f"Unexpected error parsing Gemini response: {e}")
        raise # Re-raise to signal failure

def validate_eligibility_data(data: dict) -> None:
    """
    Validates the structure and types of the parsed eligibility data.

    Args:
        data: Parsed JSON data representing eligibility information.

    Raises:
        ValueError: If the data structure is invalid or if required fields are
            missing or have incorrect types.
    """

    if not isinstance(data, dict):
        raise ValueError("Parsed data is not a dictionary.")

    required_keys = ["risk_assessment"]

    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        raise ValueError(f"Missing required field(s): {', '.join(missing_keys)}")

    risk_assessment = data["risk_assessment"]

    if not isinstance(risk_assessment, dict):
        raise ValueError("risk_assessment must be a dictionary")

    required_risk_assessment_keys = ["overall_risk_score", "high_risk_items", "medium_risk_items", "low_risk_items"]
    missing_risk_keys = [key for key in required_risk_assessment_keys if key not in risk_assessment]

    if missing_risk_keys:
        raise ValueError(f"Missing risk assessment field(s): {', '.join(missing_risk_keys)}")

# --- Main Function ---

async def main(rfp_file_path: Optional[str] = None):
    """
    Main function to run the eligibility check.
    """
    if not GEMINI_API_KEY:
        logger.error("Cannot run main function: GEMINI_API_KEY not set.")
        return

    if not gemini_model:
        logger.error("Cannot run main function: Gemini model not initialized.")
        return

    logger.info("Starting eligibility evaluation...")

    # Load RFP data, either from the default path or a user-specified path
    try:
        if rfp_file_path:
            client_rfp_text_json = load_json_data(rfp_file_path)
        else:
            client_rfp_text_json = load_json_data(RFP_DATA_PATH)

        client_rfp_text_str = json.dumps(client_rfp_text_json, indent=2)
    except Exception as e:
        logger.error(f"Failed to load RFP data: {e}")
        return  # Exit if RFP data is not available

    try:
        result = await evaluate_eligibility(client_rfp_text_str)

        logger.info("Eligibility evaluation completed.")
        print("\nEligibility Assessment Result:")
        print(json.dumps(result, indent=2))

    except Exception as e:
        logger.error(f"Eligibility evaluation failed: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate RFP eligibility using Gemini API.")
    parser.add_argument("--rfp_file", type=str, help="Path to the RFP data file (JSON).")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.rfp_file))
    except RuntimeError as e:
        if "cannot run event loop while another loop is running" in str(e):
            logger.warning("Asyncio event loop already running. Skipping main().")
        else:
            raise