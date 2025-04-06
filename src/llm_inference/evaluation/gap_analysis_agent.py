import logging
import json
import re
import os
import sys
import asyncio
from typing import List, Optional, TypedDict
import argparse

import google.generativeai as genai
from dotenv import load_dotenv

# --- Load environment variables ---
load_dotenv()

# --- Logging setup ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Data Structures ---
class GapItem(TypedDict):
    requirement: str
    current_capability: str
    gap: str
    recommendation: str

class GapAnalysis(TypedDict):
    gaps: List[GapItem]
    summary: str

# --- Configuration ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = 'gemini-1.5-pro'  # ✅ Correct model name
COMPANY_DATA_PATH = 'data/companydata.json'
RFP_DATA_PATH = 'RAG/data/embedding.json'

if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY environment variable not set.")
    sys.exit("Error: GEMINI_API_KEY environment variable not set.")

# Configure Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(MODEL_NAME)
except Exception as config_error:
    logger.error(f"Failed to configure Gemini API: {config_error}")
    sys.exit(1)

# --- Project Root Fix ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.append(project_root)

# --- Load JSON ---
def load_json_data(file_path: str) -> dict:
    try:
        full_path = os.path.join(project_root, file_path)
        with open(full_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON file {file_path}: {e}")
        raise

# --- Prompt ---
GAP_ANALYSIS_PROMPT = """
You are a proposal analyst. Your job is to identify **gaps** between the company's capabilities and the requirements listed in this government RFP.

Company capabilities:
{company_data}

RFP requirements:
{rfp_data}

Perform a **Gap Analysis**. For each requirement in the RFP:
- Compare it to what the company currently offers.
- If there’s a difference or shortfall, mark it as a gap.
- Suggest how the company could address this gap.

Return JSON in the following format:

{{
  "gaps": [
    {{
      "requirement": "string",
      "current_capability": "string",
      "gap": "string",
      "recommendation": "string"
    }}
  ],
  "summary": "string"
}}
"""

# --- Perform Gap Analysis ---
async def perform_gap_analysis(rfp_text: str, company_data: str) -> GapAnalysis:
    prompt = GAP_ANALYSIS_PROMPT.format(
        company_data=company_data,
        rfp_data=rfp_text
    )

    try:
        response = await gemini_model.generate_content_async(prompt)
        return parse_gap_response(response)
    except Exception as e:
        logger.error(f"Gemini API Error: {e}")
        raise

# --- Parse Response ---
def parse_gap_response(response) -> GapAnalysis:
    try:
        text_content = response.text if hasattr(response, "text") else getattr(response, "candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

        logger.debug(f"Raw response:\n{text_content}")

        json_pattern = r'```json\s*(\{[\s\S]*?\})\s*```|(\{[\s\S]*?\})'
        match = re.search(json_pattern, text_content, re.DOTALL)

        json_str = match.group(1) if match and match.group(1) else match.group(2) if match else None

        if not json_str:
            raise ValueError("No valid JSON found in Gemini response.")

        gap_analysis: GapAnalysis = json.loads(json_str)
        return gap_analysis
    except Exception as e:
        logger.error(f"Failed to parse Gemini response: {e}")
        raise

# --- Main Logic ---
async def main(rfp_file_path: Optional[str] = None):
    logger.info("Starting Gap Analysis Agent...")

    try:
        company_data = load_json_data(COMPANY_DATA_PATH)
        rfp_data = load_json_data(rfp_file_path or RFP_DATA_PATH)
    except Exception as e:
        logger.critical(f"Failed to load input data: {e}")
        return

    company_data_str = json.dumps(company_data, indent=2)
    rfp_data_str = json.dumps(rfp_data, indent=2)

    try:
        result = await perform_gap_analysis(rfp_data_str, company_data_str)

        output_path = os.path.join(project_root, "data/gap_analysis_output.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        logger.info("Gap analysis completed. Output saved.")
        print("\nGap Analysis Result:\n", json.dumps(result, indent=2))

    except Exception as e:
        logger.error(f"Gap analysis failed: {e}")

# --- Entry Point ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Gap Analysis Agent.")
    parser.add_argument("--rfp_file", type=str, help="Path to the RFP data JSON file.")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.rfp_file))
    except RuntimeError as e:
        if "event loop" in str(e):
            logger.warning("Event loop is already running. Skipping main().")
        else:
            raise
