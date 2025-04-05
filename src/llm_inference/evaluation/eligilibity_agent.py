import logging
import json
import re
import os
import sys
import asyncio # Import asyncio for async operations if needed elsewhere

# Import the Google Generative AI library
import google.generativeai as genai

# --- Configuration ---
# Load API Key from environment variable
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    # Log an error or raise an exception if the key is missing
    # Choose one based on how you want to handle missing configuration
    # Option 1: Log and exit (or handle gracefully later)
    logging.basicConfig(level=logging.ERROR) # Ensure logging is configured
    logging.error("GEMINI_API_KEY environment variable not set.")
    # sys.exit("Error: GEMINI_API_KEY environment variable not set.") # Or exit
    # Option 2: Raise an exception immediately
    # raise ValueError("GEMINI_API_KEY environment variable not set.")

    # For this example, let's just log the error and proceed,
    # but the API call will fail later. A real application should handle this more robustly.
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as config_error:
        logging.error(f"Failed to configure Gemini API: {config_error}")
        # Handle configuration error (e.g., exit or set a flag)

# Create the Gemini model instance (adjust model name if needed, e.g., 'gemini-1.5-flash')
# Handle potential errors during model instantiation if configuration failed
try:
    # Consider adding generation_config or safety_settings if needed
    gemini_model = genai.GenerativeModel('gemini-2.0-flash')
except Exception as model_init_error:
    logging.error(f"Failed to initialize Gemini model: {model_init_error}")
    gemini_model = None # Ensure model is None if initialization fails

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.append(project_root)

# No longer needed: from src.utils.gemini import gemini_client

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Example basic logging config

# Load company data
try:
    company_data_path = os.path.join(project_root, 'data', 'companydata.json')
    with open(company_data_path, 'r', encoding='utf-8') as f:
        service_company_data = json.load(f)
    # If you want to embed it as raw JSON string
    service_company_data_str = json.dumps(service_company_data, indent=2)
except FileNotFoundError:
    logger.error(f"Company data file not found at: {company_data_path}")
    sys.exit(f"Error: Company data file not found at: {company_data_path}")
except json.JSONDecodeError:
    logger.error(f"Error decoding JSON from company data file: {company_data_path}")
    sys.exit(f"Error: Could not parse company data JSON.")
except Exception as e:
    logger.error(f"Error loading company data: {e}")
    sys.exit(f"Error loading company data: {e}")


# Load RFP data (assuming this is loaded correctly elsewhere or passed to the function)
# For testing purposes, let's load it here if the function expects it pre-loaded
try:
    rfp_data_path = os.path.join(project_root, 'data', 'processed', 'rfq.json')
    with open(rfp_data_path, 'r', encoding='utf-8') as f:
        client_rfp_text_json = json.load(f) # Assuming it's JSON
    # Convert the loaded JSON object back to a string for the prompt
    client_rfp_text_str = json.dumps(client_rfp_text_json, indent=2)
except FileNotFoundError:
    logger.warning(f"RFP data file not found at: {rfp_data_path}. Using placeholder if needed.")
    # Decide how to handle missing RFP data - perhaps use a default or raise error
    client_rfp_text_str = "{}" # Placeholder empty JSON string
except json.JSONDecodeError:
    logger.warning(f"Error decoding JSON from RFP data file: {rfp_data_path}. Using placeholder.")
    client_rfp_text_str = "{}" # Placeholder
except Exception as e:
    logger.warning(f"Error loading RFP data: {e}. Using placeholder.")
    client_rfp_text_str = "{}" # Placeholder


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
    """
    Evaluates company eligibility for an RFP using the Gemini API directly.

    Args:
        rfp_text: A string containing the RFP data (ideally JSON formatted).

    Returns:
        A dictionary containing the eligibility assessment.
    """
    # Check if the model was initialized successfully
    if not gemini_model:
        logger.error("Gemini model is not available. Cannot evaluate eligibility.")
        return create_fallback_response("Gemini model initialization failed.")

    try:
        # Format the prompt properly
        prompt = ELIGIBILITY_PROMPT.format(
            company_data=service_company_data_str,
            rfp_data=rfp_text  # Use the passed rfp_text argument
        )

        try:
            # Use the generate_content_async method for asynchronous call
            response = await gemini_model.generate_content_async(prompt)
            logger.info("Successfully received response from Gemini API.")
        except Exception as api_error:
            logger.error(f"Gemini API error: {str(api_error)}")
            # Consider more specific error handling based on google.api_core.exceptions
            return create_fallback_response(f"API error: {str(api_error)}")

        eligibility_data = parse_gemini_response(response)

        # Save the output to a JSON file
        output_path = os.path.join(project_root, 'data', 'eligibility_output.json')
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

    except Exception as e:
        logger.exception(f"Unexpected error during eligibility evaluation: {str(e)}") # Use logger.exception to include traceback
        return create_fallback_response(f"Evaluation error: {str(e)}")


