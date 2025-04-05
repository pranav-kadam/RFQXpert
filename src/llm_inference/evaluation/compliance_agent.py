import logging
import json
import re
import os
import sys
import asyncio
from typing import Dict, List, Optional, TypedDict
import argparse

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from dotenv import load_dotenv
load_dotenv()


# --- Logging Configuration ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- TypedDict Definitions ---
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

# --- Configurations ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = 'gemini-2.0-flash'
COMPANY_DATA_PATH = 'data/companydata.json'
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
    gemini_model = None

# --- Project Root Resolution ---
try:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
except NameError:
    project_root = os.getcwd()
sys.path.append(project_root)

# --- Data Loading ---
def load_json_data(file_path: str) -> dict:
    try:
        full_path = os.path.join(project_root, file_path)
        with open(full_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading data from {file_path}: {e}")
        raise

try:
    service_company_data = load_json_data(COMPANY_DATA_PATH)
    service_company_data_str = json.dumps(service_company_data, indent=2)
except Exception:
    logger.critical("Failed to load company data. Exiting.")
    sys.exit(1)

# --- Gemini Prompt ---
ELIGIBILITY_PROMPT = """
RFQXpert provides services to U.S. government agencies. To secure contracts, we must respond to Requests for Proposals (RFPs)—detailed documents outlining project requirements, legal terms, and submission guidelines. Crafting a winning proposal is complex and time-sensitive, requiring extensive legal and compliance checks. These are the details of RFQXpert data:
{service_company_data_str}

Analyze this RFP for compliance risks:
{rfp_data}

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
    "high_risk_items": [...],
    "medium_risk_items": [...],
    "low_risk_items": [...]
  }}
}}
"""

# --- Evaluate Eligibility ---
async def evaluate_eligibility(rfp_text: str) -> EligibilityData:
    if not gemini_model:
        raise ValueError("Gemini model is not initialized.")

    prompt = ELIGIBILITY_PROMPT.format(
        service_company_data_str=service_company_data_str,
        rfp_data=rfp_text
    )

    try:
        response = await gemini_model.generate_content_async(prompt)
        logger.info("Successfully received response from Gemini API.")
    except google_exceptions.GoogleAPIError as api_error:
        logger.error(f"Gemini API error: {api_error}")
        raise

    eligibility_data = parse_gemini_response(response)

    output_path = os.path.join(project_root, 'data', 'eligibility_output.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(eligibility_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Eligibility output saved to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save eligibility output: {e}")

    return eligibility_data

# --- Parse Gemini Response ---
def parse_gemini_response(response) -> EligibilityData:
    try:
        text_content = getattr(response.parts[0], 'text', None) if response.parts else getattr(response, 'text', None)
        if not text_content:
            raise ValueError("No text content in Gemini response.")

        logger.debug(f"Raw response text:\n{text_content[:1000]}")

        json_match = re.search(r'```json\s*(\{.*?"risk_assessment":.*?})\s*```', text_content, re.DOTALL)
        json_str = json_match.group(1) if json_match else text_content.strip()

        eligibility_data: EligibilityData = json.loads(json_str)
        validate_eligibility_data(eligibility_data)
        return eligibility_data
    except Exception as e:
        logger.exception("Failed to parse Gemini response.")
        raise

# --- Data Validator ---
def validate_eligibility_data(data: dict) -> None:
    if not isinstance(data, dict) or "risk_assessment" not in data:
        raise ValueError("Invalid data: Missing 'risk_assessment' key.")

    ra = data["risk_assessment"]
    required_keys = {"overall_risk_score", "high_risk_items", "medium_risk_items", "low_risk_items"}

    if not isinstance(ra, dict) or not required_keys.issubset(ra.keys()):
        raise ValueError(f"Invalid risk_assessment keys: Expected {required_keys}")

# --- Main Entrypoint ---
async def main(rfp_file_path: Optional[str] = None):
    if not gemini_model:
        logger.error("Gemini model not initialized.")
        return

    try:
        rfp_json = load_json_data(rfp_file_path or RFP_DATA_PATH)
        rfp_text = json.dumps(rfp_json, indent=2)
        result = await evaluate_eligibility(rfp_text)

        print("\nEligibility Assessment Result:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate RFP eligibility using Gemini API.")
    parser.add_argument("--rfp_file", type=str, help="Path to the RFP JSON file.")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.rfp_file))
    except RuntimeError as e:
        if "event loop" in str(e):
            logger.warning("Event loop already running. Skipping asyncio.run().")
