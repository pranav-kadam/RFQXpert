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

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.append(project_root)

# --- Configuration ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = 'gemini-2.0-flash'
COMPLIANCE = os.path.join(project_root, 'data', 'compliance_output.json') # Relative path within project
ELIGIBLITY = os.path.join(project_root, 'data', 'eligibility_output.json')

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
    compliance = load_json_data(COMPLIANCE)
    compliance = json.dumps(compliance, indent=2)
except Exception:
    logger.critical("Failed to load company data. Exiting.")
    sys.exit(1)

# --- RFP Data Loading (Handling Missing or Invalid Data) ---
try:
    eligiblity = load_json_data(ELIGIBLITY)
    eligiblity = json.dumps(eligiblity, indent=2)
except Exception:
    logger.warning("Failed to load RFP data. Using placeholder.")
    eligiblity = "{}"  # Placeholder

# --- Main Functionality ---
def generate_checklist_and_recommendations(compliance_data: str, eligibility_data: str) -> str:
    """Generates a checklist of requirements met, compliance status, and recommendations using Gemini."""

    prompt = f"""
You are an AI assistant that analyzes company compliance data and RFP (Request for Proposal) eligibility requirements to generate a checklist, assess compliance, and provide recommendations.

Here's the company compliance data:
{compliance_data}

Here's the RFP eligibility data:
{eligibility_data}

Based on this data, please generate the following in json:

1.  Checklist of Requirements Met:
    List each RFP requirement from the 'eligibility_data' and indicate whether it is met or not met based on the company's 'compliance_data'.  Focus on actionable items and clear yes/no answers.  Provide a brief explanation for each item regarding why it's considered met or not met.

2.  Compliance Status:
    Summarize the overall compliance status based on the checklist. Highlight any significant compliance gaps or risks identified in the data.  Quantify the compliance where possible (e.g. "Meets 80% of requirements currently").

3.  Recommendations:
    Provide specific and actionable recommendations to address any identified compliance gaps. These recommendations should directly relate to the 'mitigation' strategies outlined in both datasets.  Prioritize recommendations based on the severity and likelihood of the associated risks.  Make sure that recommendations are clear, concise, and easily implementable.

Your response should be well-formatted and easy to understand.
"""

    if gemini_model:
        try:
            response = gemini_model.generate_content(prompt)
            return response.text
        except google_exceptions.GoogleAPIError as api_error:
            logger.error(f"Gemini API error: {api_error}")
            return f"Error: Failed to generate checklist due to API error: {api_error}"
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return f"Error: Failed to generate checklist due to an unexpected error: {e}"
    else:
        return "Error: Gemini model not initialized."


def main():
    """Main function to orchestrate the process."""
    try:
        checklist_and_recommendations = generate_checklist_and_recommendations(compliance, eligiblity)
        print(checklist_and_recommendations)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()