"""
Get Sample Newsletter Lambda Handler
Returns latest newsletter for landing page preview
"""
import json
import logging
from .s3_client import get_latest_newsletter_from_s3

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Returns latest newsletter from S3 archive
    
    Returns HTML content with CORS headers
    
    Requirements:
        - 8.1: Provide endpoint to retrieve sample newsletter
        - 8.2: Return the most recent newsletter from S3 archive
        - 8.3: Include CORS headers for landing page access
        - 8.4: Return HTML content with appropriate Content-Type header
    """
    logger.info("Fetching sample newsletter")

    import json
    cors_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    }

    # Get latest newsletter from S3
    html_content = get_latest_newsletter_from_s3()

    if html_content is None:
        logger.warning("No newsletter available in S3")
        return {
            'statusCode': 404,
            'headers': cors_headers,
            'body': json.dumps({
                'success': False,
                'message': 'No newsletter available yet'
            })
        }

    return {
        'statusCode': 200,
        'headers': cors_headers,
        'body': json.dumps({
            'success': True,
            'html_content': html_content
        })
    }
