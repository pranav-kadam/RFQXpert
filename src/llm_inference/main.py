# main.py

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import async main functions from agents
from evaluation.eligilibity_agent import main as eligibility_main
from evaluation.compliance_agent import main as compliance_main
from evaluation.checklist_agent import main as checklist_main

async def run_agents():
    print("Running Eligibility Agent...")
    await eligibility_main()

    print("Running Compliance Agent...")
    await compliance_main()

    print("Running Checklist Agent...")
    await checklist_main()

if __name__ == "__main__":
    asyncio.run(run_agents())
