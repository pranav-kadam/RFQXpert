import os
import sys
import re
import json
import logging
import asyncio
from dotenv import load_dotenv
import google.generativeai as genai

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Load Environment Variables ---
load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY environment variable not set.")
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as config_error:
        logger.error(f"Failed to configure Gemini API: {config_error}")

# --- Initialize Gemini Model ---
try:
    gemini_model = genai.GenerativeModel('gemini-2.0-flash')
except Exception as model_init_error:
    logger.error(f"Failed to initialize Gemini model: {model_init_error}")
    gemini_model = None

# --- Add Project Root ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.append(project_root)

# --- Load Company Data ---
try:
    company_data_path = os.path.join(project_root, 'data', 'companydata.json')
    with open(company_data_path, 'r', encoding='utf-8') as f:
        service_company_data = json.load(f)
    service_company_data_str = json.dumps(service_company_data, indent=2)
except FileNotFoundError:
    logger.error(f"Company data file not found at: {company_data_path}")
    sys.exit(1)
except json.JSONDecodeError:
    logger.error("Could not parse company data JSON.")
    sys.exit(1)
except Exception as e:
    logger.error(f"Error loading company data: {e}")
    sys.exit(1)

# --- Load RFP Data ---
try:
    rfp_data_path = os.path.join(project_root, 'RAG', 'data', 'embedding.json')
    with open(rfp_data_path, 'r', encoding='utf-8') as f:
        client_rfp_text_json = json.load(f)
    client_rfp_text_str = json.dumps(client_rfp_text_json, indent=2)
except FileNotFoundError:
    logger.warning(f"RFP data file not found at: {rfp_data_path}.")
    client_rfp_text_str = "{}"
except json.JSONDecodeError:
    logger.warning("Error decoding JSON from RFP data file.")
    client_rfp_text_str = "{}"
except Exception as e:
    logger.warning(f"Error loading RFP data: {e}")
    client_rfp_text_str = "{}"

# --- Prompt Template ---
ELIGIBILITY_PROMPT = """
RFQXpert provides services to U.S. government agencies. To secure contracts, we must respond to Requests for Proposals (RFPs)—detailed documents outlining project requirements, legal terms, and submission guidelines. These are the details of RFQXpert data:
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
}}
"""

# --- Gemini Response Parser ---
def parse_gemini_response(response_text: str) -> dict:
    try:
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if match:
            return json.loads(match.group())
        else:
            logger.warning("No JSON block found in response.")
            return {"error": "Invalid response format"}
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return {"error": "Invalid JSON in response"}

# --- Eligibility Evaluation Function ---
async def evaluate_eligibility(rfp_text: str) -> dict:
    if not gemini_model:
        logger.error("Gemini model is not available.")
        return {"error": "Model not available"}

    prompt = ELIGIBILITY_PROMPT.format(
        company_data=service_company_data_str,
        rfp_data=rfp_text
    )

    try:
        response = gemini_model.generate_content(prompt)
        if hasattr(response, 'text'):
            return parse_gemini_response(response.text)
        else:
            logger.error("No text found in Gemini response.")
            return {"error": "Empty response from model"}
    except Exception as e:
        logger.error(f"Error during eligibility evaluation: {e}")
        return {"error": str(e)}

# --- Main ---
async def main():
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not set.")
        return
    if not gemini_model:
        logger.error("Gemini model not initialized.")
        return
    if not client_rfp_text_str or client_rfp_text_str == "{}":
        logger.error("RFP data missing or invalid.")
        return

    result = await evaluate_eligibility(client_rfp_text_str)
    print("\nEligibility Assessment Result:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "cannot run event loop while another loop is running" in str(e):
            logger.warning("Asyncio event loop already running. Skipping main().")
        else:
            raise
