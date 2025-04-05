import logging
import json
import os
import sys
import re
import asyncio
from typing import List, TypedDict, Optional
import argparse
from dotenv import load_dotenv
import google.generativeai as genai

# --- Load Environment ---
load_dotenv()

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- TypedDicts ---
class ActionStep(TypedDict):
    step: str
    description: str
    priority: str
    estimated_days: int

class PlanOfAction(TypedDict):
    steps: List[ActionStep]
    overall_strategy: str

# --- Config ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = "models/gemini-1.5-pro-latest"
COMPANY_DATA_PATH = 'data/companydata.json'
RFP_DATA_PATH = 'data/processed/rfq.json'
GAP_DATA_PATH = 'data/gap_analysis_output.json'  # Optional

# --- Gemini Setup ---
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY not set in environment.")
    sys.exit(1)

try:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(MODEL_NAME)
except Exception as e:
    logger.error(f"Gemini setup failed: {e}")
    sys.exit(1)

# --- Project Root Fix ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.append(project_root)

# --- Load JSON ---
def load_json(file_path: str) -> dict:
    try:
        full_path = os.path.join(project_root, file_path)
        with open(full_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {file_path}: {e}")
        return {}

# --- Prompt Template ---
PLAN_OF_ACTION_PROMPT = """
You are a strategic proposal consultant. Based on the following company profile and RFP, generate a prioritized step-by-step action plan to help the company win the contract.

Include:
- Necessary documents or certificates
- Compliance or legal steps
- Technical/staffing upgrades
- Timelines
- General strategy

Company Profile:
{company_data}

RFP Details:
{rfp_data}

Gap Analysis (if available):
{gap_data}

Return JSON in this format:
{{
  "steps": [
    {{
      "step": "string",
      "description": "string",
      "priority": "High | Medium | Low",
      "estimated_days": number
    }}
  ],
  "overall_strategy": "string"
}}
"""

# --- Parse Response ---
def parse_plan_response(response) -> PlanOfAction:
    try:
        text = response.text if hasattr(response, "text") else getattr(response, "candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```|(\{[\s\S]*?\})', text, re.DOTALL)
        json_str = match.group(1) or match.group(2) if match else None

        if not json_str:
            raise ValueError("No JSON found in response")

        return json.loads(json_str)
    except Exception as e:
        logger.error(f"Parsing response failed: {e}")
        raise

# --- Core Evaluation Function ---
async def generate_plan_of_action(company_data: str, rfp_data: str, gap_data: str = "") -> PlanOfAction:
    prompt = PLAN_OF_ACTION_PROMPT.format(
        company_data=company_data,
        rfp_data=rfp_data,
        gap_data=gap_data
    )

    try:
        response = await gemini_model.generate_content_async(prompt)
        return parse_plan_response(response)
    except Exception as e:
        logger.error(f"Error generating plan of action: {e}")
        raise

# --- Main ---
async def main(rfp_file: Optional[str] = None):
    logger.info("Starting Plan of Action Agent...")

    try:
        company = load_json(COMPANY_DATA_PATH)
        rfp = load_json(rfp_file or RFP_DATA_PATH)
        gap = load_json(GAP_DATA_PATH)  # Optional
    except Exception as e:
        logger.error(f"Input data loading failed: {e}")
        return

    company_str = json.dumps(company, indent=2)
    rfp_str = json.dumps(rfp, indent=2)
    gap_str = json.dumps(gap, indent=2) if gap else ""

    try:
        result = await generate_plan_of_action(company_str, rfp_str, gap_str)

        output_path = os.path.join(project_root, 'data/plan_of_action_output.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        logger.info("Plan of Action generated successfully.")
        print("\nPlan of Action Result:\n", json.dumps(result, indent=2))
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")

# --- Entry Point ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Plan of Action Agent.")
    parser.add_argument("--rfp_file", type=str, help="Path to alternate RFP file.")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.rfp_file))
    except RuntimeError as e:
        if "event loop" in str(e):
            logger.warning("Event loop is already running. Skipping main().")
        else:
            raise
