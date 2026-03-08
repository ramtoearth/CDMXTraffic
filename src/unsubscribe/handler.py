"""
Unsubscribe Lambda Handler
Handles unsubscribe requests

Requirements validated:
- 11.3: Mark subscriber as inactive when unsubscribe link is clicked
- 11.4: Inactive subscribers not included in future distributions
- 11.5: Validate unsubscribe_token before processing
"""
import json
import logging

from src.unsubscribe.unsubscribe_logic import process_unsubscribe, process_unsubscribe_by_email

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Handles unsubscribe requests
    
    Expected event body:
    {
        "token": "unsubscribe_token"
    }
    
    Returns:
    {
        "success": bool,
        "message": str
    }
    
    Requirements:
        - 11.3: Mark subscriber as inactive (active=False)
        - 11.4: Inactive subscribers excluded from future distributions
        - 11.5: Validate unsubscribe_token before processing
    """
    logger.info("Processing unsubscribe request")
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        token = body.get('token', '').strip()
        email = body.get('email', '').strip()

        if not token and not email:
            logger.warning("Missing token and email in request")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'message': 'Missing unsubscribe token'
                })
            }

        # Process unsubscribe — prefer token, fall back to email
        if token:
            success, message = process_unsubscribe(token)
        else:
            success, message = process_unsubscribe_by_email(email)
        
        # Determine HTTP status code
        status_code = 200 if success else 400
        
        logger.info(f"Unsubscribe response: success={success}, message={message}")
        
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': success,
                'message': message
            })
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request body: {e}")
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'message': 'Invalid JSON in request body'
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error processing unsubscribe: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'message': 'Internal server error'
            })
        }
