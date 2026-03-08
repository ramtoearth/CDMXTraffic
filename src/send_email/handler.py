"""
Send Email Lambda Handler
Sends emails via Zavu.dev API
"""
import json
import logging

from src.send_email.zavu_client import send_email_via_zavu
from src.shared.models import EmailResponse

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Sends emails via Zavu.dev API
    
    Expected event:
    {
        "to_email": "user@example.com",
        "to_name": "User Name",
        "subject": "...",
        "html_body": "...",
        "text_body": "...",
        "newsletter_type": "welcome" | "daily"
    }
    
    Returns:
    {
        "success": bool,
        "message_id": "...",
        "error": "..." (if failed)
    }
    
    Requirements:
        - 6.1: Uses Zavu.dev API
        - 6.2: Includes both HTML and text versions
        - 6.3: Retry logic with exponential backoff
        - 6.4: Returns message_id on success
        - 6.5: Logs failures with error details
    """
    try:
        # Extract parameters from event
        to_email = event.get('to_email')
        to_name = event.get('to_name', '')
        subject = event.get('subject')
        html_body = event.get('html_body')
        text_body = event.get('text_body')
        newsletter_type = event.get('newsletter_type', 'daily')
        
        # Validate required fields
        if not to_email:
            logger.error("Missing required field: to_email")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'error': 'Missing required field: to_email'
                })
            }
        
        if not subject:
            logger.error("Missing required field: subject")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'error': 'Missing required field: subject'
                })
            }
        
        if not html_body or not text_body:
            logger.error("Missing required fields: html_body and/or text_body")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'error': 'Missing required fields: html_body and text_body'
                })
            }
        
        logger.info(f"Processing email send request for {to_email} (type: {newsletter_type})")
        
        # Send email via Zavu
        response = send_email_via_zavu(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            to_name=to_name
        )
        
        # Log result
        if response.success:
            logger.info(f"Email sent successfully to {to_email}. Message ID: {response.message_id}")
        else:
            logger.error(f"Failed to send email to {to_email}. Error: {response.error}")
        
        # Return response
        return {
            'statusCode': 200 if response.success else 500,
            'body': json.dumps(response.to_dict())
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': f'Internal error: {str(e)}'
            })
        }

