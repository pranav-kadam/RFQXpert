import asyncio
import json
import os
import sys
import logging

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.append(project_root)

from src.llm_inference.evaluation.eligilibity_agent import evaluate_eligibility

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_eligibility():
    try:
        # Load sample RFP data
        with open('data/processed/rfq.json', 'r') as f:
            rfp_data = json.load(f)
        
        # Test with the RFP data
        logger.info("Starting eligibility evaluation...")
        result = await evaluate_eligibility(json.dumps(rfp_data))
        
        # Print results
        logger.info("\nEligibility Results:")
        logger.info(f"Meets Criteria: {result['meets_criteria']}")
        logger.info("\nMet Requirements:")
        for req in result['met_requirements']:
            logger.info(f"✓ {req}")
        
        logger.info("\nUnmet Requirements:")
        for req in result['unmet_requirements']:
            logger.info(f"✗ {req}")
            
        logger.info("\nReasons:")
        for reason in result['reasons']:
            logger.info(f"• {reason}")
            
        logger.info("\nRecommendations:")
        for rec in result['recommendations']:
            logger.info(f"→ {rec}")
            
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_eligibility()) 