import json
from pathlib import Path

def load_eligibility_report(file_path: str) -> dict:
    """Load the output from the Gemini evaluation JSON."""
    with open(file_path, 'r') as f:
        return json.load(f)

def generate_checklist_json(eligibility_data: dict) -> dict:
    """Generate a structured checklist dictionary."""
    return {
        "meets_overall_criteria": eligibility_data["meets_criteria"],
        "met_requirements": [
            {"requirement": req, "status": "met"} for req in eligibility_data["met_requirements"]
        ],
        "unmet_requirements": [
            {"requirement": req, "status": "unmet"} for req in eligibility_data["unmet_requirements"]
        ],
        "reasons": eligibility_data["reasons"],
        "recommendations": eligibility_data["recommendations"]
    }

def save_json_checklist(data: dict, output_path: str) -> None:
    """Save the checklist as JSON."""
    Path(output_path).write_text(json.dumps(data, indent=2), encoding='utf-8')
    print(f"Checklist JSON saved to: {output_path}")

if __name__ == "__main__":
    input_file = "RFQXpert/data/eligibility_output.json"  # Change path if needed
    output_file = "RFQXpert/output/eligibility_checklist.json"

    try:
        eligibility_data = load_eligibility_report(input_file)
        checklist = generate_checklist_json(eligibility_data)
        save_json_checklist(checklist, output_file)
    except Exception as e:
        print(f"Error generating JSON checklist: {e}")