def parse_gemini_response(response) -> dict:
    """
    Parse the JSON response from Gemini API.

    Args:
        response: Response object from google.generativeai.types.GenerateContentResponse

    Returns:
        dict: Parsed eligibility assessment data
    """
    try:
        # Extract text content from the response parts
        # Check if response has parts and the first part has text
        if not response.parts:
             logger.warning("Gemini response has no parts.")
             # Attempt to access text directly as a fallback, though structure might differ
             try:
                 text_content = response.text
             except AttributeError:
                 logger.error("Gemini response has no parts and no direct text attribute.")
                 return create_fallback_response("Received empty or invalid response structure from model")
        else:
             text_content = response.parts[0].text

        logger.debug(f"Raw response text:\n{text_content}") # Log the raw text for debugging

        # Try to find JSON in the response using a precise regex first
        # Look for JSON object that matches the expected structure (starts with { and "meets_criteria")
        # Make the regex more robust to handle potential leading/trailing whitespace and markdown backticks
        json_pattern_precise = r'```json\s*(\{\s*"meets_criteria":.+?\}\s*})\s*```|(\{\s*"meets_criteria":.+?\}\s*})'
        json_matches = re.search(json_pattern_precise, text_content, re.DOTALL)

        json_str = None
        if json_matches:
            # Group 1 captures JSON within backticks, Group 2 captures JSON without backticks
            json_str = json_matches.group(1) if json_matches.group(1) else json_matches.group(2)
            logger.info("Found JSON block using precise pattern.")
        else:
            # Fallback: Try finding any JSON block if the precise pattern fails
            logger.warning("Precise JSON pattern failed. Trying general JSON block search.")
            json_pattern_general = r'```json\s*(\{[\s\S]*?\})\s*```|(\{[\s\S]*?\})'
            potential_jsons = re.findall(json_pattern_general, text_content, re.DOTALL)

            for potential_match in potential_jsons:
                # Extract the non-empty group (either with or without backticks)
                potential_json_str = potential_match[0] if potential_match[0] else potential_match[1]
                try:
                    data = json.loads(potential_json_str)
                    # Check if it looks like our expected structure
                    if "meets_criteria" in data and "met_requirements" in data:
                        json_str = potential_json_str
                        logger.info("Found JSON block using general pattern fallback.")
                        break # Use the first valid-looking JSON found
                except (json.JSONDecodeError, TypeError):
                    logger.debug(f"Ignoring invalid JSON block: {potential_json_str[:100]}...")
                    continue # Ignore blocks that are not valid JSON

        if json_str:
            # Parse the extracted JSON string
            eligibility_data = json.loads(json_str)

            # Validate the structure
            validate_eligibility_data(eligibility_data)

            return eligibility_data
        else:
            logger.error("No valid JSON found in Gemini response text.")
            logger.debug(f"Full response text where JSON was not found:\n{text_content}")
            return create_fallback_response("No valid JSON found in model response")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from Gemini response: {str(e)}")
        logger.debug(f"JSON String that failed parsing: {json_str}")
        return create_fallback_response(f"JSON parsing error: {str(e)}")

    except ValueError as e: # Catch validation errors
        logger.error(f"Invalid eligibility data structure: {str(e)}")
        return create_fallback_response(f"Data validation error: {str(e)}")

    except AttributeError:
         # This might happen if the 'response' object doesn't have '.parts' or '.text'
         logger.error("Unexpected response structure from Gemini API.")
         return create_fallback_response("Invalid response object structure received from API.")

    except Exception as e:
        logger.exception(f"Unexpected error parsing Gemini response: {str(e)}") # Use exception for traceback
        return create_fallback_response(f"Unexpected parsing error: {str(e)}")


