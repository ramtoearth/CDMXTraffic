"""
Subscribe Lambda Handler
Handles user subscription requests

Requirements validated:
- 1.1: Create subscriber with unique subscriber_id
- 1.2: Validate email format
- 1.3: Handle duplicate active subscriptions
- 1.4: Reactivate inactive subscriptions
- 1.5: Support daily and weekly frequencies
"""
import json
import logging

from src.shared.models import SubscribeRequest
from src.subscribe.subscription_logic import validate_and_save_subscriber

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Handles subscription requests
    
    Expected event body:
    {
        "email": "user@example.com",
        "frequency": "daily" | "weekly",
        "name": "User Name" (optional)
    }
    
    Returns:
    {
        "success": bool,
        "message": str,
        "subscriber_id": str (optional)
    }
    
    Requirements:
        - 1.1: Create new subscriber record
        - 1.2: Reject invalid email formats
        - 1.3: Reject duplicate active subscriptions
        - 1.4: Reactivate inactive subscriptions
        - 1.5: Validate frequency values
    """
    logger.info(f"Received subscription request")
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Create request object
        request = SubscribeRequest.from_dict(body)
        
        # Validate and save subscriber
        response = validate_and_save_subscriber(
            email=request.email,
            frequency=request.frequency,
            name=request.name
        )
        
        # Determine HTTP status code
        status_code = 200 if response.success else 400
        
        logger.info(f"Subscription response: success={response.success}, message={response.message}")
        
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response.to_dict())
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
        logger.error(f"Unexpected error processing subscription: {e}", exc_info=True)
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
