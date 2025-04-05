# main.py

from evaluation.eligilibity_agent import main as eligibility_main
from evaluation.compliance_agent import main as compliance_main
from evaluation.checklist_agent import main as checklist_main

def run_agents():
    print("Running Eligibility Agent...")
    eligibility_main()

    print("Running Compliance Agent...")
    compliance_main()

    print("Running Checklist Agent...")
    checklist_main()

if __name__ == "__main__":
    run_agents()
