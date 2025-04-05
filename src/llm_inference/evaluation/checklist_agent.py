import logging
import json
import re
from llm_inference.utils.gemini import gemini_client

logger = logging.getLogger(__name__)

CHECKLIST_PROMPT = """Generate submission checklist from RFP: {rfp_text}

Company Profile: {company_profile}

Create actionable tasks with:
- Clear description
- Priority (high/medium/low)
- Responsible department
- Due date (relative to RFP deadline)
- Required documents

Return JSON format:
{{
  "checklist": [
    {{
      "task": string,
      "priority": string,
      "department": string,
      "due_date_offset": int,
      "documents": [strings]
    }}
  ],
  "total_tasks": int,
  "critical_path": [task_ids]
}}"""

async def generate_checklist(rfp_text: str, company_profile: dict) -> dict:
    try:
        prompt = CHECKLIST_PROMPT.format(
            rfp_text=rfp_text,
            company_profile=company_profile
        )
        
        response = await gemini_client.generate_content(prompt)
        return parse_checklist_response(response)
        
    except Exception as e:
        logger.error(f"Gemini checklist error: {str(e)}")
        raise

def parse_checklist_response(response) -> dict:
    """
    Parse the JSON response from Gemini API for the checklist generation.
    
    Args:
        response: Response object from Gemini API
        
    Returns:
        dict: Parsed checklist data
    """
    try:
        # Extract text content from the response
        text_content = response.text
        
        # Try to find JSON in the response using regex
        json_pattern = r'({[\s\S]*})'
        json_matches = re.search(json_pattern, text_content)
        
        if json_matches:
            json_str = json_matches.group(1)
            # Parse the JSON string
            checklist_data = json.loads(json_str)
            
            # Validate the structure
            validate_checklist_data(checklist_data)
            
            # Add task IDs if they don't exist
            checklist_data = add_task_ids(checklist_data)
            
            return checklist_data
        else:
            # No JSON found, fallback to a basic structure
            logger.warning("No valid JSON found in Gemini response")
            return create_fallback_checklist("No valid JSON found in model response")
            
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from Gemini response: {str(e)}")
        return create_fallback_checklist(f"JSON parsing error: {str(e)}")
        
    except ValueError as e:
        logger.error(f"Invalid checklist data structure: {str(e)}")
        return create_fallback_checklist(f"Data validation error: {str(e)}")
        
    except Exception as e:
        logger.error(f"Unexpected error parsing Gemini response: {str(e)}")
        return create_fallback_checklist(f"Unexpected error: {str(e)}")

def validate_checklist_data(data: dict) -> None:
    """
    Validate that the checklist data contains all required fields.
    
    Args:
        data: Parsed JSON data
        
    Raises:
        ValueError: If data is missing required fields
    """
    if "checklist" not in data:
        raise ValueError("Missing required field: checklist")
        
    if "total_tasks" not in data:
        raise ValueError("Missing required field: total_tasks")
        
    if "critical_path" not in data:
        raise ValueError("Missing required field: critical_path")
        
    if not isinstance(data["checklist"], list):
        raise ValueError("'checklist' must be a list")
        
    if not isinstance(data["total_tasks"], int):
        raise ValueError("'total_tasks' must be an integer")
        
    if not isinstance(data["critical_path"], list):
        raise ValueError("'critical_path' must be a list")
        
    # Validate each task in the checklist
    valid_priorities = ["high", "medium", "low"]
    for i, task in enumerate(data["checklist"]):
        required_task_fields = ["task", "priority", "department", "due_date_offset", "documents"]
        
        for field in required_task_fields:
            if field not in task:
                raise ValueError(f"Task #{i+1} missing required field: {field}")
                
        if task["priority"].lower() not in valid_priorities:
            raise ValueError(f"Task #{i+1} has invalid priority: {task['priority']}")
            
        if not isinstance(task["due_date_offset"], int):
            raise ValueError(f"Task #{i+1} 'due_date_offset' must be an integer")
            
        if not isinstance(task["documents"], list):
            raise ValueError(f"Task #{i+1} 'documents' must be a list")
            
def add_task_ids(data: dict) -> dict:
    """
    Ensure each task has an ID field, required for critical path references.
    
    Args:
        data: Parsed checklist data
        
    Returns:
        dict: Checklist data with task IDs added
    """
    # Create a copy to avoid modifying the original
    result = data.copy()
    
    # Add task IDs if they don't exist
    for i, task in enumerate(result["checklist"]):
        if "id" not in task:
            task["id"] = f"task_{i+1}"
    
    # Validate that critical path references existing task IDs
    task_ids = [task["id"] for task in result["checklist"]]
    for path_id in result["critical_path"]:
        if path_id not in task_ids:
            logger.warning(f"Critical path contains unknown task ID: {path_id}")
    
    # Update total_tasks count to match actual number of tasks
    result["total_tasks"] = len(result["checklist"])
    
    return result

def create_fallback_checklist(error_message: str) -> dict:
    """
    Create a fallback checklist when parsing fails.
    
    Args:
        error_message: Description of the error
        
    Returns:
        dict: Basic checklist structure
    """
    return {
        "checklist": [
            {
                "id": "task_1",
                "task": "Review RFP requirements manually",
                "priority": "high",
                "department": "Proposal Team",
                "due_date_offset": -30,
                "documents": ["RFP document"]
            },
            {
                "id": "task_2",
                "task": "Consult with department heads on submission plan",
                "priority": "high",
                "department": "Management",
                "due_date_offset": -25,
                "documents": ["RFP summary"]
            },
            {
                "id": "task_3",
                "task": "Create manual submission checklist",
                "priority": "high",
                "department": "Proposal Team",
                "due_date_offset": -20,
                "documents": ["Internal template"]
            }
        ],
        "total_tasks": 3,
        "critical_path": ["task_1", "task_2", "task_3"],
        "error": error_message
    }