def validate_eligibility_data(data: dict) -> None:
    """
    Validate that the eligibility data contains all required fields and correct types.

    Args:
        data: Parsed JSON data

    Raises:
        ValueError: If data is missing required fields or has incorrect types.
    """
    if not isinstance(data, dict):
         raise ValueError("Parsed data is not a dictionary.")

    required_keys = ["meets_criteria", "met_requirements", "unmet_requirements",
                     "reasons", "recommendations"]

    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        raise ValueError(f"Missing required field(s): {', '.join(missing_keys)}")

    # Validate data types
    if not isinstance(data["meets_criteria"], bool):
        # Attempt type coercion if it's a string 'true'/'false' (case-insensitive)
        if isinstance(data["meets_criteria"], str):
             val_lower = data["meets_criteria"].lower()
             if val_lower == 'true':
                 data["meets_criteria"] = True
             elif val_lower == 'false':
                 data["meets_criteria"] = False
             else:
                  raise ValueError("'meets_criteria' must be a boolean (or 'true'/'false' string)")
        else:
            raise ValueError("'meets_criteria' must be a boolean")

    for list_field in ["met_requirements", "unmet_requirements", "reasons", "recommendations"]:
        if not isinstance(data[list_field], list):
            raise ValueError(f"'{list_field}' must be a list")

        # Validate that all items in lists are strings
        if not all(isinstance(item, str) for item in data[list_field]):
             # Allow non-strings but log a warning, or raise error if strict typing is needed
             logger.warning(f"Not all items in '{list_field}' are strings. Found types: {[type(item) for item in data[list_field]]}")
             # Optionally convert non-strings to strings
             data[list_field] = [str(item) for item in data[list_field]]
             # Or raise error for strict validation:
             # raise ValueError(f"All items in '{list_field}' must be strings")


def create_fallback_response(error_message: str) -> dict:
    """
    Create a fallback response when parsing or API call fails.

    Args:
        error_message: Description of the error

    Returns:
        dict: Structured fallback response
    """
    logger.warning(f"Creating fallback response due to error: {error_message}")
    return {
        "meets_criteria": False,
        "met_requirements": [],
        "unmet_requirements": ["Unable to determine requirements due to error."],
        "reasons": [f"Processing failed: {error_message}"],
        "recommendations": [
            "Review the RFP manually.",
            "Verify API key and connectivity.",
            "Check the input RFP data format.",
            "If the issue persists, review logs or contact support."
        ]
    }

# --- Example Usage (if running this script directly) ---
async def main():
    """Main function to run eligibility check."""
    # Ensure logging is configured
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Check if GEMINI_API_KEY was set and model initialized
    if not GEMINI_API_KEY:
        logger.error("Cannot run main function: GEMINI_API_KEY not set.")
        return
    if not gemini_model:
        logger.error("Cannot run main function: Gemini model not initialized.")
        return

    logger.info("Starting eligibility evaluation...")

    # Use the pre-loaded client_rfp_text_str
    # Ensure it's not empty or just a placeholder if loading failed earlier
    if not client_rfp_text_str or client_rfp_text_str == "{}":
         logger.error("Cannot evaluate eligibility: RFP data is missing or invalid.")
         # You might want to load a default test RFP string here for demonstration
         # test_rfp_data = '{"title": "Test RFP", "requirements": ["Must have 5 years experience.", "Must be US-based."]}'
         # result = await evaluate_eligibility(test_rfp_data)
         return # Exit if no valid RFP data

    result = await evaluate_eligibility(client_rfp_text_str)

    logger.info("Eligibility evaluation completed.")
    print("\nEligibility Assessment Result:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    # To run the async main function
    try:
        asyncio.run(main())
    except RuntimeError as e:
        # Handle cases where asyncio event loop is already running (e.g., in Jupyter)
        if "cannot run event loop while another loop is running" in str(e):
            logger.warning("Asyncio event loop already running. Skipping main().")
        else:
            raise # Re-raise other runtime errors