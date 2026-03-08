"""
Generate Newsletter Lambda Handler
Orchestrates newsletter generation and distribution
"""
import json
import logging

from src.generate_newsletter.orchestrator import generate_and_send_daily_newsletter

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Orchestrates newsletter generation and distribution
    
    Triggered by EventBridge daily at 7 AM Mexico City time
    
    Returns:
    {
        "statusCode": 200,
        "body": {
            "newsletter_id": "...",
            "sent_count": int,
            "failed_count": int,
            "incidents_count": int
        }
    }
    
    Requirements:
        - 5.2: Scrape current traffic data when daily trigger executes
        - 5.3: Generate newsletter content using AI when traffic data is collected
    """
    logger.info("Starting daily newsletter generation")
    
    try:
        # Execute orchestration
        result = generate_and_send_daily_newsletter()
        
        logger.info(
            f"Newsletter generation completed successfully: "
            f"newsletter_id={result['newsletter_id']}, "
            f"incidents={result['incidents_count']}"
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Newsletter generation failed: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Newsletter generation failed'
            })
        }
